# MedOrigin synthetic FHIR batch — stable Core/Workspace boundary

**Private source implementation; synthetic-only; NOT a clinical/production
release.** This slice is stacked on private Core Draft #916
(`12b8b34f7852c5d3f04d788fd433b024f1884dbf`).
It builds a stable, independently tested Python boundary between the Core
Bundle preflight and the separately packaged encrypted Workspace.

## What changed

The preceding #916 `medscale.fhirkit.workspace_ingest` implementation
reached into 11+ Workspace FHIR/provenance/audit internals, including
private test-provider state, directly from Core. This introduces
`medscale_workspace.fhir_batch.commit_synthetic_fhir_batch_atomic`
as a constrained, public importable **developer/test-only** facade.
Core now owns only the immutable, finite JSON snapshot, local
`urn:uuid` Bundle preflight, strict 16-resource upper bound and
translation of **two** supported references (subject/encounter) to
Workspace's existing bounded representation.

Workspace now owns the strict **exact** InMemoryTestKeyProvider check,
store instance identity check, bounded per-resource validation,
deterministic resource identities, source provenance, existing audit
spine, and the single real encrypted SQLite
`WorkspaceStore.put_objects_atomic` transaction. All N FHIR resources,
N provenance records and one audit event commit together or roll back
together. No unsupported Workspace resource fields are silently
discarded, and errors are redacted fixed tokens.

### Independent self-contained batch references

The facade **independently verifies every supported Workspace reference
points to a resource of the same type/id inside this incoming batch**,
before committing. A dangling reference is refused even if an unrelated
Patient from an earlier transaction already happens to exist in the
same encrypted store. Duplicate resourceType/id within a direct batch
call is refused rather than allowing ambiguous multiple versions.

This is stricter than general FHIR Bundle reference handling, by
design. No multi-workspace, EHR, external URL, arbitrary patient data,
general FHIR R4 schema/profile/terminology validation, de-identification,
or full FHIR import compatibility claim is made.

### Source digest scope and key limits

Core computes SHA-256 over the admitted immutable **raw synthetic input**
and passes it to Workspace; Workspace verifies digest syntax and records
it as audit metadata. A caller who bypasses Core and directly invokes
the Workspace developer/test API can supply an arbitrary syntactically
valid digest: this is **not** a cryptographic signature, an identity
credential, or a proof that the source has no PHI. The Bundle's
synthetic tag and caller opt-in are assertions, **not** PHI detection.

The stable batch facade is test-only and requires an explicit
`synthetic_only=True` attestation **even for direct callers**, plus
**exactly** `InMemoryTestKeyProvider`, already bound to the open store.
Subclasses and production platform providers fail closed. Neither
Core nor this facade creates/persists a test root secret or enables
the unavailable OS protected-key resolver. Do not process patient data.

## Reproducible developer experience

The existing hardcoded example exercises all three modules:

```powershell
$env:PYTHONPATH = "src;apps/workspace/src"
py -3.14 examples/synthetic_fhir_bundle_preflight/atomic_workspace_demo.py --synthetic-only --ephemeral-demo
```

It commits 3 FHIR resources + 3 provenance records + 1 append-only
audit event with one SQLite transaction, closes/reopens with the same
in-memory test key, verifies the audit chain and deletes the temporary
database. It accepts no arbitrary user input or destination and
never displays input identifiers/names/observation values.

`tests/test_core_public_workspace_batch_contract.py` directly tests
the Workspace facade without relying on Core preflight, including
cross-batch reference prevention, duplicate identity, invalid digest,
resource count limits, unreviewed fields and subclassed test providers.
`tests/test_core_atomic_synthetic_workspace_ingest.py` preserves the
Core interoperability and true rollback/crash-injection acceptance
tests. Existing `test_clinical_workspace_fhir_v1.py` and adversarial
tests verify the earlier FHIR storage behavior was not regressed.

## Explicit release blockers

Not production-key management, authorization, clinical workflow or
full conformant FHIR R4. Not an approval to use PHI, publish/sign a
package, merge protected main, or expose a new UI feature. Exact-head
hosted CI, independently reviewed dependency vulnerabilities,
independent clinical/security signoff, and #574, #603, #622, #877,
#882 and #893 remain separate blocking gates. The draft is source
qualification only until independently reviewed.


## Native installed developer CLI — fixture is embedded (no checkout needed)

An additional Core-only product command exercises the *fully installed*
Core and Workspace packages without relying on the repository's
`examples/` fixture or source checkout:

```sh
medscale fhir workspace-demo --synthetic-only --ephemeral-demo
```

The command requires two exact opt-in flags, uses a **fresh hardcoded
three-record fictional Bundle** shipped with Core, creates one encrypted
temporary Workspace with a freshly generated in-memory test key, saves
3 resource objects + 3 provenance objects + 1 audit event atomically,
closes and reopens to verify the audit chain, and deletes the temporary
directory. It emits a single **redacted** JSON status and counts, with
all clinical/conformance/release authorizations set `false`.
It accepts **no external FHIR file, network address, EHR, key or
persistent output destination**. Unknown tokens and supplied paths
are refused with a fixed error code without echoing their value.

The optional Workspace package must actually be installed; Core does
not add `medscale-workspace` as a mandatory runtime dependency.
The native generated console shim remains a separate unqualified
attestation issue (#893), so **local installed-module invocation
does not certify a generated `medscale.exe` launcher's origin**.

`tests/test_core_portable_workspace_demo_cli.py` covers the real
public Core dispatcher, successful encrypted ephemeral reopen,
both flag requirements, no caller-input echo, negative error outputs
and fresh independent fictional payload instances. The broader
Windows Python3.14 selected functional suite: **100 PASS,
2 DESELECTED**. Two historical raw-wheel tests in
`tests/test_fhir_cli.py` failed at fixture setup because an expected
external build executable was not available in that particular
Windows test environment, **not because their assertions passed**;
they were explicitly excluded in this test selection. Exact-source
Wheel build, source identity and installed-binary smoke are separate
gates, not inferred from the functional test selection.


## Latest independently source-checked installed Core + Workspace pair

**Functional commit `0351b667ec910480fd61c30f18cf3bb0dd0ae842`.**
All checks below are local/private and were performed against that
exact functional source on the authorized Windows PC + WSL Linux ext4.

- Exact-source native ext4 checkout was refreshed to `0351b667`.
  Existing read-only Core source projection was built with
  `uv build --offline --no-create-gitignore`. Independently existing
  Core Wheel/sdist source verification gates returned
  `SOURCE_BOUND_WHEEL_QUALIFIED_ONLY` and
  `SDIST_SCOPE_QUALIFIED_ONLY`, both with **zero issues**.
- Separately built **Workspace Wheel + sdist** from
  `apps/workspace` in the same pinned checkout with offline `uv`.
  Zip entry and **byte-for-byte exact source** comparison passed for
  all **33 Python module files**. The Workspace Wheel metadata matched
  MedOrigin's repository and the intended `cryptography==50.0.1`
  runtime pin. The Core Wheel's `medscale/cli/fhir.py`,
  `medscale/fhirkit/workspace_demo.py` and
  `medscale/fhirkit/workspace_ingest.py` also matched exact source
  module bytes. No generated publisher artifact was uploaded.
- Core Wheel `medscale-0.3.0-py3-none-any.whl` SHA-256:
  `25a11917d79edc1432bb28f2dba06ae3327b28a2ec495f619f45ba105fe2e7f6`.
  Core sdist SHA-256:
  `acaad0dc4e81d966f40705fbd5f981b919ccfe6661533dc67e7d82c590d2e2d8`.
- Workspace Wheel `medscale_workspace-0.1.0.dev1-py3-none-any.whl`
  SHA-256:
  `c37516f2b7b831b3fcfc417a2d7703c29d0917f3c684c19215f7e07399e05b73`.
  Workspace sdist SHA-256:
  `e513f6f943cce76b90596ecd47f5ef89fa517802fce1d35dd4756878623ea47d`.
- Both exact-hash verified Wheels installed in **one task-owned
  Windows --target directory** via
  `pip --no-index --no-deps`, without modifying the system's
  `site-packages`. Windows Python3.14 `-P -B -s` with only that
  target in `PYTHONPATH` verified both Core and Workspace module
  paths resolved **inside the installed Wheel tree**, not source.
- Real installed Core public dispatcher (`medscale.cli.main`) invoked
  `fhir workspace-demo --synthetic-only --ephemeral-demo`:
  **exit0, `SYNTHETIC_ENCRYPTED_ATOMIC_DEMO_PASS`, three encrypted
  resources, successful reopen and integrity check, temporary store
  removed, no clinical use authorized**. An unknown supplied
  fictional file path returned **exit2 with fixed refusal token and
  no echo of the path**.
- Python3.14 selected Core CLI/Workspace FHIR tests:
  **100 PASS, 2 DESELECTED** (raw-Wheel tests invoke unavailable
  external executable). Python3.11.15/3.12.13 combined portable
  CLI + direct Workspace batch + atomic Core integration suites:
  **40 PASS each**, with separate pinned task-only binary
  `cryptography==50.0.1` and `cffi==2.1.1` and controlled reused
  pytest; **not hermetic hosted CI**.

The actual Windows `medscale.exe` console shim was not independently
attested; this run used the exact installed Python public dispatcher,
not a signed/bundled native launcher. Protected OS key custody,
production authorization, full FHIR R4 validation, real PHI, hosted
CI, independent security/clinical review, publication, and merging
remain out of scope. Result remains a **private synthetic-only NO-GO
release candidate**, not a production-ready clinical application.
