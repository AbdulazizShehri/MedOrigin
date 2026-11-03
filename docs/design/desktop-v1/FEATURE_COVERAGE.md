# MedOrigin Desktop — complete feature-to-screen coverage contract
**Source baseline:** `AbdulazizShehri/MedOrigin` canonical `main` at `dd84bb7` (2026-10-23) plus experimental PRs reviewed 2026-11-03. **Not a statement of delivered desktop features.**

The goal is **full navigational coverage and honest capability integration**, not pretending every planned clinical function is enabled. A Python API can be complete for synthetic-fixture research and still have **no authorized desktop/clinical experience**.

## Status keys
- **FOUNDATION**: matching implemented Python Workspace/Core code or test/contract exists. Desktop connection is separately required.
- **EXPERIMENT**: isolated Windows/Rust/Tauri engineering experiment, not production.
- **DESIGNED**: UI screen may be implemented safely using synthetic fixtures once approved; no backend claim.
- **GATED**: no real clinical/model/network authority; disable with explanation, don't disguise as ready.
- **DEFERRED**: outside the currently authorized scope.

## Left-navigation IA — one brand, all major capability groups

| Section / screen | Source-backed modules or spec | Desktop interaction contract | State / gate |
|---|---|---|---|
| **Home** | `apps/workspace/README.md`, README | Workspace health, local/offline state, pinned tasks, recent **synthetic** work | DESIGNED |
| **Synthetic patients** | `identity.py`, `binding.py`, `patient_graph.py` | synthetic records list, search, provenance, contextual detail | FOUNDATION; UI adapter pending |
| **Encounter detail** | `encounter.py`, `review.py` | encounter timeline, status, source drilldown, reviewed/edit history | FOUNDATION; fixtures only |
| **Audio & transcript** | `asr.py`, specs/medscale-clinical-workspace-v1/capability_map.md (4.1) | transcript review and adapter status; **no live microphone unless separately qualified** | FOUNDATION contract; capture GATED |
| **Clinical note drafts** | `draft.py`, `review.py` | source-linked editable draft, missing-information indicators, review-only state | FOUNDATION; synthetic-only |
| **Orders / tasks** | specs/medscale-clinical-workspace-v1/capability_map.md (4.2) | explicit suggestion list, NO auto-submit; manual review gate | DESIGNED; external write GATED |
| **Coding suggestions** | specs/medscale-clinical-workspace-v1/capability_map.md | source/rationale and human acknowledgement, no billing submission | DEFERRED/GATED |
| **Clinical evidence** | `retrieval.py`, `corpus.py`, `evidence_strength.py` | query, sources, frozen snapshot, citations, contradictions, abstention | FOUNDATION; not a medical answer guarantee |
| **Literature screening** | `src/medscale/litdb`, `screen.py` | results, screening criteria, provenance and reproducible export preview | FOUNDATION; read-only first |
| **FHIR workspace** | `fhir_r4.py`, `src/medscale/fhirkit` | bounded FHIR R4 validation with errors & provenance, export preview | FOUNDATION; synthetic-only |
| **FHIR fixture inspector** | D1 Tauri and D2 native Rust experiments | native synthetic FHIR examples with verified hashes | EXPERIMENT; do not conflate with full validator |
| **Patient graph** | `patient_graph.py`, `linked_workspace.py` | timeline/graph, source labels, extracted vs inferred edges | FOUNDATION; synthetic only |
| **Patient timeline** | `patient_graph.py`, `encounter.py` | chronological events, drilldown and visible uncertainty | FOUNDATION |
| **Documents & canvas** | `draft.py`, `corpus.py`, specs/medscale-clinical-workspace-v1/capability_map.md | structured notes, source links, local object blocks | PARTIAL FOUNDATION / DESIGNED |
| **Tables & structured data** | `dataset.py`, `analytics.py` | queryable local tables, export preview, boundaries | FOUNDATION |
| **Local search** | `retrieval.py`, `corpus.py` | exact scope, readable result provenance, offline errors | FOUNDATION |
| **Analytics** | `analytics.py` | Workspace-only indicators, local calculations, provenance | FOUNDATION; no telemetry to Research |
| **Dataset manager** | `dataset.py`, `src/medscale/dataset` | distinguish Research dataset and Workspace export staging | FOUNDATION; no implicit cross-domain copy |
| **Export quarantine** | `nobackflow.py`, `dataset.py`, `lifecycle.py` | explicit target, preview, residual-risk result, quarantine manifest | FOUNDATION; Research admission GATED |
| **Research explorer** | `research_view.py`, `src/medscale/research` | read-only hypotheses, experiment artifacts, source-bound status | FOUNDATION; **read-only** |
| **Benchmark & evaluation** | `src/medscale/bench`, `mesc`, `modelkit` | inspect trusted results and frozen evaluator versions | FOUNDATION; training/model promotion GATED |
| **Model catalog & runtime** | `modelkit`, `asr.py` | available local adapters and identity; never claim installed models | PARTIAL FOUNDATION; execution GATED |
| **Integrations** | `connector.py`, `fhir_r4.py` | capability listing, consent/permissions, read-only dry run | FOUNDATION contracts; EHR read later, EHR write GATED |
| **Audit history** | `audit.py`, `provenance.py` | append-only events, source identity, revision and failure traces | FOUNDATION |
| **Storage & recovery** | `storage.py`, `lifecycle.py`, `keyprovider.py` | encrypted local store, backup/restore quarantine, key status, safe deletion | FOUNDATION; platform secret provider must qualify |
| **Settings** | `versions.py`, brand/architecture | System/Light/Dark, density, keyboard shortcuts, offline state | DESIGNED |
| **About & diagnostics** | core version, `CITATION.cff`, lockfiles | explicit app/engine build hashes, provenance, no PHI in logs | DESIGNED |
| **Help & safety boundaries** | `SECURITY.md`, governance | research-only, synthetic-only, no EHR writes, clear incident workflow | REQUIRED |

## Nonnegotiable UX statuses

All backend-facing screens must distinguish `available`, `fixture-only`, `not-implemented`, `permission-required`, `offline-unavailable`, `blocked-by-governance`, and `error`. Do not render disabled medical features as active buttons.

All data-dependent screens need explicit empty, loading, failed, unauthorized and corrupt-state variants. Never create sample medical information that appears real; identify it as fictitious/synthetic, with reproducible fixture ID.

## Four end-to-end qualification journeys

1. **Encounter:** synthetic patient → encounter → fixture transcript → source-linked draft → review → FHIR preview → audit replay.
2. **Evidence:** evidence query → frozen retrieval snapshot → citations → strength/contradictions → abstention → provenance.
3. **Context:** synthetic FHIR → normalized objects → graph/timeline → derived-vs-extracted path inspection.
4. **Export:** Workspace selection → explicit quarantine export → risk controls → Domain X manifest → **STOP (no Research admission)**.

## Acceptance matrix before "all features are included"

- Every listed section has an executable route or an accurately labeled disabled state.
- Every green/active feature invokes a versioned, tested and allowlisted backend command.
- Each route has at least one synthetic E2E test and keyboard/a11y coverage.
- No hidden Python import of Research Core from Workspace; no telemetry/training backflow.
- Training, PHI, clinical deployment, model promotion, billing, EHR write, external sync and real patient data remain unavailable until separate formal authorization.
- Build receipts distinguish **UI implemented**, **backend connected**, **qualified with synthetic fixtures**, and **clinically authorized**. The first three never imply the last.
