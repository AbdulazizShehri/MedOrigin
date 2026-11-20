# Native fictional Core relationship inspector and visitable breadcrumbs

**2026-11-04 · private stacked Draft above #942 · only reviewed imaginary FHIR-like Core resources, NO real patients.**

## Functional native Desktop changes

Inside the actual D2 decrypted fictional Core resource details, the native Rust UI now shows **Verified fictional references: N outgoing, M incoming**, derived directly and exclusively from the existing source-verified recovered resource graph. Outgoing edges are the selected record's reviewed link array; incoming edges are counted by matching the same source-projected `full_url` in the other recovered records. This is an inspection aid, not terminology, clinical inference, risk scoring or treatment advice.

A **Recovered fictional navigation trail: N previous verified steps** displays each earlier source-derived resource as its own clickable button, e.g. `Jump recovered history step 1: Observation/fictional-observation-001`. Users can jump directly to the earlier valid reviewed resource rather than repeatedly pressing Back. Jumping **truncates** the intervening history, resets the type facet and query to All, and never synthesizes a new graph edge. Out-of-range/malformed/stale history or nonexistent data **fails closed**, clears selected record, history and imaginary readback; normal Back remains unchanged. Existing type/search filters reset navigation history to prevent stale links. No data is saved, exported, copied, downloaded, synced, inferred or passed to models.

## Actual Windows 11 evidence

- Rust offline+locked: **55 native lib tests + 11 main tests + 7 browser/process/network static guard tests = 73 PASS**. New adversarial unit checks a real fictional Observation -> Encounter -> Patient navigation chain, direct jump to Encounter and Observation, retained/truncated history, refusal of invented breadcrumb, refusal of intentionally corrupted history, and search/type-filter history clearing.
- Offline+locked Clippy `--all-targets -- -D warnings`, Rustfmt `--all --check` PASS; no dependency added.
- Rebuilt native Windows D2 debug GUI SHA-256 `29c234abfe621a2cb62d21f7b5cef0390f82af49b8f9d3f896e58a6f091a535c`. Actual Windows UIAutomation `tests/windows-encrypted-core-readback-uia.ps1` verified Patient has **0 outgoing / 2 incoming** reviewed fictional links and two history steps, clicked direct Observation breadcrumb, verified Observation **2 outgoing / 0 incoming** and stale Encounter breadcrumb is absent, then re-followed exact source-projected Encounter and Patient relationships, incoming Observation and multi-step Back/Clear. Exit 0 `WINDOWS_REAL_ENCRYPTED_CORE_READBACK_THREE_RESOURCES_LINK_AND_BACK_UIA_PASS_NOT_CLINICAL`.
- Actual Python 3.14 encrypted AES-GCM Core/Workspace source-run and reopened real fictional Bundle under Windows suspended-before-execution kill-on-close Job Object to native D2 test separately verified. Only exact canonical 1,164-byte redacted fictional projection accepted.
- GitHub-hosted exact PR-head Ubuntu/Windows nonpublishing CI **must be observed** before declaring remote green.

## Restrictions / honest NO-GO

The three resource identities are **fictional and redacted**, not real patient records. This GUI does not implement patient search, writable clinical workspace, production key management/RBAC, consent, clinical reporting, medications, EHR connectivity, full FHIR R4 terminology/semantics or medical review. Per-launch HMAC from #941 is developer-owner-bound, not independently authenticated sender identity; Windows job lifetime control is NOT OS network egress confinement. Python/cryptography native dependencies, signed distribution, security/dependency remediation, clinical validation and independent accessibility/security reviews remain unresolved. Do not merge protected main, publish/sign, process PHI or claim clinical readiness.
