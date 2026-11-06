# MedOrigin Core: reject cross-patient Observation/Encounter links

Date: 2026-11-05 Asia/Riyadh. Private source-backed engineering, not
complete HL7 FHIR R4 conformance, release authorization or real PHI support.

## User-impacting issue and fix

The existing narrow offline synthetic FHIR Bundle check admitted a local
`Observation.subject` reference when it resolved to any Patient and a
local `Observation.encounter` when it resolved to any Encounter, but did
not require the referenced Encounter to belong to the same Patient as
the Observation. For a Bundle containing more than one Patient, that
could accept clinically misleading cross-patient event ownership even
though all UUID references existed and had the correct resource types.

`src/medscale/fhirkit/bundle.py` now builds an Encounter-fullUrl to
Encounter-subject-Patient-UUID map after collecting all admitted
resources, independently of input entry order. On a declared local
`Observation.encounter`, Core verifies that the Observation's own
`subject.reference` equals the referenced Encounter's
`subject.reference`; otherwise it raises the fixed redacted
`observation_encounter_patient_mismatch` error. The previous
no-Encounter Observation subset is still supported. Good
forward-reference Bundles with multiple distinct Patients and their
independent Encounters remain accepted, with exactly the same count
and source report shape as before. No new patient identity or reference
value is included in outward-facing results.

`src/medscale/fhirkit/bundle_diagnostics.py` now maps the fixed error
to an allowed, source-safe, per-file FHIR OperationOutcome. The existing
read-only Core public `bundle-preflight` refuses mismatches entirely,
while `batch-bundle-diagnose` can show which source ordinal was
rejected without disclosing rejected source SHA, resource payload, or
Patient identity. Existing `bundle-assess` and official offline
JSON Schema gated `batch-bundle-assess` / `file-batch-encrypted-demo`
now reject cross-Patient links *before* optional schema validation
or Workspace encryption, because they all call this shared Core
relationship preflight. No independent PHI detection or real patient
permission is inferred from the synthetic marker.

## Verification and limitations

`tests/test_core_multi_patient_reference_consistency.py` uses six
invented resources across two independently linked fictional Patients.
It tests correct and mismatched Observations with reversed/forward
entry ordering, changes to an Encounter's Patient binding, an
Observation lacking optional Encounter reference, fixed redacted
OperationOutcome, actual saved fictional FHIR JSON passed through
public Core `bundle-preflight` and `batch-bundle-diagnose`,
and refusal of dual-schema or atomic encrypted Workspace commit before
untrusted downstream processing when the local Patient link is wrong.

This is one **mandatory local semantic relationship invariant**, not
full FHIR R4 semantic validation. It does not verify references outside
the narrow admitted synthetic Patient/Encounter/Observation fields,
profiles, terminology, Encounter ownership over time, consent,
FHIRPath, external EHR links, OS-backed key storage, production
authorization, or patient safety. The existing release gates for
#877 full FHIR R4, #882 full Beta, #893 independently attested console,
#603 security/clinical review, #622 advisories and #574 owner
publication permission remain **NO-GO**. Never merge or publish
without those independent gates.

## Verified Windows product evidence

- New tests + existing source relationship/triage suite: **64 PASS**.
- Expanded existing official-R4 structural gate, caller-selected
  encrypted file import, source-scoped timeline, synthetic Workspace
  atomic import, and Core FHIR regression: **317 PASS / 4 optional
  official HL7 R4 ZIP tests SKIPPED**. Two pre-existing tests had
  depended on the old late refusal path; updated to assert **early Core
  refusal and zero encrypted objects written** while retaining the
  independent timeline invariant check as defense in depth. No failed
  regression remains in this defined source suite. Ruff lint and
  format PASS; Git whitespace check PASS.
- Built both genuine PEP517/Hatchling Wheels on Windows from this exact
  isolated Core worktree: Core `medscale-0.3.0-py3-none-any.whl`,
  observed SHA-256
  `da0fef298993ad9e170eb18c52a6b32a5eb8cf7c5f731a4e35e2ed1a12ec60b5`;
  Workspace `medscale_workspace-0.1.0.dev1-py3-none-any.whl`,
  observed SHA-256
  `7613774b1f64daf1473d2f7c1ef7601c43e01bba70b62e4b1edc212bc86c95a5`.
- Installed both Wheels into a task-owned, isolated Windows prefix.
  Real public Core CLI on 2 caller-authored invented local JSON files,
  containing 6 resources and 2 independent fictional Patients, passed
  the good local-reference source and rejected the wrong-patient source
  with fixed redacted stderr and **zero JSON**. Real two-file diagnostic
  showed one accepted and one rejected source, with no rejected SHA
  or patient identifiers. The generated Windows `medscale.exe` console
  from this installation was directly exercised with the same two
  files, yielding identical success/refusal and redaction behavior.
  Both installed packages were explicitly loaded from installed Wheel
  paths, not from the development source checkout. This is **functional
  smoke only**, not independent PE vendor/installer authentication
  or tamper-negative qualification (#893 remains NO-GO).
- The installed Core Wheel's patient/Encounter matching check also
  passed on Windows Python **3.11.15, 3.12.13 and 3.14.7**. Direct
  console PE was tested only with its generated Python 3.14 launcher;
  no separate 3.11/3.12 executable attestation or full cross-platform
  product release is claimed.
- No official HL7 structural schema was required for this narrower
  mandatory local cross-patient invariant. The previous product's
  optional, exact official R4 Schema structural checks are still
  independent, partial and nonclinical, with no new full-conformance
  assertions. No actual patient data or external FHIR server was used.
