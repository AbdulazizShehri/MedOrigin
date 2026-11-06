"""Actual source/audit-verified encrypted fictional FHIR patient timeline tests."""

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
from medscale.fhirkit.bundle import (  # noqa: E402
    BundlePreflightError,
    inspect_synthetic_bundle,
)
from medscale.fhirkit.workspace_demo import _fictional_bundle  # noqa: E402
from medscale.fhirkit.workspace_ingest import (  # noqa: E402
    SyntheticWorkspaceImportError,
    ingest_synthetic_bundle_atomic,
)
from medscale.fhirkit.workspace_timeline import (  # noqa: E402
    SyntheticTimelineError,
    _events,
    read_verified_synthetic_patient_timeline,
)

WID = UUID("6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe")
ACTOR = "fictional-timeline-test-owner"
TIME = "2026-11-04T08:00:00+03:00"
TIME2 = "2026-11-04T08:10:00+03:00"
SECRET = "FICTIONAL_PRIVATE_PATIENT_FAMILY_NAME_NEVER_OUTPUT"
PATIENT_URL = "urn:uuid:00000000-0000-4000-8000-000000000002"


def _open(path: Path, provider: InMemoryTestKeyProvider) -> WorkspaceStore:
    path.mkdir(parents=True, exist_ok=True)
    return WorkspaceStore.open(
        store_root=str(path),
        workspace_id=WID,
        key_provider=provider,
        application_version="0.1.0.dev1",
    )


def _source() -> dict:
    source = _fictional_bundle()
    source["entry"][1]["resource"]["name"][0]["text"] = SECRET
    source["entry"][0]["resource"]["effectiveDateTime"] = "2026-11-02T22:10:00-05:00"
    source["entry"][2]["resource"]["period"] = {
        "start": "2026-11-03T02:20:00Z",
        "end": "2026-11-03T03:00:00Z",
    }
    return source


def _import(store: WorkspaceStore, provider: InMemoryTestKeyProvider, source: dict):
    return ingest_synthetic_bundle_atomic(
        source,
        store,
        test_key_provider=provider,
        actor_id=ACTOR,
        occurred_at=TIME,
        synthetic_only=True,
    )


def _read(store, provider, imported, current_head=None, **overrides):
    args = {
        "store": store,
        "test_key_provider": provider,
        "source_content_sha256": imported["source_content_sha256"],
        "import_audit_event_digest": imported["audit_head_digest"],
        "expected_current_audit_head_digest": current_head or imported["audit_head_digest"],
        "actor_id": ACTOR,
        "synthetic_only": True,
        "allow_in_memory_timeline": True,
    }
    args.update(overrides)
    return read_verified_synthetic_patient_timeline(**args)


def test_real_encrypted_source_reopen_historical_audit_timeline_and_no_plaintext(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    root = tmp_path / "encrypted"
    with _open(root, provider) as store:
        imported = _import(store, provider, _source())
        benign = AuditTrail(store).append(
            event_type=AuditEventType.WORKSPACE_OPEN,
            actor_id=ACTOR,
            occurred_at=TIME2,
        )
        assert store.object_count() == 9
        assert (
            AuditTrail(store).verify(expected_head_event_digest=benign.event_digest).events_verified
            == 2
        )
        assert SECRET.encode() not in Path(store.store_path).read_bytes()
    with _open(root, provider) as reopened:
        result = _read(reopened, provider, imported, benign.event_digest)
        assert result["schema"] == "medorigin-core-synthetic-verified-patient-timeline/v1"
        assert result["status"] == "source_verified_fictional_timeline"
        assert result["source_content_sha256"] == imported["source_content_sha256"]
        assert result["current_audit_head_digest"] == benign.event_digest
        assert result["event_count"] == 2
        assert result["patient_count"] == 1
        assert result["selection_mode"] == "single_unique_patient"
        assert result["undated_event_count"] == 0
        assert result["timeline"] == [
            {
                "ordinal": 1,
                "resource_type": "Encounter",
                "day_utc": "2026-11-03",
                "date_available": True,
            },
            {
                "ordinal": 2,
                "resource_type": "Observation",
                "day_utc": "2026-11-03",
                "date_available": True,
            },
        ]
        for key in (
            "patient_identity_included",
            "resource_payload_included",
            "filesystem_export_performed",
            "network_access_performed",
            "fhir_r4_conformance_validated",
            "clinical_use_authorized",
            "release_authorized",
        ):
            assert result[key] is False
        output = json.dumps(result)
        for secret in (SECRET, PATIENT_URL, "fictional-", "valueString", "urn:uuid"):
            assert secret not in output


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"synthetic_only": False}, "explicit_synthetic_timeline_attestation_required"),
        ({"allow_in_memory_timeline": False}, "explicit_synthetic_timeline_attestation_required"),
        ({"source_content_sha256": "a" * 64}, "verified_encrypted_timeline_read_refused"),
        ({"import_audit_event_digest": "b" * 64}, "verified_encrypted_timeline_read_refused"),
        (
            {"expected_current_audit_head_digest": "c" * 64},
            "verified_encrypted_timeline_read_refused",
        ),
        ({"test_key_provider": None}, "verified_encrypted_timeline_read_refused"),
        ({"actor_id": "other-fictional-owner"}, "verified_encrypted_timeline_read_refused"),
        (
            {"patient_local_reference": "urn:uuid:00000000-0000-4000-8000-000000000099"},
            "selected_patient_not_found",
        ),
    ],
)
def test_wrong_key_source_audit_actor_selection_or_permission_fail_closed(
    tmp_path: Path, overrides: dict, reason: str
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    with _open(tmp_path / "encrypted", provider) as store:
        imported = _import(store, provider, _source())
        with pytest.raises(SyntheticTimelineError, match=reason):
            _read(store, provider, imported, **overrides)


def test_missing_dates_at_end_and_timezone_day_rollover() -> None:
    source = _source()
    source["entry"][0]["resource"].pop("effectiveDateTime")
    source["entry"][2]["resource"]["period"] = {
        "start": "2026-11-02T23:45:00-05:00",
        "end": "2026-11-03T01:45:00-05:00",
    }
    assert inspect_synthetic_bundle(source)["resource_count"] == 3
    events, patients, undated = _events(source, None)
    assert patients == 1
    assert undated == 1
    assert events == [
        {
            "ordinal": 1,
            "resource_type": "Encounter",
            "day_utc": "2026-11-03",
            "date_available": True,
        },
        {"ordinal": 2, "resource_type": "Observation", "day_utc": None, "date_available": False},
    ]


@pytest.mark.parametrize(
    "field,value,reason",
    [
        (
            "effectiveDateTime",
            "2026-11-03T00:10:00",
            "timeline_observation_timezone_timestamp_required",
        ),
        ("effectiveDateTime", "2026-02-30T00:10:00Z", "timeline_observation_invalid"),
        ("effectiveDateTime", "2026-11-03", "timeline_observation_timezone_timestamp_required"),
        (
            "effectiveDateTime",
            "2026-11-03T00:00:00+2500",
            "timeline_observation_timezone_timestamp_required",
        ),
        (
            "effectiveDateTime",
            "2026-11-03T00:10:00Z " + SECRET,
            "timeline_observation_timezone_timestamp_required",
        ),
        ("effectiveDateTime", 1762100000, "timeline_observation_timezone_timestamp_required"),
    ],
)
def test_invalid_observation_dates_refuse_without_leaking(
    field: str, value: object, reason: str
) -> None:
    source = _source()
    source["entry"][0]["resource"][field] = value
    with pytest.raises(SyntheticTimelineError, match=reason) as err:
        _events(source, None)
    assert SECRET not in str(err.value)


@pytest.mark.parametrize(
    "period,reason",
    [
        ({"end": "2026-11-03T00:01:00Z"}, "timeline_encounter_period_start_required"),
        (
            {"start": "2026-11-03T04:00:00Z", "end": "2026-11-03T02:00:00Z"},
            "timeline_encounter_period_reversed",
        ),
        ({"start": "2026-11-03T02:00:00"}, "timeline_encounter_timezone_timestamp_required"),
        ({"start": "2026-12-90T02:00:00Z"}, "timeline_encounter_invalid"),
        (
            {"start": "2026-11-03T02:00:00Z", "unreviewed": SECRET},
            "timeline_encounter_period_refused",
        ),
    ],
)
def test_invalid_encounter_intervals_refuse(period: object, reason: str) -> None:
    source = _source()
    source["entry"][2]["resource"]["period"] = period
    with pytest.raises(SyntheticTimelineError, match=reason) as err:
        _events(source, None)
    assert SECRET not in str(err.value)


def _second_patient() -> dict:
    source = _source()
    source["entry"].append(
        {
            "fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000004",
            "resource": {
                "resourceType": "Patient",
                "id": "invented-second-patient",
                "active": True,
            },
        }
    )
    return source


def test_two_patient_selection_explicit_and_no_identity_emitted() -> None:
    source = _second_patient()
    inspect_synthetic_bundle(source)
    with pytest.raises(SyntheticTimelineError, match="explicit_patient_selection_required"):
        _events(source, None)
    one, total, undated = _events(source, PATIENT_URL)
    assert total == 2 and undated == 0
    assert len(one) == 2
    other, _, _ = _events(source, source["entry"][-1]["fullUrl"])
    assert other == []
    assert PATIENT_URL not in json.dumps(one)


def test_cross_patient_observation_encounter_link_refused_at_both_boundaries() -> None:
    source = _second_patient()
    # The early Core Bundle preflight must now reject cross-patient
    # Encounter ownership, while the independent timeline guard remains
    # in force as defense in depth for unreviewed downstream sources.
    source["entry"][2]["resource"]["subject"]["reference"] = source["entry"][-1]["fullUrl"]
    with pytest.raises(BundlePreflightError, match="observation_encounter_patient_mismatch"):
        inspect_synthetic_bundle(source)
    with pytest.raises(SyntheticTimelineError, match="cross_patient_encounter_link_refused"):
        _events(source, PATIENT_URL)


def test_public_cli_uses_true_encrypted_workspace_and_removes_temp(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert public_cli(["fhir", "timeline-demo", "--synthetic-only", "--ephemeral-demo"]) == 0
    out = capsys.readouterr()
    assert out.err == ""
    summary = json.loads(out.out)
    assert summary["status"] == "SYNTHETIC_SOURCE_VERIFIED_TIMELINE_PASS"
    assert summary["event_count"] == 2
    assert summary["audit_events_verified"] == 2
    assert summary["closed_and_reopened"] is True
    assert summary["ephemeral_store_removed"] is True
    assert [item["resource_type"] for item in summary["timeline"]] == ["Encounter", "Observation"]
    assert [item["day_utc"] for item in summary["timeline"]] == ["2026-11-03", "2026-11-03"]
    for key in (
        "patient_identity_included",
        "resource_payload_included",
        "fhir_r4_conformance_validated",
        "clinical_use_authorized",
        "release_authorized",
    ):
        assert summary[key] is False
    for marker in (SECRET, "fictional-", "urn:uuid:", "valueString", "patient_local_reference"):
        assert marker not in out.out


@pytest.mark.parametrize(
    "tokens",
    [
        [],
        ["--synthetic-only"],
        ["--ephemeral-demo"],
        ["--synthetic-only", "--ephemeral-demo", "--input", SECRET],
        ["--synthetic-only", "--synthetic-only"],
        ["--ephemeral-demo", "--synthetic-only"],
        ["--synthetic-only", "--ephemeral-demo", SECRET],
    ],
)
def test_cli_disallows_user_supplied_fhir_input_secrets_and_wrong_flags(
    capsys: pytest.CaptureFixture[str], tokens: list[str]
) -> None:
    assert public_cli(["fhir", "timeline-demo", *tokens]) == 2
    out = capsys.readouterr()
    assert out.out == ""
    assert "exact_synthetic_ephemeral_flags_required" in out.err
    assert SECRET not in out.err


def test_timeline_help_is_nonclinical(capsys: pytest.CaptureFixture[str]) -> None:
    assert public_cli(["fhir", "timeline-demo", "--help"]) == 0
    out = capsys.readouterr()
    assert "NO patient files" in out.out
    assert out.err == ""


def test_real_encrypted_multi_patient_selection_and_cross_person_mismatch(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    source = _second_patient()
    root = tmp_path / "encrypted"
    with _open(root, provider) as store:
        imported = _import(store, provider, source)
        with pytest.raises(SyntheticTimelineError, match="explicit_patient_selection_required"):
            _read(store, provider, imported)
        selected = _read(store, provider, imported, patient_local_reference=PATIENT_URL)
        assert selected["patient_count"] == 2
        assert selected["event_count"] == 2
        assert selected["selection_mode"] == "explicit_local_reference"
        assert PATIENT_URL not in json.dumps(selected)

    mismatched = _second_patient()
    mismatched["entry"][2]["resource"]["subject"]["reference"] = mismatched["entry"][-1]["fullUrl"]
    with pytest.raises(BundlePreflightError, match="observation_encounter_patient_mismatch"):
        inspect_synthetic_bundle(mismatched)
    with _open(tmp_path / "mismatched", provider) as store:
        with pytest.raises(
            SyntheticWorkspaceImportError, match="synthetic_bundle_preflight_refused"
        ):
            _import(store, provider, mismatched)
        # Failure must happen before *any* encrypted resource/provenance write.
        assert store.object_count() == 0


def test_real_encrypted_invalid_observation_date_fails_closed(
    tmp_path: Path,
) -> None:
    provider = InMemoryTestKeyProvider(new_root_secret())
    source = _source()
    source["entry"][0]["resource"]["effectiveDateTime"] = "2026-02-30T04:00:00Z"
    with _open(tmp_path / "encrypted", provider) as store:
        imported = _import(store, provider, source)
        with pytest.raises(SyntheticTimelineError, match="timeline_observation_invalid"):
            _read(store, provider, imported)
        assert store.object_count() == 8
