# MedOrigin Core: one-command synthetic FHIR Bundle assessment

**Private prototype/engineering scope, 2026-11-04. No PHI,
clinical conformance, real EHR, signing, or publication authorization.**

## Product improvement

Previously Core exposed two separate local read-only checks:

1. `fhir bundle-preflight` accepts a very narrow explicitly
   tagged `Bundle.type=collection` containing synthetic
   Patient, Encounter and Observation resources, inspects
   their allowed field keys, unique resource IDs/fullUrls and
   selected local `urn:uuid` subject/encounter links,
   without a full R4 schema.
2. `fhir structural-outcome` separately checks an explicit
   fictional FHIR JSON document against the SHA-pinned
   permanent official HL7 FHIR R4 v4.0.1 JSON Schema with
   version-qualified local `jsonschema==4.25.1` and emits
   only a bounded redacted `OperationOutcome`. This still
   does not validate terminology, profiles, invariants,
   references or clinical safety.

**New user-visible Core command combining both:**

```text
medscale fhir bundle-assess --synthetic-only \
  --offline-r4-schema OFFICIAL_R4_ZIP FICTIONAL_LOCAL_BUNDLE_JSON
```

Source component
`medscale.fhirkit.bundle_assessment.assess_synthetic_bundle_offline`
executes the existing *actual* strict local reference relationship
preflight first, then independently checks the **same** admitted
document against the official offline R4 structural schema. It
verifies that both checks produced the identical deterministic
input SHA-256, rejects any contradictory status or unexpected
schema provenance, and returns one finite, stable JSON receipt.

The output contains only: schema/version/status; source SHA-256;
resource counts (Patient/Encounter/Observation); number of
verified local links; separate `relationship_status`;
separate `r4_structural_status`, which is ONLY
`not_validated` or `invalid`; a bounded `OperationOutcome`
with fixed keyword-only structural issues and mandatory
incomplete-coverage warning; verified official ZIP SHA; and
literal negative authority flags. It does **not** output
patient names, resource IDs, reference URLs, original FHIR
documents, host paths, raw JSON Schema errors, clinical guidance,
or a machine-readable FHIR validity success.

**The CLI always exits 2 after returning any dual-assessment
receipt**, including a structurally passing Bundle: a JSON
Schema pass is *not* full FHIR R4 conformance. Malformed/unreadable
input exits 1 with fixed redacted source refusal; missing or
unqualified schema/version exits 2 with fixed refusal, never
fabricating an Outcome. Invalid local relationships exit 2
without running the optional schema. The CLI admits only the
exact four documented arguments and a separately explicit
`--synthetic-only`; unknown positional arguments, extra
flags or unapproved schema/archive locations cannot be echoed.

The synthetic Bundle marker is **only a caller assertion**, NOT
a PHI filter; never provide real patient data. The Core
subset does NOT cover other FHIR resource types, arbitrary
reference properties, or external EHR links. Both checks
are strictly local-only, source-approved and read-only: no
output directory, DB changes, persisted reports, network
requests, external validator command or optional dependency
install is performed by this command. The official ZIP is
provided by the caller and matched against hardcoded SHA256
`75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6`;
all schema metadata and installed jsonschema version are still
checked by the previously source-qualified validator.

Legacy commands, stored report formats and the full Developer
Beta rehearsal are **unchanged**, especially the truthful
`not_validated`/exit2 behavior from #939. This CLI is not a
workaround for the existing RED full Beta/Browser CI. Native
Desktop/D2 source owned by another agent is untouched.

## Source test evidence

`tests/test_core_bundle_dual_assessment.py` covers the
source-bound receipt, deterministic SHA/source count, separate
invalid vs. not_validated R4 result, real public Core CLI
dispatch, redaction, strict input flags, duplicate JSON keys,
absent/unqualified official ZIP, missing source, broken or
nonlocal references, unknown FHIR types, unreviewed fields,
and no report/files persisted. A synthetic unit-only schema
fixture is intentionally patched within test scope; it is NOT
represented as an actual official HL7 schema.

For the separate **real permanent HL7 R4 v4.0.1 ZIP** test:
downloaded a task-only local copy and independently verified
the exact source-pinned SHA256 above. Version-qualified
`jsonschema==4.25.1` was installed to a separate
task-only QA directory (not the user's system interpreter).
**22 focused tests PASSED** with the official ZIP enabled.

Real official schema testing also demonstrates a meaningful
distinction: a Bundle with an invented Patient
`active="true"` string instead of a JSON boolean has
otherwise acceptable local `urn:uuid` relationships
under the limited preflight, but the **actual official R4
JSON Schema** marks it `invalid`; a matching fictional
bundle with `active=true` yields `not_validated`,
NOT `valid`. In both cases the output is redacted
and all FHIR conformance/clinical/release flags are FALSE.

Broader source regression, source-qualified offline Core
Wheel/sdist checks, independently installed-Wheel native
Windows public CLI and hosted exact-head CI results are
separate gates and should be recorded only after actual runs.

**NO-GO** until complete profile/terminology/FHIRPath/invariant
and clinical validation, real RBAC/OS-managed key custody,
third-party security review (#603), full Developer Beta/GUI
negative-truth reconciliation (#882), dependency advisory
closure (#622), native executable launcher integrity (#893),
actual hosted CI, and founder release permission (#574).


## Final source, offline package and native installed Windows evidence

**Functional commit:** `a6ddce33ac21d8484839fd1a56d91fd3f6d9ccc6`.
Broad source Core/Workspace/crypto/audit/FHIR suite, with the
**real SHA-pinned official** HL7 R4 archive configured and isolated
`jsonschema==4.25.1`: **379 PASS, 3 DESELECTED**, zero
test failures. Ruff check+format and Git whitespace PASS. Focused
new command suite: **22 PASS** with the exact permanent official
FHIR R4 v4.0.1 archive. Verified archive SHA256
`75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6`.
One real source fixture proves the official schema detects a
mis-typed Patient `active` in an otherwise correctly linked
Bundle; a structurally passing fictional Bundle returns
`not_validated` and the wrong type `invalid`, never
`valid` or full R4 conformance.

A task-only Windows **exact HEAD Git** checkout supplied
`scripts/stage_medorigin_core_projection.py`. It generated a
source-attested Core projection of **266 files**, with
`source_git_commit=a6ddce33...` and
`publication_authorized=false`. The projection was copied
to a disposable **Ubuntu WSL2 ext4** build directory for
`uv build --offline --no-create-gitignore`. An initial
unqualified build was rejected by the existing strict
source-bound Wheel gate due to incorrect POSIX permission bits
inherited from Windows NTFS. This rejection was **not ignored**:
the files in the **task-only WSL projection** were normalized
to 0644, directories 0755, then rebuilt offline without
changing any committed source, root pyproject, lock file,
system Python or protected main.

The corrected, local, **unpublished** artifacts are:

- Core Wheel `medscale-0.3.0-py3-none-any.whl` SHA256:
  `0c7930553d7e9dd70ac53a45deade66d5b4166731210855c78aa06cdf78336c1`
- Core sdist `medscale-0.3.0.tar.gz` SHA256:
  `973b986f652872680ac41eb5203b995bed0a3d061446687bb6c9f49eed392df3`

The repository's independent, **Windows Git-backed** exact
source-bound Core Wheel identity,
`SOURCE_BOUND_WHEEL_QUALIFIED_ONLY`, sdist publication-scope,
`SDIST_SCOPE_QUALIFIED_ONLY`, and wheel metadata,
`METADATA_QUALIFIED_ONLY`, returned **ZERO issues each**.
Five Core FHIR modules including the new
`bundle_assessment.py` and CLI `fhir.py` matched the
built Wheel members **byte-for-byte**.

The exact SHA-checked Wheel was installed locally with
`pip --no-index --no-deps --target` into a **task-only
Windows package directory**; no global/site Python
installation, registry, release or signed launcher changed.
An independent test script forced six imported Core modules
to resolve strictly **inside that installed Wheel target**,
not from Git/source checkout. The *real installed public
Python Core dispatcher* `fhir bundle-assess` executed with
the **same official pinned HL7 R4 ZIP** and separate qualified
`jsonschema==4.25.1` dependencies on:

- Native Windows **Python 3.14**.
- Native Windows **Python 3.11.15**, with a separately
  installed task-only pinned jsonschema dependency tree.
- Native Windows **Python 3.12.13**, with its own separate
  task-only pinned jsonschema dependency tree.

On **all three** runtimes, two actually executed fictional
sources passed independently: correctly typed, locally linked
Bundle -> `r4_structural_status=not_validated`,
`issue.severity=warning` and **exit2**; same local
links but `Patient.active` wrong type ->
`r4_structural_status=invalid`, error+warning and
**exit2**. Printed receipts contained no patient name,
resource identity, fullUrl, input path or schema path.
No local report was written. All full FHIR conformance,
clinical, and publication flags were explicitly FALSE.
Source-independent installed package import provenance was
checked for each runtime. This does NOT independently qualify
the native Windows `medscale.exe` shim (#893).

**These are author-side exact-source technical tests, not hosted
CI, full R4 validator qualification, clinical review or
release approval.** The pre-existing release gates, including
historically RED full Beta/Browser QA (#882), production
key custody/RBAC, dependency advisories (#622), independent
security (#603), clinical review, FHIRPath/profiles/terminology
(#877), Windows shim (#893) and founder authority (#574),
remain **NO-GO**. No publication or main merge.
