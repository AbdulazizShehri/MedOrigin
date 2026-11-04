"""Real dual-import encrypted FHIR synthetic per-import timeline tests.

All inputs are hardcoded invented FHIR data. Source SHA and both audit
anchors must qualify independently; no cross-import Patient identity joining.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "workspace" / "src"))

from medscale_workspace.audit import AuditEventType, AuditTrail  # noqa: E402
from medscale_workspace.keyprovider import InMemoryTestKeyProvider, new_root_secret  # noqa: E402
from medscale_workspace.storage import WorkspaceStore  # noqa: E402

from medscale.cli import main as public_cli  # noqa: E402
from medscale.fhirkit.workspace_demo import _fictional_bundle  # noqa: E402
from medscale.fhirkit.workspace_ingest import ingest_synthetic_bundle_atomic  # noqa: E402
from medscale.fhirkit.workspace_multi_timeline import (  # noqa: E402
    SyntheticMultiImportTimelineError,
    list_verified_synthetic_import_timelines,
)
from medscale.fhirkit.workspace_multi_timeline_demo import (  # noqa: E402
    _second_fictional_timeline_bundle,
)

_WID = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
_ACTOR = "fictional-multiimport-owner"
_NOW = "2026-11-04T10:00:00+03:00"
_SECRET = "PRIVATE_FAKE_PERSON_NAME_NEVER_EXPOSED"


def _open(root: Path, provider: InMemoryTestKeyProvider):
    root.mkdir(parents=True, exist_ok=True)
    return WorkspaceStore.open(
        store_root=str(root),
        workspace_id=_WID,
        key_provider=provider,
        application_version="0.1.0.dev1",
    )


def _first() -> dict:
    source = _fictional_bundle()
    source["entry"][1]["resource"]["name"][0]["text"] = _SECRET
    source["entry"][0]["resource"]["effectiveDateTime"] = "2026-11-03T05:00:00Z"
    source["entry"][2]["resource"]["period"] = {
        "start": "2026-11-03T03:30:00Z",
        "end": "2026-11-03T04:00:00Z",
    }
    return source


def _second() -> dict:
    return _second_fictional_timeline_bundle()


def _ingest(store, provider, bundle):
    return ingest_synthetic_bundle_atomic(
        bundle,
        store,
        test_key_provider=provider,
        actor_id=_ACTOR,
        occurred_at=_NOW,
        synthetic_only=True,
    )


def _read(store, provider, head, **kwargs):
    args = {
        "store": store,
        "test_key_provider": provider,
        "actor_id": _ACTOR,
        "expected_current_audit_head_digest": head,
        "synthetic_only": True,
        "allow_in_memory_listing": True,
        "allow_in_memory_timeline": True,
    }
    args.update(kwargs)
    return list_verified_synthetic_import_timelines(**args)


def _two_imports(root: Path, provider):
    with _open(root, provider) as store:
        original = _ingest(store, provider, _first())
        AuditTrail(store).append(
            event_type=AuditEventType.WORKSPACE_OPEN,
            actor_id="fictional-reader",
            occurred_at="2026-11-04T10:01:00+03:00",
        )
        latest = _ingest(store, provider, _second())
        assert store.object_count() == 17
        assert (
            AuditTrail(store)
            .verify(expected_head_event_digest=latest["audit_head_digest"])
            .events_verified
            == 3
        )
    return original, latest


def test_actual_encrypted_two_imports_reopen_grouped_timeline_without_patient_merge(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    source_root = tmp_path / "encrypted-store"
    first, latest = _two_imports(source_root, provider)
    with _open(source_root, provider) as store:
        report = _read(store, provider, latest["audit_head_digest"])
        assert report["schema"] == "medorigin-core-verified-fictional-multiimport-timelines/v1"
        assert report["status"] == "verified_independent_import_timelines"
        assert report["current_audit_head_digest"] == latest["audit_head_digest"]
        assert report["import_count"] == 2
        assert report["total_event_count"] == 4
        assert report["total_undated_event_count"] == 0
        assert report["cross_import_patient_identity_join_performed"] is False
        assert [p["import_ordinal"] for p in report["imports"]] == [1, 2]
        assert [p["audit_sequence"] for p in report["imports"]] == [1, 3]
        assert [p["source_content_sha256"] for p in report["imports"]] == [
            first["source_content_sha256"],
            latest["source_content_sha256"],
        ]
        assert [p["import_audit_event_digest"] for p in report["imports"]] == [
            first["audit_head_digest"],
            latest["audit_head_digest"],
        ]
        assert [p["patient_count_within_import"] for p in report["imports"]] == [1, 1]
        assert [p["event_count"] for p in report["imports"]] == [2, 2]
        assert [event["resource_type"] for event in report["imports"][0]["events"]] == [
            "Encounter",
            "Observation",
        ]
        assert [event["day_utc"] for event in report["imports"][1]["events"]] == [
            "2026-11-04",
            "2026-11-05",
        ]
        for flag in (
            "patient_identity_included",
            "resource_payload_included",
            "filesystem_export_performed",
            "network_access_performed",
            "fhir_r4_conformance_validated",
            "clinical_use_authorized",
            "release_authorized",
        ):
            assert report[flag] is False
        encoded = json.dumps(report, sort_keys=True)
        for forbidden in (_SECRET, "fictional-patient", "urn:uuid:", "valueString"):
            assert forbidden not in encoded
        ciphertext = Path(store.store_path).read_bytes()
        assert _SECRET.encode() not in ciphertext


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"synthetic_only": False}, "multi_timeline_explicit_permissions_required"),
        ({"allow_in_memory_listing": False}, "multi_timeline_explicit_permissions_required"),
        ({"allow_in_memory_timeline": False}, "multi_timeline_explicit_permissions_required"),
        ({"expected_current_audit_head_digest": "bad"}, "multi_timeline_current_anchor_refused"),
        (
            {"expected_current_audit_head_digest": "0" * 64},
            "multi_timeline_catalog_verification_refused",
        ),
        ({"test_key_provider": None}, "multi_timeline_catalog_verification_refused"),
        ({"max_imports": 1}, "multi_timeline_catalog_verification_refused"),
        ({"max_imports": 0}, "multi_timeline_bounds_refused"),
        ({"max_imports": True}, "multi_timeline_bounds_refused"),
        ({"max_total_events": 3}, "multi_timeline_event_limit_refused"),
        ({"max_total_events": 0}, "multi_timeline_bounds_refused"),
        ({"max_total_events": True}, "multi_timeline_bounds_refused"),
        (
            {"patient_selections": {"0" * 64: "urn:uuid:00000000-0000-4000-8000-000000000009"}},
            "multi_timeline_unknown_patient_selection",
        ),
        ({"patient_selections": {"0" * 64: _SECRET}}, "multi_timeline_patient_selection_refused"),
        (
            {"patient_selections": {_SECRET: "urn:uuid:00000000-0000-4000-8000-000000000009"}},
            "multi_timeline_patient_selection_refused",
        ),
    ],
)
def test_fail_closed_wrong_permissions_audit_keys_caps_or_selection(
    tmp_path: Path, overrides: dict, reason: str
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    root = tmp_path / "encrypted"
    _, latest = _two_imports(root, provider)
    with _open(root, provider) as store:
        with pytest.raises(SyntheticMultiImportTimelineError, match=reason) as failure:
            _read(store, provider, latest["audit_head_digest"], **overrides)
        assert _SECRET not in str(failure.value)


def test_two_patient_source_requires_explicit_selection_per_import(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    source = _first()
    other_url = "urn:uuid:00000000-0000-4000-8000-000000000099"
    source["entry"].append(
        {
            "fullUrl": other_url,
            "resource": {
                "resourceType": "Patient",
                "id": "fictional-multi-second-person",
                "active": True,
            },
        }
    )
    root = tmp_path / "encrypted"
    with _open(root, provider) as store:
        first = _ingest(store, provider, source)
        with pytest.raises(
            SyntheticMultiImportTimelineError, match="multi_timeline_source_verification_refused"
        ):
            _read(store, provider, first["audit_head_digest"])
        selected = _read(
            store,
            provider,
            first["audit_head_digest"],
            patient_selections={
                first["source_content_sha256"]: "urn:uuid:00000000-0000-4000-8000-000000000002"
            },
        )
        assert selected["import_count"] == 1
        assert selected["total_event_count"] == 2
        assert selected["imports"][0]["patient_count_within_import"] == 2
        assert selected["imports"][0]["patient_selection_mode"] == "explicit_local_reference"
        assert other_url not in json.dumps(selected)


def test_one_import_historical_benign_later_event_keeps_anchor_verification(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path / "encrypted", provider) as store:
        first = _ingest(store, provider, _first())
        later = AuditTrail(store).append(
            event_type=AuditEventType.WORKSPACE_OPEN,
            actor_id="fictional-extra-reader",
            occurred_at="2026-11-04T11:00:00+03:00",
        )
        report = _read(store, provider, later.event_digest)
        assert report["import_count"] == 1
        assert report["imports"][0]["import_audit_event_digest"] == first["audit_head_digest"]
        assert report["total_event_count"] == 2


def test_real_public_fictional_multiimport_demo_executes_and_cleans_store(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert public_cli(["fhir", "multi-timeline-demo", "--synthetic-only", "--ephemeral-demo"]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    proof = json.loads(output.out)
    assert proof["status"] == "SYNTHETIC_VERIFIED_MULTIPLE_IMPORT_TIMELINES_PASS"
    assert proof["import_count"] == 2
    assert proof["event_count"] == 4
    assert proof["verified_audit_events"] == 3
    assert proof["closed_and_reopened"] is True
    assert proof["ephemeral_store_removed"] is True
    assert proof["cross_import_patient_identity_join_performed"] is False
    assert [x["event_count"] for x in proof["imports"]] == [2, 2]
    for flag in (
        "patient_identity_included",
        "resource_payload_included",
        "fhir_r4_conformance_validated",
        "clinical_use_authorized",
        "release_authorized",
    ):
        assert proof[flag] is False
    for token in (
        _SECRET,
        "Fictional Example Only",
        "urn:uuid:",
        "fictional-patient",
        "valueString",
    ):
        assert token not in output.out


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--synthetic-only"],
        ["--ephemeral-demo"],
        ["--ephemeral-demo", "--synthetic-only"],
        ["--synthetic-only", "--ephemeral-demo", "--input", _SECRET],
        ["--synthetic-only", "--ephemeral-demo", "--patient", _SECRET],
    ],
)
def test_public_cli_rejects_arbitrary_fhir_paths_keys_and_patient_inputs(
    capsys: pytest.CaptureFixture[str], args: list[str]
) -> None:
    assert public_cli(["fhir", "multi-timeline-demo", *args]) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert "exact_synthetic_ephemeral_flags_required" in result.err
    assert _SECRET not in result.err


def test_help_is_nonclinical_and_identity_safe(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert public_cli(["fhir", "multi-timeline-demo", "--help"]) == 0
    result = capsys.readouterr()
    assert "NO cross-import patient identity linkage" in result.out
    assert result.err == ""
