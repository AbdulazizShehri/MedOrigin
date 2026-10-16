"""Synthetic FHIR JSON byte-envelope regression tests (issue #567)."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))

fhir = importlib.import_module("medscale_workspace.fhir_r4")


def test_invalid_encoding_fails_closed_at_parse_stage() -> None:
    for payload in (bytes([0xFF]), bytearray([0xFF])):
        report = fhir.validate_payload(fhir.FhirResourceType.PATIENT, "synthetic", payload)
        assert report.stage("parse").evaluated
        assert not report.stage("parse").passed
        assert "not JSON" in report.stage("parse").detail
        assert not report.stage("structure").evaluated
        assert not report.stage("profile").evaluated


def test_oversized_byte_payload_refused_before_json_parse() -> None:
    oversized = b" " * (fhir.MAXIMUM_RESOURCE_BYTES + 1)
    for payload in (oversized, bytearray(oversized)):
        report = fhir.validate_payload(fhir.FhirResourceType.PATIENT, "synthetic", payload)
        assert not report.stage("parse").passed
        assert "exceeds the admitted resource size" in report.stage("parse").detail


def test_boundary_sized_json_byte_payload_is_accepted() -> None:
    payload = b'{"resourceType":"Patient","id":"synthetic","active":true}'
    payload += b" " * (fhir.MAXIMUM_RESOURCE_BYTES - len(payload))
    assert len(payload) == fhir.MAXIMUM_RESOURCE_BYTES
    for raw in (payload, bytearray(payload)):
        report = fhir.validate_payload(fhir.FhirResourceType.PATIENT, "synthetic", raw)
        assert report.stage("parse").passed
        assert report.stage("structure").passed
        assert report.stage("profile").passed


def test_unicode_string_payload_preserves_encoded_size_limit() -> None:
    payload = '{"resourceType":"Patient","id":"synthetic","active":true}'
    payload += " " * (fhir.MAXIMUM_RESOURCE_BYTES - len(payload) - 1) + "\u00e9"
    report = fhir.validate_payload(fhir.FhirResourceType.PATIENT, "synthetic", payload)
    assert not report.stage("parse").passed
    assert "exceeds the admitted resource size" in report.stage("parse").detail


def test_unpaired_unicode_surrogate_fails_closed() -> None:
    payload = '{"resourceType":"Patient","id":"synthetic","active":true}'
    payload += chr(0xD800)
    report = fhir.validate_payload(fhir.FhirResourceType.PATIENT, "synthetic", payload)
    assert not report.stage("parse").passed
    assert "not JSON" in report.stage("parse").detail
