# MedOrigin Core: exact official HL7 FHIR R4 structure before encrypted import

Date: 2026-11-05 Asia/Riyadh. Private Core engineering, not a clinical
validator, not a release, not real-patient authorization.

## Product-level missing link addressed

The previous Core `batch-bundle-assess` was a real *read-only* official
FHIR R4 JSON Schema structural check. Separately, `file-batch-encrypted-demo`
accepted actual caller-selected invented FHIR files into an AES-GCM
ephemeral Workspace after only narrow Patient/Encounter/Observation local
reference checks. The official R4 structural check did not guard that
encrypted import operation.

This additive, opt-in command now performs **both checks before any
Workspace allocation**:

    medscale fhir file-batch-encrypted-demo --synthetic-only --ephemeral-demo --offline-r4-schema FHIR_R4_OFFICIAL_4_0_1.zip invented1.json invented2.json

It can be combined with the already available inclusive UTC day and
Encounter/Observation source-scoped filters. Without the schema option,
the existing command and JSON receipt are unchanged.

All 2–4 caller-selected invented FHIR files are read by the existing
size-/depth-/UTF-8-bounded JSON source reader, snapshotted and fully
synthetic-marker/local-reference preflighted before encryption. The
optional new gate runs `assess_synthetic_bundle_batch_offline` on **ALL**
source snapshots using the exact HL7 FHIR R4 v4.0.1 JSON Schema ZIP.
The ZIP must be supplied locally, not downloaded automatically; its
SHA-256 is exactly
`75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6`.
The validator's exact `jsonschema==4.25.1` dependency must be available
locally; no fallback to unpinned or unsigned schema is allowed.

An explicit structural `invalid` in any source, a missing/wrong ZIP,
wrong validator version, missing marker, duplicate source SHA, injected
false positive, mismatched source ordinal/SHA/resource count or extra
downstream patient content causes a **fixed, redacted refusal before
temporary Workspace allocation**, with **no partial JSON result**. A
source-verified positive from *each* source may report only the original
status `not_validated`, because official JSON Schema checks remain
**partial FHIR R4 structural checks**. The newly surfaced read-only
`official_r4_structural_gate` receipt contains only pinned archive SHA,
number of source documents with structural checks and negative
clinical/conformance/release flags. It is never labeled `valid`.
The following real fictional Workspace encryption, audit, physical
close/reopen, independent per-source catalog/timeline verification and
ephemeral cleanup run only after the qualified source checks pass.

The user-facing Core command returns exit **2 even on structural pass**
to avoid implying complete FHIR conformance or a clinically authorized
import. The input marker is an assertion by the caller, never a reliable
PHI detector. No real patient data, EHR/endpoint, cloud inference, remote
FHIR terminology server, retained permanent patient Workspace,
production key custody, RBAC or Patient identity federation is allowed.

## Testing and exclusions

`tests/test_core_file_official_r4_before_encrypted_import.py` has
source-bound contract tests and a separately opt-in **genuine official
HL7 v4.0.1 ZIP** test. Contract doubles exercise only the outer
source identity, issue-allowlist and pre-allocation refusal contract;
they **must never be described as a real official-schema validation**.
The opt-in real test must provide
`MEDORIGIN_R4_OFFICIAL_SCHEMA_ZIP` and `jsonschema==4.25.1`,
verifying a real fictional two-file structural pass and a second
structurally invalid `Observation.valueString` (numeric instead of
string) which must prevent Workspace allocation entirely. The ZIP
and temporary pip dependencies are QA-only and never committed.

Remaining release blockers: no full R4 terminology/profiles/FHIRPath/
invariants and reference conformance (#877), full Beta (#882),
source-independent attested installed console/installer (#893),
independent clinical and security review (#603), vulnerable dependency
backlog (#622), final owner release permission (#574), real host-backed
production key custody, role authorization, consent and PHI governance.
The app remains PRIVATE Draft and **RELEASE NO-GO**. No merge into
protected main, tag, distribution or clinical assertion is authorized.

## Observed owner Windows QA and source/packaging integrity

- Genuine downloaded **official HL7 R4 v4.0.1 ZIP** 287789 bytes,
  verified SHA-256
  `75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6`,
  exactly matches the existing pinned Core source SHA; not committed.
- Strict `jsonschema==4.25.1` used from a temporary isolated QA
  installation. Genuine source tests: **99 PASS / 2 optional official
  schema tests SKIP** (two separately opted-in historical tests did not
  share this test's environment variable). Extended Core FHIR,
  encrypted Workspace and actual source-file import regression:
  **273 PASS / 2 optional SKIP**. No failed test; Ruff lint and format
  and Git whitespace checks PASS.
- PEP517/Hatchling generated real Core Wheel
  `medscale-0.3.0-py3-none-any.whl` SHA-256
  `84f6bd2c4c1dc68c626a8345136753112f366ed8a9c7ad16b722d98551128c80`
  and real Workspace Wheel
  `medscale_workspace-0.1.0.dev1-py3-none-any.whl` SHA-256
  `7613774b1f64daf1473d2f7c1ef7601c43e01bba70b62e4b1edc212bc86c95a5`.
  Independently inspected **eight exact Python Wheel members**; each
  was byte-identical to the corresponding checked-out source file.
- Both Wheels installed together into an isolated Windows
  `--prefix`, with no project source path in imports; actual Core and
  Workspace import file locations verified under that prefix.
  On Windows Python **3.14.7, 3.11.15, 3.12.13**, actual interpreter
  execution from **both installed Wheels** passed real two-source
  official-R4 structural qualification + real encrypted Workspace
  commit and cold reopen + verified audit and source-filtered
  readback + temporary store cleanup. A genuine, syntactically
  well-formed but structurally invalid second fictional JSON input
  (`Observation.valueString` numeric) caused **no successful/partial
  JSON output**. The official archive was the exact pinned file in
  every run; `not_validated` and exit 2 are deliberate.
- Actual task-generated Windows `Scripts/medscale.exe` in the Python
  **3.14** installed prefix was directly invoked on genuine positive
  and structural-negative invented inputs; both exhibited the
  intended behavior. This is only functional console smoke, **not
  independent PE authenticity or signed-distribution qualification**
  (#893 stays OPEN). The 3.11/3.12 validations used interpreter-level
  invocations of the two installed Wheels, **not** 3.11/3.12 console PE
  executables.
- One dependency-resolution finding is important for productization:
  on task-owned bare CPython3.11/3.12, unpinned transient
  `referencing` dependencies could fail during `jsonschema` import
  because `typing_extensions` was absent. With an explicitly
  isolated `referencing==0.36.2`, `typing_extensions==4.15.0`,
  `jsonschema==4.25.1`, `cryptography==50.0.1` and runtime-compatible
  subordinate wheels, both versions **passed**. These were confined
  to removable task scratch; no globally installed packages, project
  dependency locks or frozen release metadata were modified.
  An independently reviewed offline dependency lock for full
  3.11–3.14 installed distribution remains a future release task.

The official HL7 JSON Schema is a partial conformance method only.
Neither source tests nor an installer execution prove terminology
bindings, full profiles, FHIRPath invariants, authorization, OS-backed
key custody, PHI isolation or clinical readiness; no real patient
data, protected-main merge or publication is authorized here.
