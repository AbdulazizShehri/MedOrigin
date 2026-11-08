"""Real caller-file fictional FHIR -> encrypted Workspace import + cold reopen QA.

All FHIR identities/names here are invented, never real patient information.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, NoReturn

import pytest

from medscale.cli import main as public_cli
from medscale.fhirkit.workspace_demo import _fictional_bundle
from medscale.fhirkit.workspace_file_batch_demo import (
    SyntheticFileImportDemoError,
    run_fictional_file_batch_encrypted_demo,
)
from medscale.fhirkit.workspace_multi_timeline_demo import (
    _second_fictional_timeline_bundle,
)

_SECRET = "INVENTED_PRIVATE_NAME_DO_NOT_ECHO"


def _two() -> list[dict[str, Any]]:
    one: dict[str, Any] = _fictional_bundle()
    one["entry"][1]["resource"]["name"][0]["text"] = _SECRET
    two: dict[str, Any] = _second_fictional_timeline_bundle()
    two["entry"][1]["resource"]["name"][0]["text"] = _SECRET + "_SECOND"
    return [one, two]


def _files(tmp_path: Path, bundle_list: list[dict[str, Any]]) -> list[Path]:
    outputs = []
    for index, bundle in enumerate(bundle_list, 1):
        filepath = tmp_path / f"{_SECRET}-{index}.json"
        filepath.write_text(json.dumps(bundle), encoding="utf-8")
        outputs.append(filepath)
    return outputs


def _cli(files: list[Path]) -> list[str]:
    return [
        "fhir",
        "file-batch-encrypted-demo",
        "--synthetic-only",
        "--ephemeral-demo",
        *(str(file) for file in files),
    ]


def test_real_two_fictional_caller_files_encrypted_cold_reopen_and_audit(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sources = _files(tmp_path, _two())
    before = {source: source.read_bytes() for source in sources}
    assert public_cli(_cli(sources)) == 2
    output = capsys.readouterr()
    assert output.err == ""
    receipt = json.loads(output.out)
    assert receipt["schema"] == "medorigin-core-fictional-file-encrypted-batch-reopen/v1"
    assert receipt["status"] == "FICTIONAL_FILE_BATCH_ENCRYPTED_REOPEN_VERIFIED"
    assert receipt["import_count"] == 2
    assert receipt["resource_count"] == 6
    assert receipt["verified_timeline_event_count"] == 4
    assert receipt["verified_audit_events"] == 2
    assert len(receipt["imports"]) == 2
    assert [x["import_ordinal"] for x in receipt["imports"]] == [1, 2]
    assert [x["resource_count"] for x in receipt["imports"]] == [3, 3]
    assert [x["patient_count_within_import"] for x in receipt["imports"]] == [1, 1]
    assert [x["verified_timeline_event_count"] for x in receipt["imports"]] == [2, 2]
    assert len({x["source_content_sha256"] for x in receipt["imports"]}) == 2
    assert len({x["import_audit_event_digest"] for x in receipt["imports"]}) == 2
    assert len(receipt["current_audit_head_digest"]) == 64
    assert receipt["physically_closed_and_reopened"] is True
    assert receipt["ephemeral_store_removed"] is True
    for flag in (
        "source_filenames_included",
        "patient_identity_included",
        "resource_payload_included",
        "permanent_workspace_created",
        "production_key_provider_used",
        "cross_import_patient_identity_join_performed",
        "network_access_performed",
        "fhir_r4_conformance_validated",
        "clinical_use_authorized",
        "release_authorized",
    ):
        assert receipt[flag] is False
    assert all(source.read_bytes() == before[source] for source in sources)
    assert set(tmp_path.iterdir()) == set(sources)
    for secret in (_SECRET, "fictional-patient", "urn:uuid:", str(sources[0]), str(sources[1])):
        assert secret not in output.out + output.err


def test_second_patient_only_bundle_cold_reopen_does_not_invent_activity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    one, two = _two()
    two["entry"] = [
        entry for entry in two["entry"] if entry["resource"]["resourceType"] == "Patient"
    ]
    sources = _files(tmp_path, [one, two])
    assert public_cli(_cli(sources)) == 2
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["resource_count"] == 4
    assert receipt["verified_timeline_event_count"] == 2
    assert [x["verified_timeline_event_count"] for x in receipt["imports"]] == [2, 0]
    assert receipt["ephemeral_store_removed"] is True


@pytest.mark.parametrize(
    "mutator",
    [
        lambda items: items[1].pop("meta"),
        lambda items: items[1]["entry"][0]["resource"]["subject"].update(
            reference="https://untrusted.invalid/Patient/" + _SECRET
        ),
        lambda items: items[1]["entry"][0]["resource"].update({"unapproved_field": _SECRET}),
    ],
)
def test_second_unqualified_bundle_cannot_trigger_any_encrypted_write(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    mutator: Callable[[list[dict[str, Any]]], object],
) -> None:
    import medscale.fhirkit.workspace_file_batch_demo as module

    sources = _two()
    mutator(sources)
    paths = _files(tmp_path, sources)

    def no_workspace_create(*_a: object, **_kw: object) -> NoReturn:
        raise AssertionError("should never allocate a Workspace on bad preflight")

    monkeypatch.setattr(module, "TemporaryDirectory", no_workspace_create)
    assert public_cli(_cli(paths)) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert "verified_encrypted_fictional_batch_refused" in output.err
    assert _SECRET not in output.err


def test_exact_duplicate_source_is_refused_before_allocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import medscale.fhirkit.workspace_file_batch_demo as module

    first = _two()[0]

    def no_workspace_create(*_a: object, **_kw: object) -> NoReturn:
        raise AssertionError("should refuse duplicate before allocating Workspace")

    monkeypatch.setattr(module, "TemporaryDirectory", no_workspace_create)
    with pytest.raises(SyntheticFileImportDemoError, match="preflight_contract_refused"):
        run_fictional_file_batch_encrypted_demo(
            [first, copy.deepcopy(first)], synthetic_only=True, ephemeral_demo=True
        )


def test_api_requires_two_explicit_demo_permissions() -> None:
    for syn, eph in [(False, False), (True, False), (False, True)]:
        with pytest.raises(SyntheticFileImportDemoError, match="explicit_demo_flags_required"):
            run_fictional_file_batch_encrypted_demo(_two(), synthetic_only=syn, ephemeral_demo=eph)


@pytest.mark.parametrize(
    "payloads",
    [
        [],
        [_fictional_bundle()],
        [_fictional_bundle()] * 5,
        [_fictional_bundle(), None],
    ],
)
def test_api_refuses_invalid_batch_before_workspace(payloads: list[Any]) -> None:
    with pytest.raises(SyntheticFileImportDemoError):
        run_fictional_file_batch_encrypted_demo(payloads, synthetic_only=True, ephemeral_demo=True)


@pytest.mark.parametrize(
    "wrong",
    [
        [],
        ["--synthetic-only"],
        ["--synthetic-only", "--ephemeral-demo", "single"],
        ["--synthetic-only", "a", "b"],
        ["--ephemeral-demo", "--synthetic-only", "a", "b"],
        ["--synthetic-only", "--ephemeral-demo", "a", "--evil"],
        ["--synthetic-only", "--ephemeral-demo", *[str(i) for i in range(5)]],
    ],
)
def test_cli_fail_closed_exact_admission_without_path_echo(
    wrong: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert public_cli(["fhir", "file-batch-encrypted-demo", *wrong]) == 2
    result = capsys.readouterr()
    assert result.out == ""
    assert result.err.strip().endswith("exact_fictional_ephemeral_file_flags_required")
    assert _SECRET not in result.err


def test_missing_second_source_refuses_without_partial_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    paths = _files(tmp_path, _two())
    paths[1].unlink()
    assert public_cli(_cli(paths)) == 1
    result = capsys.readouterr()
    assert result.out == ""
    assert "source_file_refused" in result.err
    assert _SECRET not in result.err


def test_fake_downstream_catalog_content_cannot_escape_into_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from medscale.fhirkit import workspace_catalog

    def poison(*_args: object, **_kwargs: object) -> dict[str, str]:
        return {"status": _SECRET, "patient_name": _SECRET}

    monkeypatch.setattr(workspace_catalog, "list_synthetic_bundle_imports", poison)
    with pytest.raises(
        SyntheticFileImportDemoError, match="fictional_import_cold_reopen_contract_refused"
    ) as error:
        run_fictional_file_batch_encrypted_demo(_two(), synthetic_only=True, ephemeral_demo=True)
    assert _SECRET not in str(error.value)


def test_public_help_is_explicitly_ephemeral_and_not_clinical(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert public_cli(["fhir", "file-batch-encrypted-demo", "--help"]) == 0
    output = capsys.readouterr()
    assert "NO permanent import" in output.out
    assert "FICTIONAL_BUNDLE_4" in output.out
    assert output.err == ""
