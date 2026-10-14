"""Fail-closed FHIR validation results, using synthetic test objects only."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Protocol, cast
from uuid import uuid4

import pytest

WORKSPACE_SRC = Path(__file__).resolve().parents[1] / "apps" / "workspace" / "src"
sys.path.insert(0, str(WORKSPACE_SRC))

fhir = importlib.import_module("medscale_workspace.fhir_r4")
errors = importlib.import_module("medscale_workspace.errors")


class _Validatable(Protocol):
    def validated(self) -> object: ...


def _resource(*, labels: tuple[object, ...] = (), refs: tuple[object, ...] = ()) -> _Validatable:
    """Construct a minimal synthetic resource with deliberately injectable members."""
    return cast(
        _Validatable,
        fhir.FhirResource(
            workspace_id=uuid4(),
            resource_id=uuid4(),
            resource_type=fhir.FhirResourceType.PATIENT,
            fhir_id="test-patient",
            resource_version="synthetic-v1",
            content=(),
            security_labels=labels,
            references=refs,
            patient_id=None,
            source_id=None,
            source_revision=None,
            content_digest=None,
        ),
    )


def test_fhir_rejects_invalid_security_label_validation_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    label = fhir.SecurityLabel(system="urn:synthetic:security", code="test", display="synthetic")
    resource = _resource(labels=(label,))
    monkeypatch.setattr(fhir.SecurityLabel, "validated", lambda _self: None)
    with pytest.raises(errors.FhirInputError, match="SecurityLabel"):
        resource.validated()


def test_fhir_rejects_invalid_reference_validation_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reference = fhir.ResourceReference(
        resource_type=fhir.FhirResourceType.PATIENT, resource_id="other-synthetic"
    )
    resource = _resource(refs=(reference,))
    monkeypatch.setattr(fhir.ResourceReference, "validated", lambda _self: None)
    with pytest.raises(errors.FhirInputError, match="ResourceReference"):
        resource.validated()
