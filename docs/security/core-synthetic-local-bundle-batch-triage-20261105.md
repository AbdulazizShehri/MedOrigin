# MedOrigin Core: actionable fictional FHIR batch diagnostics

Date: 2026-11-05 Asia/Riyadh. Private developer feature, not a clinical
validator, not production authorization and not a release candidate.

## Actual product gap and added capability

The previous multi-file offline R4 structural command
`medscale fhir batch-bundle-assess` returns no partial JSON if **any**
source fails local relationship preflight. This is correct for an atomic
structural qualification but does not tell a developer which of several
invented local Bundles needs correction.

The new additive **local relationship triage** command provides
source-position-specific, redacted diagnostics for marked fictional
sources, including accepted and known-refused inputs:

    medscale fhir batch-bundle-diagnose --synthetic-only INVENTED_1.json INVENTED_2.json

- 2-8 local invented JSON Bundles only; bounded input size and depth are
  enforced by the established Core UTF-8 reader.
- Before any result, **every** input must contain the exact fixture marker
  and a unique source digest; inputs lacking that marker, duplicated
  sources, missing/ambiguous files and excessive entry counts fail the
  entire operation without a partial JSON receipt.
- Accepted source: ordinal, SHA-256, Patient/Encounter/Observation counts,
  checked local reference count and explicit `preflight_only` status.
  Rejected, but exact marker-backed source: ordinal, `rejected` status,
  two fixed FHIR-style OperationOutcome issues (one specific local error
  and one universal nonconformance warning); no rejected-source hash or
  source identifiers. Caller data and raw exception text are NEVER relayed.
- Returned JSON includes counts of accepted and rejected source files,
  no patient identity union, no file names/paths, no payload, no network,
  no export. Even if all local preflights pass, CLI returns exit code **2**
  rather than implying FHIR or clinical validation. The separate optional
  official HL7 FHIR R4 schema command is unchanged; neither command proves
  profiles, terminology, invariants, cross-file identity, or clinical safety.

Synthetic markers are **caller assertions**, not PHI detectors; don't
feed real patient data, connect EHRs or export findings for clinical use.
The new API refuses malformed or unapproved sources before any output,
and only exact fixed rejection issue texts from the existing Core
`rejected_synthetic_bundle_operation_outcome` are admitted.

## QA and boundary

Source tests: `tests/test_core_batch_local_diagnostics.py` actually write
two invented JSON Bundles and invoke the public Core CLI dispatcher.
Fixtures include mismatched local Patient ref, forbidden external URL,
missing marker, duplicate source, missing second file, malformed CLI
flags, wrong permissions, and poisoned upstream diagnostic fields. No
real PHI, external inference or hosted deployment.

**Observed Windows evidence, exact source branch before Git commit:**
- **243 PASS**, **3 optional HL7 R4-schema tests SKIPPED** across the new
  triage, original multi-Bundle structural check, original single-file
  preflight and OperationOutcome, encrypted Workspace timelines/ingest
  and portable CLI. Ruff lint/format PASS and Git whitespace PASS.
- Public Core CLI source dispatcher used genuine two invented local JSON
  files, one accepted and one with forged external Patient reference,
  under **Python 3.11.15, 3.12.13 and 3.14.7**: all exit 2 with correct
  finite local diagnostics, no private text/paths echoed.
- A real PEP517/Hatchling **medscale 0.3.0 Wheel** was built on Windows:
  SHA-256 `4243f0aad7c1b80c2d94c811c6e97825deb81808282d04bb6b064234dee7c54c`.
  It was installed with no dependency resolution in temporary --target.
  Exact installed-module Core CLI execution (source-tree imports
  explicitly forbidden and package metadata version asserted) passed the
  same fictional scenarios for all THREE Python versions.
  Independent Wheel archive bytes matched all five checked-out source
  files: new batch module, CLI dispatcher, preflight, redacted diagnostic
  generator and bounded JSON input reader.
- This is **installed module** proof, NOT attestation of the generated
  Windows `medscale.exe` PE entrypoint, an approved MSI, clinical
  validation, complete HL7 R4 validation or hosted CI.

The separate full official R4 schema structural check is unchanged.
These tests did not supply a real official R4 archive, correctly leaving
those 3 optional tests skipped; previous PR #959 qualified the genuine
partial R4 batch command separately.

Release remains explicitly NO-GO: #877 full HL7 R4 conformance, #882 full
Developer Beta, #893 genuine Windows CLI launcher attestation, #603
independent security and clinical review, #622 vulnerable dependencies,
#574 independent founder release decision, and production key custody,
consent, role authorization and PHI handling. No merge, tag or publish.
