"""Redacted, FHIR-shaped OperationOutcome for offline R4 *structural* findings.

The output uses fixed, bounded FHIR R4 issue codes and diagnostics with no
resource payload, path, value, patient/clinician identifier, or filesystem
path. It is NOT evidence of full FHIR R4 or clinical conformance.
"""

from __future__ import annotations

import json

from medscale.fhirkit.r4_schema import (
    MAX_REPORTED_ERRORS,
    PARTIAL_COVERAGE_WARNING,
)
from medscale.fhirkit.report import ValidationReport

_ALLOWED_VALIDATOR_KEYWORDS = frozenset(
    {
        "additionalItems",
        "additionalProperties",
        "allOf",
        "anyOf",
        "const",
        "contains",
        "dependencies",
        "enum",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "format",
        "items",
        "maxItems",
        "maxLength",
        "maxProperties",
        "maximum",
        "minItems",
        "minLength",
        "minProperties",
        "minimum",
        "multipleOf",
        "not",
        "oneOf",
        "pattern",
        "patternProperties",
        "properties",
        "propertyNames",
        "required",
        "type",
        "uniqueItems",
        "$ref",
    }
)
_PREFIX = "r4_json_schema_structural_error:"
_TRUNCATED = "r4_json_schema_additional_errors_not_reported"
_REPORT_VALIDATOR_NAME = "hl7-fhir-r4-json-schema-structural-only"
_REPORT_VALIDATOR_VERSION = "R4-4.0.1/jsonschema-4.25.1"
_WARNING = (
    "Structural-only JSON Schema result; not FHIR R4 conformance. "
    "Profiles, terminology, invariants, cross-references and clinical "
    "safety remain unverified."
)


class StructuralOutcomeError(ValueError):
    """A fixed redacted contract refusal; no diagnostic input is echoed."""


def structural_outcome_for_report(report: ValidationReport) -> dict[str, object]:
    """Convert only a source-pinned offline R4 structural report.

    Every diagnostic is constructed from fixed syntax keywords; raw
    jsonschema exception text and JSON paths/values are never propagated.
    The full clinical-conformance caveat is always returned as a warning.
    """
    if (
        type(report) is not ValidationReport
        or report.validator_name != _REPORT_VALIDATOR_NAME
        or report.validator_version != _REPORT_VALIDATOR_VERSION
        or report.status not in ("invalid", "not_validated")
        or report.warnings != (PARTIAL_COVERAGE_WARNING,)
        or not isinstance(report.errors, tuple)
        or len(report.errors) > MAX_REPORTED_ERRORS + 1
        or (report.status == "invalid") != bool(report.errors)
    ):
        raise StructuralOutcomeError("unqualified_r4_structural_report_refused")
    issues: list[dict[str, object]] = []
    for index, raw in enumerate(report.errors):
        if not isinstance(raw, str):
            raise StructuralOutcomeError("unqualified_r4_diagnostic_refused")
        if raw == _TRUNCATED:
            if index != len(report.errors) - 1 or index != MAX_REPORTED_ERRORS:
                raise StructuralOutcomeError("unqualified_r4_diagnostic_refused")
            message = "Further structural errors were omitted after the fixed limit."
        else:
            if not raw.startswith(_PREFIX):
                raise StructuralOutcomeError("unqualified_r4_diagnostic_refused")
            keyword = raw[len(_PREFIX) :]
            if keyword not in _ALLOWED_VALIDATOR_KEYWORDS:
                raise StructuralOutcomeError("unqualified_r4_diagnostic_refused")
            message = "FHIR R4 JSON Schema structural keyword: " + keyword
        issues.append(
            {
                "severity": "error",
                "code": "structure",
                "details": {"text": message},
            }
        )
    issues.append(
        {
            "severity": "warning",
            "code": "informational",
            "details": {"text": _WARNING},
        }
    )
    return {"resourceType": "OperationOutcome", "issue": issues}


def structural_outcome_to_json(report: ValidationReport) -> str:
    """Canonical-ish stable JSON serialization, with no data-bearing fields."""
    return (
        json.dumps(
            structural_outcome_for_report(report),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    )
