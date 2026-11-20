# Private security and clinical release NO-GO — 2026-11-04

**MedOrigin is not authorized to accept patients, store patient data, connect to EHRs, or publish a clinical desktop release.** This gate is a read-only QA tool, not an approval mechanism or a substitute for human security or medical review.

## Source-backed live GitHub findings

Read-only `gh api --paginate --slurp` returned **66 open Dependabot alerts** from private `AbdulazizShehri/MedOrigin`: **6 critical, 29 high, 27 medium, 4 low**. All 66 alerts list `uv.lock` as the manifest and `pip` as the ecosystem. Package-name totals are Pillow 41, filelock 9, aiohttp 8, urllib3 3, certifi 1, accelerate 1, diskcache 1, multidict 1, setuptools 1. Five critical Pillow alerts give a first-patched version 13.0.0; one critical certifi alert gives a first-patched version 2026.10.18 **according to GitHub alert metadata at observation time**. These are *advisory leads*, not a validated upgrade plan: an upgrade must independently verify compatibility, source provenance, optional groups, availability and platform-specific impacts.

Core's `pyproject.toml` at the sampled source declares **no mandatory runtime dependencies**, but does include Pillow 12.3.0 and Accelerate 1.14.0 in **optional research extras**. GitHub alert `dependency.scope=runtime` does not establish that every package is actually shipped by the D2 native preview; equally, optional classification does not dismiss repository-wide security debt. **No native D2 dependency reachability conclusion can be derived from the Dependabot response alone.** D2 separately has AccessKit/transitive Linux `zbus 5` maintenance concern #673; these six issues are not a complete inventory of security risks.

The following live issues are open and must retain independent NO-GO status:
- **#574** owner release-governance, identity, signing/publication approval.
- **#603** independent security assessment and risk qualification.
- **#622** optional research dependency advisories.
- **#662** D1/Tauri WebView2 real external TCP/egress blocker; D2 negative network canary does **not** close D1.
- **#673** D2 AccessKit Linux unmaintained transitive dependencies.
- **#676** real macOS spoken VoiceOver and independent accessibility acceptance.

## New read-only, fail-closed guard

`scripts/qualify_private_release_gate.py` uses authorized `gh` and the exact repository owner/name to fetch all open alerts via **cursor-following GitHub Link pagination** (`gh api --paginate --slurp`; using `page=` would incorrectly give HTTP 400), and checks all six issue IDs. It rejects unexpected issue IDs, ambiguous alert severity, duplicate alert numbers, missing source evidence or API failure. It reports exact alert count, severity distribution, affected manifests and package names, explicitly `dependency_reachability_to_native_d2=NOT_DETERMINED_FROM_ALERT_API`, and independent governance/clinical/security/OS-traffic gates false. Even a hypothetical empty alert list and all issues closed **cannot** cause the script to self-award approval. The tool exits **2 by design** and says `MEDORIGIN_PRIVATE_RELEASE_GUARD_ENFORCED_NO_GO` when all evidence is available. If evidence fails, it exits 2 with `MEDORIGIN_RELEASE_GUARD_NO_GO_EVIDENCE_UNAVAILABLE`.

The script does not close, dismiss or mutate GitHub alerts/issues, update dependencies, modify source or publish packages. It is **not embedded in the D2 runtime**, so its status is an engineering proof and policy reminder rather than a guaranteed release-pipeline enforcement. Actual signed release/publishing pipelines must separately implement independent policy controls.

```sh
cd experiments/desktop-d2-native-egui
python3 -m unittest discover -s scripts -p test_private_release_gate.py -v
python3 scripts/qualify_private_release_gate.py
# Expected exit 2; not a test failure, but a deliberately enforced NO-GO.
```

## Evidence and remaining unresolved acceptance

- **8/8** Python negative guard tests passed on real Apple Silicon Mac, including duplicate alert refusals, missing records, forged issue states and API failure.
- Live authenticated GitHub scan returned 66 open alerts and all six expected open issues, exit **2**, status NO-GO.
- The other private stacked D2 Draft PRs provide: #904 standalone real synthetic Core→D2 macOS sandbox QA, #905 standalone age-encrypted synthetic local workspace QA, #906 real offline HL7 R4 **structural** JSON Schema QA with a documented incomplete StructureDefinition blind spot; none is an installed patient-ready Core/GUI/clinical workspace.
- Needed for any actual release: independent clinical FHIR R4 validation (full structure, terminology, profiles, invariants, references and safety), verified installed Core and OS-level process/packet isolation on **all three supported OSes**, production encryption/auth/key escrow/rotation/backup/recovery and patient consent, dependency maintenance and SBOM/reachability review, real accessibility assessments, security review, and the owner's explicit signing/publication release approval.

No clinical/EHR/PHI workflow, public tag/release, installer, signing or protected-main merge is authorized by this project stage.
