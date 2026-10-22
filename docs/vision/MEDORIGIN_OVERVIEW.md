# MedOrigin — Project Overview

> **Every medical AI output deserves an origin.**

**MedOrigin** is open-source infrastructure for verifiable medical AI research and a local-first clinical workspace foundation.

The aim is to make every significant output inspectable: **which data was used, which source supports a claim, what the software inferred, which transformations were performed, and what an independent reviewer can reproduce.**

## Two deliberately isolated domains

- **Research Core:** reproducible literature/evidence workflows, synthetic datasets, deterministic FHIR and benchmark contracts, governed model experiments, and source-linked artifacts.
- **Clinical Workspace:** local, synthetic-only Python interfaces for encounter records, draft review, evidence, patient timelines/graphs, analytics and dataset export containment.

No patient/workspace records may silently flow into Research Core training or evaluation. The current Workspace is **not a finished desktop or web application**. PHI ingestion, clinical production, external EHR writes, and model promotion are **not authorized**.

## Current capabilities and limits

The repository has substantial verified engineering foundations, but its scientific runtime and model-development completion are separate decisions. In particular, **MRL-0809** trusted runtime feasibility and **MRL-0899** real-experiment readiness remain open. The consumed Colab Recovery-3 exception provides no retry authority; Kaggle follows separate qualification and authorization.

Read the [roadmap](../../ROADMAP.md), [research-loop task ledger](../../specs/mesc-research-loop-v1/tasks.md), and [Clinical Workspace task ledger](../../specs/medscale-clinical-workspace-v1/tasks.md) for authoritative details. Source-specific governance and test evidence always outrank this overview.

## Identity and continuity

**MedOrigin** is the sole current public project and repository identity.
Existing Python import and command paths remain stable for backward compatibility;
use `uv run medscale --help` for the current developer CLI. Technical identifiers,
experiment receipts, and earlier versioned decisions remain immutable where they
are required for reproducibility.

See the [MedOrigin architecture](../architecture/medorigin_architecture.md),
[compatibility policy](../BRAND_TRANSITION.md), and [roadmap](../../ROADMAP.md)
for a clear distinction between public product identity and historical research
records. Proposed public API renames require a compatibility plan, tests, and
their own governed approval.

## Get started and contribute

Clone [MedOrigin](https://github.com/AbdulazizShehri/MedOrigin), follow the [developer guide](../guides/developer_guide.md), and validate every research assertion through actual test and evidence artifacts. Read the [identity policy](../BRAND_TRANSITION.md), [contributing](../../CONTRIBUTING.md), and [third-party provenance policy](../../THIRD_PARTY_NOTICES.md). Reusing externally sourced code requires rights review and preservation of applicable notices; branding does not erase upstream authorship.
