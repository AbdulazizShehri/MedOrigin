"""Explicit, synthetic-only evidence export for the native Developer Beta demo.

The export holds only validated status and SHA-256 digests, not a patient
record, original FHIR JSON, file paths, Workspace identifiers or PHI.
Writing uses exclusive creation and never overwrites an existing file.
"""

from __future__ import annotations

import json
import re
from contextlib import suppress
from pathlib import Path
from typing import Any

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_WORKSPACE = {"version": "0.1.0.dev1", "mode": "SYNTHETIC / offline-shell"}


def build_receipt(result: object, *, case_verified: bool = False) -> dict[str, Any]:
    """Reject ambiguous or unqualified results before exposing export bytes."""
    if not isinstance(result, dict) or set(result) != {"fhir", "workspace"}:
        raise ValueError("demo result has unexpected keys")
    fhir = result["fhir"]
    if not isinstance(fhir, dict) or set(fhir) != {"status", "report_sha256", "fixture_sha256"}:
        raise ValueError("synthetic FHIR result has unexpected fields")
    if fhir["status"] != "VALID":
        raise ValueError("synthetic structural validation was not successful")
    report = fhir["report_sha256"]
    fixture = fhir["fixture_sha256"]
    if not all(isinstance(value, str) and _SHA.fullmatch(value) for value in (report, fixture)):
        raise ValueError("synthetic evidence digest is invalid")
    workspace = result["workspace"]
    if workspace is not None and (not isinstance(workspace, dict) or workspace != _WORKSPACE):
        raise ValueError("optional Workspace result is not synthetic-safe")
    if type(case_verified) is not bool:
        raise ValueError("case-verification flag must be Boolean")
    if case_verified and workspace is None:
        raise ValueError("no installed synthetic Workspace was verified")
    return {
        "schema": "medorigin-synthetic-desktop-evidence/v1",
        "project": "MedOrigin",
        "distribution": "medscale 0.3.0",
        "data_class": "SYNTHETIC",
        "validation_kind": "local structural fixture check, not complete HL7 FHIR conformance",
        "fhir": {
            "status": "VALID",
            "report_sha256": report,
            "synthetic_fixture_sha256": fixture,
        },
        "workspace": {
            "installed_synthetic_shell": workspace is not None,
            "synthetic_case_preview_verified": case_verified,
        },
        "clinical_use_authorized": False,
        "publication_authorized": False,
        "independent_review_completed": False,
    }


def save_receipt_new(destination: Path, result: object, *, case_verified: bool = False) -> str:
    """Write validated synthetic evidence once; fail safely if file exists."""
    receipt = build_receipt(result, case_verified=case_verified)
    if destination.suffix.lower() != ".json" or not destination.parent.is_dir():
        raise ValueError("choose a new JSON file in an existing local directory")
    payload = (json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode(
        "utf-8"
    )
    # Exclusive creation is atomic at the filesystem name boundary (wx is
    # deliberately not used with a tempfile rename that could replace output).
    created = False
    try:
        with destination.open("xb") as file:
            created = True
            file.write(payload)
        return "SYNTHETIC_EVIDENCE_EXPORTED"
    except Exception:
        if created:
            with suppress(OSError):
                destination.unlink()
        raise
