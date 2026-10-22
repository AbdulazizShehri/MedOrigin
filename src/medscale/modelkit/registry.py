"""The machine-readable model registry (ADR-0006 tiers/roles, ADR-0015 structured).

This is the code twin of ``docs/models/model_registry.md`` — the documentation table
remains the human narrative; this module is the enforceable form. Facts only: the
registry never downloads, hosts, or vendors weights.

Invariant enforced here, not merely documented: **only Tier-1 generative models can be
adapter-base candidates.** A capability argument cannot promote a Tier-2 model into a
release path — only a dedicated ADR can (by editing this file under review).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Final

from medscale.provenance import validate_timestamp

__all__ = [
    "REGISTRY",
    "ModelEntry",
    "ModelKind",
    "Role",
    "eligible_bases",
    "extraction_baselines",
    "get_entry",
    "validate_registry",
]


class ModelKind(enum.Enum):
    GENERATIVE = "generative"
    ENCODER = "encoder"
    MULTIMODAL = "multimodal"


class Role(enum.Enum):
    BASE_CANDIDATE = "base_candidate"  # may become a released MESC adapter base
    COMPARISON = "comparison"  # benchmark/evaluation subject only
    EXTRACTION_BASELINE = "extraction_baseline"  # encoder NER baselines (RQ5)
    EMBEDDING = "embedding"  # deferred retrieval roles (H2+)


@dataclass(frozen=True)
class ModelEntry:
    """One verified fact-row about an external model."""

    model_id: str
    hf_id: str
    kind: ModelKind
    licence: str
    tier: int
    roles: tuple[Role, ...]
    verified_at: str
    source_url: str
    params_b: float | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if not self.model_id.strip() or not self.hf_id.strip():
            raise ValueError("model_id and hf_id must be non-empty")
        if self.tier not in (1, 2):
            raise ValueError(f"tier must be 1 or 2, got {self.tier}")
        if not self.roles:
            raise ValueError("at least one role is required")
        validate_timestamp(self.verified_at, "verified_at")
        if not self.source_url.startswith("https://"):
            raise ValueError("source_url must be a https URL")
        if Role.BASE_CANDIDATE in self.roles:
            if self.tier != 1:
                raise ValueError(
                    f"{self.model_id}: BASE_CANDIDATE requires Tier 1 (ADR-0006); "
                    "promotion of a Tier-2 model needs a dedicated ADR"
                )
            if self.kind is not ModelKind.GENERATIVE:
                raise ValueError(
                    f"{self.model_id}: BASE_CANDIDATE requires a generative model "
                    "(encoders cannot generate FHIR under grammar)"
                )


_VERIFIED: Final = "2026-07-10T00:00:00+00:00"

#: Entries mirror docs/models/model_registry.md §3 (licences verified 2026-07-10).
REGISTRY: Final[tuple[ModelEntry, ...]] = (
    ModelEntry(
        "qwen3-8b",
        "Qwen/Qwen3-8B",
        ModelKind.GENERATIVE,
        "Apache-2.0",
        1,
        (Role.BASE_CANDIDATE, Role.COMPARISON),
        _VERIFIED,
        "https://huggingface.co/Qwen/Qwen3-8B",
        params_b=8.2,
        note="32K ctx native; active family",
    ),
    ModelEntry(
        "qwen3-4b",
        "Qwen/Qwen3-4B",
        ModelKind.GENERATIVE,
        "Apache-2.0",
        1,
        (Role.BASE_CANDIDATE, Role.COMPARISON),
        _VERIFIED,
        "https://huggingface.co/Qwen/Qwen3-8B",
        params_b=4.0,
        note="licence verified at family 8B card; pin per-model revision at use",
    ),
    ModelEntry(
        "mistral-7b-instruct-v0.3",
        "mistralai/Mistral-7B-Instruct-v0.3",
        ModelKind.GENERATIVE,
        "Apache-2.0",
        1,
        (Role.BASE_CANDIDATE, Role.COMPARISON),
        _VERIFIED,
        "https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3",
        params_b=7.2,
        note="newer Mistral models may be MRL — verify per model, never per family",
    ),
    ModelEntry(
        "biomistral-7b",
        "BioMistral/BioMistral-7B",
        ModelKind.GENERATIVE,
        "Apache-2.0",
        1,
        (Role.BASE_CANDIDATE, Role.COMPARISON),
        _VERIFIED,
        "https://huggingface.co/BioMistral/BioMistral-7B",
        params_b=7.2,
        note="PMC-OA continued pretrain (2024); authors warn against clinical use",
    ),
    ModelEntry(
        "deepseek-r1",
        "deepseek-ai/DeepSeek-R1",
        ModelKind.GENERATIVE,
        "MIT",
        1,
        (Role.COMPARISON,),
        _VERIFIED,
        "https://huggingface.co/deepseek-ai/DeepSeek-R1",
        params_b=671.0,
        note="beyond compute ceiling; hosted-API comparison only; distills inherit base licences",
    ),
    ModelEntry(
        "llama-3.1-8b-instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
        ModelKind.GENERATIVE,
        "Llama 3.1 Community License",
        2,
        (Role.COMPARISON,),
        _VERIFIED,
        "https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct",
        params_b=8.0,
        note="not OSI: passthrough + branding + derivative name prefix + 700M-MAU clause",
    ),
    ModelEntry(
        "medgemma-4b-it",
        "google/medgemma-4b-it",
        ModelKind.MULTIMODAL,
        "Health AI Developer Foundations terms",
        2,
        (Role.COMPARISON,),
        _VERIFIED,
        "https://huggingface.co/google/medgemma-27b-it",
        params_b=4.0,
        note="HAI-DEF passthrough; strongest medical-domain signal in pool",
    ),
    ModelEntry(
        "meditron-7b",
        "epfl-llm/meditron-7b",
        ModelKind.GENERATIVE,
        "Llama 2 Community License",
        2,
        (Role.COMPARISON,),
        _VERIFIED,
        "https://huggingface.co/epfl-llm/meditron-7b",
        params_b=7.0,
        note="2023-era; inherits Llama-2 terms; authors advise against deployment",
    ),
    ModelEntry(
        "bio-clinicalbert",
        "emilyalsentzer/Bio_ClinicalBERT",
        ModelKind.ENCODER,
        "MIT",
        1,
        (Role.EXTRACTION_BASELINE,),
        _VERIFIED,
        "https://huggingface.co/emilyalsentzer/Bio_ClinicalBERT",
        params_b=0.11,
        note="MIMIC-III-trained released artifact; use does not move MIMIC data into MedScale (R2)",
    ),
    ModelEntry(
        "pubmedbert-base",
        "microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext",
        ModelKind.ENCODER,
        "MIT",
        1,
        (Role.EXTRACTION_BASELINE, Role.EMBEDDING),
        _VERIFIED,
        "https://huggingface.co/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract-fulltext",
        params_b=0.11,
        note="public PubMed+PMC pretrain; embedding role is H2+",
    ),
)


def validate_registry(entries: tuple[ModelEntry, ...] = REGISTRY) -> None:
    """Cross-entry invariants (row-level ones live in ``ModelEntry.__post_init__``)."""
    ids = [entry.model_id for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate model_id in registry")
    if not any(entry.tier == 1 and Role.BASE_CANDIDATE in entry.roles for entry in entries):
        raise ValueError("registry must contain at least one Tier-1 base candidate")


def get_entry(model_id: str) -> ModelEntry:
    for entry in REGISTRY:
        if entry.model_id == model_id:
            return entry
    raise ValueError(f"unknown model_id {model_id!r}")


def eligible_bases() -> tuple[ModelEntry, ...]:
    """Models that may become released MESC adapter bases (Tier-1 generative)."""
    return tuple(e for e in REGISTRY if Role.BASE_CANDIDATE in e.roles)


def extraction_baselines() -> tuple[ModelEntry, ...]:
    return tuple(e for e in REGISTRY if Role.EXTRACTION_BASELINE in e.roles)
