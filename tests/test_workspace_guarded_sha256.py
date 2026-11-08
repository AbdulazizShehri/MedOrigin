"""Regression: guarded Workspace SHA-256 admission must stay ASCII exact."""

# mypy: disable-error-code="import-not-found"
# The Workspace package under apps/workspace is deliberately outside strict mypy's
# file set while Issue #464 item 1 is open; it is imported at runtime. Declaring
# the missing import here keeps that deferral explicit.

from types import ModuleType

import pytest
from medscale_workspace import fhir_batch, fhir_catalog, fhir_readback, fhir_structural_receipt


@pytest.mark.parametrize(
    "module", [fhir_batch, fhir_catalog, fhir_readback, fhir_structural_receipt]
)
def test_guarded_sha256_ascii_exact(module: ModuleType) -> None:
    check = module._is_lower_sha256
    assert check("0" * 64)
    assert check("abcdef0123456789" * 4)
    for value in (
        "",
        "0" * 63,
        "0" * 65,
        "A" * 64,
        "g" * 64,
        "0" * 63 + "\n",
        "0" * 63 + "\x00",
        "0" * 63 + "ï¼",
        "0" * 63 + "Ã©",
        "0" * 63 + "â°",
        123,
        None,
        b"0" * 64,
    ):
        assert not check(value)
