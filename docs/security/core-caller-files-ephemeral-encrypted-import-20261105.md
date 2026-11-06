# MedOrigin Core: caller-supplied fictional FHIR files -> encrypted ephemeral Workspace

Private Core engineering. 2026-11-05 Asia/Riyadh. This is **not**
production FHIR ingestion, real patient storage, clinical permission,
complete HL7 FHIR R4 validation, release authority or a production-ready
encryption/key custody mechanism.

## Product work added

Previous multi-import Core demonstrations only used hardcoded fictional
FHIR data, while developer-owned file diagnostic/structural commands did not
actually ingest into encrypted Workspace. This additive command connects
the real developer-selected source files to the real encrypted Workspace
ingestion and cold-reopen source verification:

    medscale fhir file-batch-encrypted-demo --synthetic-only --ephemeral-demo invented-one.json invented-two.json

Only 2-4 files; the caller supplies the paths but **paths and payloads
are never returned**. Each must be a bounded, valid UTF-8 JSON object,
include the exact invented-fixture marker, pass the narrow local-reference
Patient/Encounter/Observation preflight, contain <=16 resources and exactly
one Patient, and have a unique source content SHA-256. **All source files
are frozen and qualified before any ephemeral Workspace is allocated**.
Files containing invalid JSON, missing marker, unsupported FHIR fields,
external references, duplicate source, invalid local links, extra patients,
or malformed CLI options cause a fixed redacted error with zero partial
JSON output.

On real qualified invented files, Core creates an OS temporary directory,
a random in-memory-only test root secret, and an actual encrypted Workspace
store; writes each import via the established independently enforced
public synthetic FHIR atomic batch facade; binds source SHA and audit
digest to each import. The process physically closes the store, **reopens
it using the original in-memory demo key**, verifies the full audit chain
against the last expected head, enumerates independent verified encrypted
import manifests and original source audit anchors, and independently
reconstructs source-scoped fictional patient activity timelines. Never
merge Patient identities across imports.

Return is strictly source allowlisted (ordinal, SHA-256, original import
audit anchor, resource count and per-import verified event count), plus
aggregate counts, audit head, explicit close/reopen/cleanup markers and
all negative clinical/release flags. No paths, names, Patient IDs, raw
resources, keys, FHIR value fields, persistent exports or network. The
store is deleted on success and failure. This is an ephemeral TEST-ONLY
tool, not a way to save actual patient records or supply encryption keys.
A marker merely asserts fictional source and does not detect PHI. Never
pass real PHI even if it bears a marker.

The CLI returns **exit 2** for a successful synthetic-only demo, because
no full clinical validation or release approval has occurred. It reports
a clear success status **inside** the JSON receipt; this is intentionally
different from an installed user-facing clinical validator success exit.
No qualified official R4 JSON Schema, profiles, terminology, FHIRPath
invariants or clinical safety checks are performed in this command.

## Verification and limits

Repo test: tests/test_core_fictional_files_encrypted_batch.py uses
actually saved invented FHIR JSON files and calls the real public Core CLI.
Exercises: 2 separate actual encrypted imports -> true close/reopen ->
audit 2 events -> catalog and independent activity timeline readback;
patient-only second import; second malformed or unmarked source is refused
**before temporary Workspace creation**; duplicate SHA; wrong flags or
missing source; malicious downstream source data cannot be returned.

No production key provider, external EHR, cloud inference, real PHI,
hosted deployment, manual merging or main branch release is involved.
This Core engineering is private and NO-GO for real data until independent
risk sign-off, full FHIR conformance and identity/authorization controls.

Release blockers stay open: #877 full HL7 FHIR R4, #882 full beta
reconciliation, #893 generated Windows launcher qualification, #603
independent clinical/security review, #622 dependency vulnerabilities,
#574 founder publication permission, and real RBAC, OS-backed key custody,
airgap/egress validation and consent/PHI governance. Do not confuse
this test-only ephemeral tool with production-encrypted patient storage.

## Actual Windows source and installed-package QA

- Author/source Windows Python 3.14: new real encrypted caller-file
  import+cold-reopen suite **21 PASS**. Expanded existing FHIR,
  encrypted Workspace, previous multi-import, preflight, diagnostics,
  portable CLI and new importer regressions **264 PASS / 3 SKIPPED**.
  The three skips require separately supplied official R4 ZIP; this
  workflow makes NO official full R4 claim.
- PEP517/Hatchling generated both actual wheels from this checkout:
  Core `medscale-0.3.0-py3-none-any.whl`, SHA-256
  `7092d7a14f75a0f890dfc797e9426bdbf2f5f2c2c9a29d436d321e15b9cc2a1d`;
  Workspace `medscale_workspace-0.1.0.dev1-py3-none-any.whl`,
  SHA-256
  `7613774b1f64daf1473d2f7c1ef7601c43e01bba70b62e4b1edc212bc86c95a5`.
- Both wheels installed together into task-owned isolated target, without
  installer access to source tree. The real public Core CLI dispatcher
  (from installed Core wheel) and encryption/audit/SQLite/Workspace
  readback (from installed Workspace wheel) were executed with TWO
  actual invented on-disk FHIR JSON files. Explicit runtime assertions
  confirmed that Core and Workspace imports came exclusively from the
  installed directory. **PASS on Windows Python 3.14.7, 3.11.15 and
  3.12.13**: two encrypted imports, actual Workspace physically closed/
  reopened, two verified audit events and independent source reads, exact
  cleanup, no raw patient/path output, negative clinical flags.
- Python 3.11/3.12 initially lacked runtime `cryptography`; that
  environment failure was corrected ONLY within task-owned isolated
  directories using `cryptography==50.0.1` plus compatible CPython-
  specific `cffi==2.0.0` and `pycparser==2.23` bundles, without
  altering global Python packages or the user project.
- Exact generated Windows `medscale.exe` launcher/console shim,
  cross-OS installers, production OS-backed keys, audit signing, fully
  published binary attestation and hosted PR CI were NOT independently
  qualified. This is developer functionality verified with TWO
  installed Python wheels, not clinical or release qualification.
