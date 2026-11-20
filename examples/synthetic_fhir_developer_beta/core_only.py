"""Truthful local Core-only FHIR provenance for the historical demo.

Reuses the hardened installed-CLI provenance checker. NO static preview,
false green FHIR status, clinical conformance, EHR or release qualification.
The default historical desktop preview path remains separately blocked.
"""

from __future__ import annotations

import importlib.util
import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

SOURCE_ROOT = Path(__file__).resolve().parents[2]
GATE = SOURCE_ROOT / "scripts" / "check_installed_core_fhir_provenance.py"
SCHEMA = "medorigin-core-fhir-provenance-only/v1"
STATUS = "CORE_FHIR_PROVENANCE_ONLY"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_KEYS = frozenset(
    {
        "status",
        "installed_cli_count",
        "execution_mode",
        "known_report_sha256",
        "unknown_report_sha256",
        "fhir_conformance_validated",
        "publication_authorized",
        "clinical_use_authorized",
        "independent_security_review_complete",
        "prepublication_rehearsal_qualified",
    }
)


class CoreOnlyError(ValueError):
    """Fixed non-sensitive local qualification refusal."""


def _qualified_installed_cli(clis: list[Path]) -> dict[str, Any]:
    if not GATE.is_file():
        raise CoreOnlyError("provenance_gate_missing")
    spec = importlib.util.spec_from_file_location("medorigin_core_only_gate", GATE)
    if spec is None or spec.loader is None:
        raise CoreOnlyError("provenance_gate_unavailable")
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    try:
        return gate.qualify(clis)
    except (ValueError, OSError) as exc:
        # Do not emit potentially untrusted CLI messages or host paths.
        raise CoreOnlyError("installed_provenance_gate_refused") from exc


def qualified_receipt(
    clis: list[Path],
    *,
    checker: Callable[[list[Path]], dict[str, Any]] | None = None,
) -> dict[str, object]:
    """Admit only exactly shaped provenance-only evidence, never a release GO.

    The optional injected checker is for isolated source-controlled tests.
    Production calls use the independently tested installed-CLI gate.
    """
    if not 1 <= len(clis) <= 2:
        raise CoreOnlyError("one_or_two_installed_clis_required")
    proof = _qualified_installed_cli(clis) if checker is None else checker(clis)
    if not isinstance(proof, dict) or set(proof) != _KEYS:
        raise CoreOnlyError("unexpected_provenance_evidence")
    if (
        proof["status"] != "LOCAL_FHIR_PROVENANCE_ONLY"
        or type(proof["installed_cli_count"]) is not int
        or proof["installed_cli_count"] != len(clis)
        or proof["execution_mode"] != "unattested_installed_console_shim"
        or any(
            proof[key] is not False
            for key in (
                "fhir_conformance_validated",
                "publication_authorized",
                "clinical_use_authorized",
                "independent_security_review_complete",
                "prepublication_rehearsal_qualified",
            )
        )
    ):
        raise CoreOnlyError("provenance_evidence_not_qualified")
    for name in ("known_report_sha256", "unknown_report_sha256"):
        if not isinstance(proof[name], str) or _HEX.fullmatch(proof[name]) is None:
            raise CoreOnlyError("provenance_report_digest_not_qualified")
    if proof["known_report_sha256"] == proof["unknown_report_sha256"]:
        raise CoreOnlyError("distinct_fictional_cases_share_digest")
    # No arbitrary names or file paths reach the safe receipt, even if
    # a malicious caller provides a checker with extra unexpected fields.
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "scope": "deterministic local FHIR provenance ONLY; not FHIR validation",
        "installed_cli_count": proof["installed_cli_count"],
        "launcher_identity_attested": False,
        "known_report_sha256": proof["known_report_sha256"],
        "unknown_report_sha256": proof["unknown_report_sha256"],
        "fhir_conformance_validated": False,
        "clinical_use_authorized": False,
        "independent_security_review_complete": False,
        "prepublication_rehearsal_qualified": False,
        "publication_authorized": False,
        "preview_generated": False,
    }


def commit_new_receipt(destination: Path, receipt: dict[str, object]) -> Path:
    """Persist only allowed already-verified metadata in a fresh output dir."""
    if destination.exists() or destination.is_symlink():
        raise CoreOnlyError("refusing_to_overwrite_existing_evidence")
    destination.mkdir(parents=True, exist_ok=False)
    record = destination / "core-provenance-only.json"
    with record.open("x", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
    return record
