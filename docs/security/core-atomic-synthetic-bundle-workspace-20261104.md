# MedOrigin Core ↔ encrypted Workspace: atomic synthetic Bundle (2026-11-04)

**Owner:** Python Core functional slice, not Desktop/GUI. Private draft
stacked on #914 exact HEAD `138907ca1de67dfbf0d50ec3ce6d881e145700cd`.
**Status:** synthetic-only developer/test integration, **NO-GO for clinical
data, production keys, general-purpose FHIR Bundle import or release**.
No frozen root `pyproject.toml`, `uv.lock`, research manifest, donor code,
model or Desktop files changed.

## Real new behavior

`medscale.fhirkit.workspace_ingest.ingest_synthetic_bundle_atomic` is
an *optional* Core API, not a public `medscale` CLI import command.
It requires the same explicit `InMemoryTestKeyProvider` used to
initialize an already-open `medscale_workspace.storage.WorkspaceStore`,
a caller's `synthetic_only=True` attestation, actor ID and timestamp.
Production protected OS key selection still fails closed. A conventional
Core Wheel has **no mandatory Workspace/cryptography dependency**;
attempting this explicit integration without Workspace fails closed.

The existing #914 Core `inspect_synthetic_bundle` admits a bounded
`collection` Bundle with only Patient, Encounter and Observation and
local `urn:uuid` relationships. This bridge first copies the incoming
Python Bundle into a **strict, size-bounded, finite JSON snapshot**, then
preflights that snapshot. The snapshot prevents a caller's subsequent
in-memory mutation from changing committed content after validation.
The bridge is further limited to **16 resources** per test transaction.

Within a single already-open encrypted Workspace, it translates the
two supported local reference fields (`subject`, `encounter`) from
canonical `urn:uuid` to the existing Workspace bounded
`ResourceType/id` internal representation. Unknown fields and unsupported
Workspace structures are **refused**, not silently dropped. It prepares
the existing `FhirResource` records, deterministic Workspace identities,
encrypted provenance records and one append-only audit event in memory
before performing **one** `WorkspaceStore.put_objects_atomic` call.
The store's existing SQLite transaction and integrity seal either commit
all 2*N+1 encrypted objects (N FHIR resources, N provenance records,
one audit event) or roll back all of them. No separate sequential
patient/encounter/observation commit window remains in this test path.

**Not lossless/clinical FHIR interchange:** this transformation
is a narrow input adapter to the pre-existing owned Workspace schema.
It does not preserve original `urn:uuid` reference bytes inside stored
Workspace resource content; the input SHA-256 is retained in the encrypted
audit metadata and the redacted return receipt. It does **not** perform
HL7 R4 profile/terminology/invariant validation, clinical checks, arbitrary
FHIR Bundle reference resolution, external EHR connections or PHI admission.
The `synthetic` marker is caller-provided, never proof of PHI absence.

The return receipt includes only input SHA-256, counts, audit head digest
and explicit negative release/clinical flags. It prints no patient IDs,
name, free text, original JSON, encrypted key or filesystem path. Test
secrets exist only in memory and are neither stored in the repo nor
in an environment variable.

## Reproducible end-to-end demonstration (entirely fictional)

From a private source checkout with compatible local Core and Workspace
runtimes available on the Python import path:

```powershell
$env:PYTHONPATH = "src;apps/workspace/src"
py -3.14 examples/synthetic_fhir_bundle_preflight/atomic_workspace_demo.py --synthetic-only --ephemeral-demo
```

The demo accepts **no arbitrary input or persistent destination**.
It loads only the committed `fictional_bundle.json` fixture,
generates a disposable in-memory-only test key, creates an encrypted
temporary SQLite Workspace, commits the 3 resources, 3 provenance records
and 1 audit event in one transaction, verifies the audit chain,
closes and reopens with the same test key, verifies the chain again,
then deletes the task-only temporary store. Output is a redacted JSON
receipt with `SYNTHETIC_ENCRYPTED_ATOMIC_DEMO_PASS` and all release/
clinical claims false. Missing either opt-in flag refuses execution.

## Measured author-side evidence

- Windows Python3.14: 93 PASS, 1 SKIP, 2 DESELECTED in selected
  Core FHIR + atomic Workspace suites, Ruff PASS.
- Real native Workspace FHIR acceptance/adversarial regression: 17 PASS.
- Real encrypted roundtrip and reopen, provenance digest verification,
  audit verification, wrong-key refusal, synthetic bad-reference preflight,
  prepare-stage failure without write, replay conflict rollback, deliberate
  mid-transaction third-write failure and reopen-after-rollback,
  programmatic NaN/Infinity/non-JSON refusal, and input-mutation snapshot
  isolation covered by focused tests.
- Windows Python3.11 and3.12: 18 PASS each after installing pinned
  `cryptography==50.0.1`, `cffi==2.1.1` and required pycparser
  into **separate task-only directories**, borrowing a pure pytest
  installation with plugins disabled. Initial runs without matching
  binary dependencies **could not collect** (missing `_cffi_backend`);
  that environment failure was corrected, not counted as a passing test.
- Demo invocation on Windows Python3.14 succeeded with the redacted
  pass receipt, and missing flag refused with exit2. All fixtures fictional.
- Source-qualified Wheel/sdist and installed runtime validation are
  tracked separately and must not be assumed from source tests.

## Explicit remaining blockers

This optional integration uses Workspace's current internal
`_content_entries`, `_resource_references`, `_resource_version`
and private store provider identity to preserve existing storage
semantics; independent architecture review must qualify the coupling
before inclusion in a stable public API. Real OS-protected key provider
and operator authorization are **not implemented**. Hosted exact-head CI,
independent security/medical review, security advisories (#622), full
FHIR R4 qualification (#877), legacy demo false-valid (#882), external
launcher attestation (#893) and release governance (#574/#603) remain
**NO-GO**. Never infer release readiness from author-side synthetic QA.


## Exact-source projected package and real installed Core smoke

**Functional source SHA**: `9ee7493a06a9999ebff48da89cc08b61cab87251`
(stack base Draft #914 SHA `138907ca1de67dfbf0d50ec3ce6d881e145700cd`).

- A **task-only WSL Linux ext4** checkout of that exact source commit
  was independently staged through the repository's existing
  `stage_medorigin_core_projection.py` without modifying frozen
  `pyproject.toml`, `uv.lock`, archived research or tracked source bytes.
- `uv build --offline --no-create-gitignore` produced **LOCAL UNPUBLISHED**
  `medscale-0.3.0-py3-none-any.whl`, SHA-256:
  `ab7cdf6ea76be6606654c53497488a2ff3f8fe7da02e9860b05e427e0c92419e`.
- The sdist `medscale-0.3.0.tar.gz` SHA-256:
  `9937165bb42c854c3e9a0cababc3397c845504ad38a57d960ccc34e0598d6427`.
- Independent existing verification gates returned
  `SOURCE_BOUND_WHEEL_QUALIFIED_ONLY` and
  `SDIST_SCOPE_QUALIFIED_ONLY`, **zero issues**, exit0. These are
  source identity/scope verifiers, not release authorization.
- Copied the qualifying Wheel into a task-owned Windows QA folder,
  checked its exact SHA, and installed to a **local isolated --target**
  from local file using `pip --no-index --no-deps` (no package upload).
  Verified that the actually imported Core module was located inside
  the installed Wheel tree, not source checkout.
- With `PYTHONPATH` pointing at that installed Core + existing local
  Workspace source, native Windows Python3.14 with `-P -B -s` executed
  `atomic_workspace_demo.py --synthetic-only --ephemeral-demo`.
  Result: `SYNTHETIC_ENCRYPTED_ATOMIC_DEMO_PASS` / exit0,
  **3 encrypted FHIR resources, 3 encrypted provenance records,
  1 chained audit event, correct reopen, ephemeral DB removed**.
  `full_fhir_r4_conformance_established`, `clinical_use_authorized`
  and `publication_authorized` were all `false`.
- This test **does not** independently attest an installed generated
  Windows `medscale.exe` launcher (#893); the installed Python source
  module was invoked intentionally. The separate Workspace distribution
  was loaded from a local source path, **not** independently packaged and
  attest-tested in this run.

All source/digest evidence is author-side, nonpublishing and
synthetic-only. Nothing here resolves independent review, full FHIR
conformance, OS-protected production key management or hosted exact-head
CI. The disposable test artifacts should not be treated as signed
release files.
