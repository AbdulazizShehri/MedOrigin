# MedOrigin Model Registry

- **Status:** Canonical registry (governed by [ADR-0006](../adr/0006-model-access-strategy.md);
  structured-artifact design governed by [ADR-0012](../adr/0012-layered-architecture-model.md))
- **Date:** 2026-07-10
- **Related:** [AI model strategy](../architecture/ai_model_strategy.md),
  [model card schema](schemas/model_card_schema.md),
  [ecosystem analysis](../architecture/ecosystem_analysis.md)

This is the human narrative of the registry; the **enforceable twin is
`medscale.modelkit.registry`** (ADR-0015), where the tier/role invariants are
constructor errors, not prose. Every row records licence, tier, role, and a verified
source before it may inform any decision. The two must stay consistent — the code is
authoritative for eligibility, this document for rationale.

## 1. Where MedOrigin sits in the medical-AI ecosystem

MedOrigin is **infrastructure and evaluation**, not a foundation model. It *consumes* the
layers below and makes their claims verifiable; it competes with none of them.

| Ecosystem layer | Examples | MedOrigin's relation |
|---|---|---|
| Foundation models | MedGemma, BioMistral, PubMedBERT, ClinicalBERT | Evaluation subjects; Tier-1 generative models are adapter bases |
| Model and artifact sources | Verified, individually identified research models | Evaluation-only candidates with explicit license, revision, and evidence requirements |
| Standards | FHIR, openEHR, SNOMED, ICD | FHIR canonical; others via boundary adapters / interface (ADR-0008) |
| Evidence | PubMed, ClinicalTrials.gov, Cochrane | Ingestion sources for litdb (licence-gated; Cochrane metadata-only) |
| **Evaluation** | **MedScale-Bench** | **MedScale owns this** |
| **Infrastructure** | **MedScale** | **The verifiable substrate the rest is measured on** |

## 2. Two axes: licence tier × role

A model's admissibility is decided on two independent axes. Conflating them is a common
error — an encoder is not a smaller generator, and a permissive licence does not make a
model fit for a job it cannot do.

### Axis A — licence tier (may it ship in an artifact?)

| Tier | Criterion | Permitted roles |
|---|---|---|
| **1 — clean-permissive** | OSI-style licence permitting derivatives + commercial use, no terms passthrough | Base for released MESC adapters; any evaluation role |
| **2 — conditional terms** | Derivatives + commercial permitted, but with passthrough / use policy (e.g. HAI-DEF) | Evaluation/comparison only; adapter base **only** via a dedicated ADR accepting the passthrough |

Rationale: a Tier-2-derived released adapter would impose upstream terms on every MedScale
consumer, silently narrowing the Apache-2.0 promise (R3's spirit, not only its letter).

### Axis B — role (what job can it do?)

MedScale's core task — generating FHIR JSON under a grammar — is **generative**, so only
generative models can be MESC bases. Encoders cannot generate; their value is deterministic
extraction.

| Role | Job in MedScale | Eligible kind |
|---|---|---|
| **Generative base** | MESC adapter base; constrained-decoding subject | Decoder / seq2seq LLMs (Tier 1 to release) |
| **Reasoning reference** | Benchmark comparison only | Generative, any tier (eval-only) |
| **Extraction / NER baseline** | T-EXTRACT non-LLM baseline; RQ5 span fixtures | Encoder token-classifiers |
| **Embedding / retrieval** | Deferred (no v0 RAG); only where provenance is checkable | Encoders — H2+ |

## 3. Active registry entries

The registry entries below are research/evaluation candidates with recorded
licenses and source identifiers; they are **not MedOrigin-developed models**
and their presence is not an endorsement, download instruction, or permission
to publish their weights.

**Registry maintenance (2026-10-22):** a prior unpinned, family-level NER
placeholder was retired from the live executable catalogue because it did
not identify a concrete model revision or reproducible runtime integration.
Two individually identified encoder baselines remain. The original research
decision and comparative notes remain unchanged in historical ADRs and
architecture records; removing a non-executable catalogue placeholder is
not deletion of provenance.


| Model | Kind | Licence (tier) | Role | Provenance / note |
|---|---|---|---|---|
| BioMistral-7B | Generative (Mistral) | Apache-2.0 (T1) | Generative base candidate; comparison | Trained on PMC-OA; authors warn against clinical use |
| MedGemma 4B / 27B, MedSigLIP | Generative / multimodal | HAI-DEF (T2) | Eval/comparison; base only via ADR | Google Health AI Developer Foundations terms (passthrough) |
| Bio_ClinicalBERT | Encoder | MIT (T1) | Extraction/NER baseline | Trained on **MIMIC-III** (de-identified, credentialed). Weights are a released MIT artifact — using them as a baseline does **not** put MIMIC data into MedScale (R2 intact); provenance stated for transparency |
| PubMedBERT / BiomedBERT | Encoder | MIT (T1) | Extraction/NER baseline; embedding (H2+) | Pretrained on public PubMed + PMC |

| Qwen3 (0.6B–32B) | Generative | Apache-2.0 (T1) | Generative base candidate; comparison | Active family; 32K ctx; licence verified at 8B card |
| Mistral-7B-Instruct-v0.3 | Generative | Apache-2.0 (T1) | Generative base candidate; comparison | ⚠️ newer Mistral models may be MRL — verify per model, never per family |
| DeepSeek-R1 | Generative MoE | MIT (T1, licence only) | Comparison (API/hosted) — far beyond compute ceiling | Distillation explicitly permitted; **R1-Distill variants inherit their base licence** (Qwen2.5→T1, Llama→T2) |
| Llama 3.1 (8B) | Generative | Llama 3.1 Community License (T2) | Eval/comparison only | Not OSI: passthrough + "Built with Llama" branding + derivative name-prefix + 700M-MAU clause |
| Meditron-7B | Generative | Llama 2 Community License, inherited (T2) | Eval/comparison only | Sept-2023; PubMed/guidelines pretrain; authors advise against deployment |

**Selection remains empirical at T4** (reserved ADR-0002): the constrained-decoding 2×2
runs on the Tier-1 *generative* pool; medical-QA leaderboard scores are not selection
evidence (MedScale's task is FHIR generation, not exam QA).

## 4. Row requirements (what every entry must carry)

`model_id` · `kind` (generative/encoder/multimodal) · `licence` (SPDX or named terms) ·
`tier` (1/2) · `role` · `revision`+`sha` when actually used · `verified_at` ·
`source_url` · provenance note (training-data lineage, especially any credentialed source).
No row informs a decision until every field is present and the source verified (R1
discipline applied to models).

## 5. `medscale.modelkit.registry` — the machine-readable registry (implemented, ADR-0015)

**Implemented 2026-07-10** under operator directive (pulling forward the structuring the
ADR-0006 compliance clause had deferred to T4). The original design intent below is
retained and was followed:

- **Purpose:** turn §3 into a validated, versioned data file (`registry.json`, canonical
  JSON) that release CI can lint — so a model card's `base_model` must resolve to a
  registry row of the right tier and role before a model release passes
  ([ci_cd §validate-model](../releases/ci_cd.md)).
- **Shape (intended):** a pure, dependency-free module over a committed data file —
  `load_registry() -> tuple[ModelEntry, ...]`, `get(model_id)`, `eligible_bases()`
  (Tier-1 generative), `baselines()` (encoders). No network, no downloads — it records
  *facts about* models, never fetches weights.
- **Build gate:** implement when the first model release (MESC-v0, T6/T7) needs card-lint
  to enforce tier/role mechanically. Until then this table is the registry.

The registry never downloads, hosts, or vendors weights. It is a catalogue of verified
facts, consistent with the PHI boundary and the licence invariant.
