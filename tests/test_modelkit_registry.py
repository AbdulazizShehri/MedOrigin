"""Registry invariants: licence-first eligibility is enforced by types, not prose."""

from __future__ import annotations

import pytest

from medscale.modelkit import (
    REGISTRY,
    ModelEntry,
    ModelKind,
    Role,
    eligible_bases,
    extraction_baselines,
    get_entry,
    validate_registry,
)

_TS = "2026-07-10T00:00:00+00:00"


def test_registry_is_valid() -> None:
    validate_registry()  # raises on violation


def test_every_base_candidate_is_tier1_generative() -> None:
    for entry in eligible_bases():
        assert entry.tier == 1
        assert entry.kind is ModelKind.GENERATIVE


def test_tier2_model_cannot_be_base_candidate() -> None:
    with pytest.raises(ValueError, match="BASE_CANDIDATE requires Tier 1"):
        ModelEntry(
            "llama-x",
            "meta/x",
            ModelKind.GENERATIVE,
            "Llama Community",
            2,
            (Role.BASE_CANDIDATE,),
            _TS,
            "https://example.org",
        )


def test_encoder_cannot_be_base_candidate() -> None:
    with pytest.raises(ValueError, match="generative"):
        ModelEntry(
            "bert-x",
            "org/bert",
            ModelKind.ENCODER,
            "MIT",
            1,
            (Role.BASE_CANDIDATE,),
            _TS,
            "https://example.org",
        )


def test_known_entries_and_lookup() -> None:
    assert get_entry("qwen3-8b").licence == "Apache-2.0"
    assert get_entry("llama-3.1-8b-instruct").tier == 2
    assert get_entry("deepseek-r1").roles == (Role.COMPARISON,)
    with pytest.raises(ValueError, match="unknown model_id"):
        get_entry("gpt-99")


def test_shortlist_matches_landscape_doc() -> None:
    ids = {entry.model_id for entry in eligible_bases()}
    assert ids == {"qwen3-8b", "qwen3-4b", "mistral-7b-instruct-v0.3", "biomistral-7b"}


def test_extraction_baselines_are_encoders() -> None:
    baselines = extraction_baselines()
    assert baselines, "at least one extraction baseline expected"
    for entry in baselines:
        assert entry.kind is ModelKind.ENCODER


def test_extraction_registry_only_exposes_concrete_verified_baselines() -> None:
    """Do not offer a non-executable model-family placeholder to callers."""
    baselines = extraction_baselines()
    assert {entry.model_id for entry in baselines} == {
        "bio-clinicalbert",
        "pubmedbert-base",
    }
    assert not any(entry.model_id.endswith("-family") for entry in baselines)
    assert all(entry.hf_id.count("/") == 1 for entry in baselines)
    for entry in baselines:
        assert get_entry(entry.model_id) is entry


def test_no_duplicate_ids() -> None:
    ids = [entry.model_id for entry in REGISTRY]
    assert len(ids) == len(set(ids))
