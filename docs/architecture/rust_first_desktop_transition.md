# MedOrigin — Rust-first desktop transition (proposal)

- **Status:** PROPOSED architecture/implementation sequence; no new runtime is implemented or release authorized by this document
- **Direction:** Founder, 2026-10-28: favor Rust for a future local desktop application, with Python retained for research and AI
- **Scope:** Future nonclinical, offline, synthetic-only product engineering; not the present Python v0.3.0 Developer Beta source candidate
- **Track:** [Software release qualification](../releases/software_release_track.md), [ADR-0013 language strategy](../adr/0013-language-strategy.md), [ADR-0003 repository boundary](../adr/0003-repository-topology.md), [local workspace boundary](../adr/0038-local-clinical-workspace-boundary.md)

## Current reality and non-goals

MedOrigin currently ships a research-oriented Python package with `medscale` distribution/import/CLI compatibility, plus a separately packaged Python synthetic Clinical Workspace foundation. It **does not have** a generally available desktop GUI or an authorized real-patient workflow. The source candidate in [PR #641](https://github.com/AbdulazizShehri/MedOrigin/pull/641) is separately qualified through its existing Python CI; nothing in this proposal supersedes those results or implies a public Beta release.

This is **not** permission to rewrite the Python Research Core, to rename its existing interfaces, to auto-migrate historical data, to include research/training extras in a desktop installer, to enable model inference by default, or to broaden the clinical authorization boundary.

The architectural trigger for a future Rust implementation is a **new local desktop consumer** and a separately evaluated privacy/attack-surface need, not a claim that the already-tested Python implementation is intrinsically slow. No measured speedup or memory reduction is asserted here.

## Proposed end-state boundaries

| Boundary | Proposed technology and responsibility | Must not do |
| --- | --- | --- |
| Desktop shell | **Tauri + TypeScript/React**; signed, separately versioned local application after qualification; UI for synthetic developer workflows only | No production clinician claims, anonymous telemetry, implicit network calls, PHI |
| Local services and persistence | **Rust** for narrowly specified desktop commands, controlled filesystem access, integrity verification, resource limits and optional local storage | No automatic EHR writes, no silently exposed HTTP server, no unsafe generic shell execution |
| FHIR and provenance | A *measured*, separately qualified Rust implementation of individual deterministic functions **only where useful**; compare to Python reference fixtures byte-for-byte | No silently different canonicalization, parser acceptance, provenance or clinical interpretation |
| Research and model adapters | **Python remains canonical** for evaluation/research and potential explicit opt-in model execution | No training/evaluation backflow from Workspace or automatic downloads |
| Cross-language contract | Versioned, bounded request/response messages, explicit errors, source hashes and synthetic-only access class | No unrestricted Python import of the desktop app, private unversioned dicts or cross-layer data backflow |

The Rust desktop shall be a **consumer** of published/versioned, read-only Research Core contracts. Decide whether it belongs in a separately versioned repository or independently isolated package **before creating** a Rust toolchain in the current research repository, consistent with accepted ADR-0003 and the proposed gating in ADR-0013. No Go or cloud service is needed for the first local build.

A future Python worker, if actually required for optional offline AI, must be a separately launched, explicitly opted-in and version-checked local subprocess with a bounded message protocol, no default network access, limited filesystem permissions and deterministic shutdown. Do **not** bundle GPU runtimes, models or research extras in the base installer.

## First testable vertical slice (not yet built)

1. **D0 — contracts, baseline and threat model.** Freeze representative **synthetic-only** FHIR R4 validation examples, canonical JSON/provenance fixtures, CLI error behaviors and existing `medscale` package version identity. Inventory filesystem, backup, install/uninstall, update, localhost and subprocess threat surfaces. Record current Python latency, peak RSS and file-size budgets in a reproducible benchmark; benchmark results will determine which hot path, if any, merits Rust.
2. **D1 — offline desktop spike.** In an isolated, nonpublishing workspace, create a minimal Tauri window with an explicit **Synthetic / Developer Preview** indicator. Show a local, non-sensitive fixture and a read-only provenance/status page; no Python import and no EHR/PHI feature. Disable analytics, auto-updates, remote content and network permissions by default.
3. **D2 — one bounded Rust command.** Implement a single strictly typed, local-only operation such as reading a synthetic fixture's SHA-256 with a size limit, canonical path restriction, no symlinks/traversal, source identity in the response, deterministic error codes and deny-by-default permissions. Test adversarial paths, malformed input, large payloads, concurrency and repeatability.
4. **D3 — Python/Rust parity.** For a justified FHIR or provenance operation, run identical synthetic fixtures against Python and Rust; require byte-for-byte equivalence of documented outputs, allowed failures, deterministic ordering and audit fields. A mismatch is a **release blocker**, not an opportunity to silently relax validation. Add both implementations to platform-specific CI only after the consumer contract is approved.
5. **D4 — installer qualification.** Only after D0–D3 pass, build an unpublished Windows installer, then qualify macOS and Linux separately. Test offline startup, uninstall, no telemetry, no network, no hidden cloud API, local storage/backup behavior, accessibility, installer integrity, rollback and licenses; ship no optional unsafe research dependencies.
6. **D5 — independent release decision.** Record source commit, toolchain locks, licenses, build reproducibility, negative-case test receipts, artifact hashes and security review. Existing Python Developer Beta and any future desktop version receive **separate** release/tag/security decisions. No publish/merge is implied by success.

## Acceptance and stop criteria

- Existing Python v0.3.0 candidate stays functionally unchanged; historical `v0.2.0` data/tag, frozen `pyproject.toml`, `uv.lock`, MRL receipts and accepted ADRs are byte-immutable.
- The new desktop artifact must work **fully offline with synthetic data only**; any unapproved network/telemetry, import of real records, patient data flow into research, or file permission escape fails closed.
- Build/test with **free local or repository CI** only. Verify each supported OS independently; do not infer Windows/macOS/Linux from a single runner.
- Rust is **not automatically a performance win**; adopt a Rust port only after reproducible benchmark and behavioral parity evidence, or a documented security/non-Python-consumer requirement.
- Distribution metadata must not advertise vulnerable Python optional extras. Resolve [issue #622](https://github.com/AbdulazizShehri/MedOrigin/issues/622) and version/package architecture [issue #574](https://github.com/AbdulazizShehri/MedOrigin/issues/574) through their own governed paths; require independent security/release signoff [#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603).
- No release/tag, protected-main merge, PHI access, clinical pilot, runtime service or model training is authorized by this plan. A separate ADR decision is required before adding a second language toolchain.

## Decision status

**Proposed direction, not an implemented feature.** Near-term priority remains completing the existing Python Developer Beta security gates without unnecessary rewrites. A later desktop engineering PR must name its consumer, exact toolchain, owner, maintenance/CI costs, and falsifiable acceptance tests before any Rust implementation becomes part of the supported MedOrigin product.
