# MedOrigin Core — verified synthetic FHIR import catalog

**2026-11-04 | Private developer/test-only feature. No clinical or publication GO.**

## Product capability

Core can now display a bounded **metadata-only list** of synthetic
encrypted FHIR Bundle imports from a real WorkspaceStore, without
returning a single patient name, FHIR resource body, `urn:uuid`
fullUrl, host file path, key or plaintext export. This builds on
the exact-source encrypted manifest and dual-audit-anchor readback
in private Draft PRs #922, #926 and #927.

The list is useful for choosing a previously imported fictional Bundle
by **original source SHA-256** and **import audit event SHA-256**, then
invoking the existing explicitly authorized in-memory readback. It is
*not* a patient roster, authentication system, history of clinical
modifications, full FHIR R4 validator or EHR interoperability claim.

The functionality lives in independent public narrow test APIs:
`medscale_workspace.fhir_catalog.list_verified_synthetic_fhir_imports`
and `medscale.fhirkit.workspace_catalog.list_synthetic_bundle_imports`.
Core keeps Workspace encryption/storage internals inside Workspace;
the separate Core facade rejects any unexpected extra fields or
arbitrary sensitive downstream output.

## Explicit installed CLI demo

From a Core+optional Workspace Wheel pair installed locally:

```sh
medscale fhir workspace-catalog-demo --synthetic-only --ephemeral-demo
```

Or equivalently invoke the installed Core Python console dispatcher,
without relying on a source tree. The two flags must appear **exactly
once** and no caller input, arbitrary FHIR file, path, provider, network
or persistence setting is admitted. Unknown tokens are never echoed.

This demo creates *two hard-coded fictional* collection Bundles, first
with three resources, second with one distinct Patient; a benign
Workspace-open audit event is appended between them. It verifies the
real AES-GCM Workspace's **13 encrypted objects**, closes/reopens the
database, verifies the full three-event chain from an externally retained
audit head, reconstructs both original Bundles **in memory** and
returns only a minimal verified index (source hashes, import audit
hashes, sequence numbers, record counts). The encrypted temporary
store is deleted **before** returning the aggregate JSON receipt.

The CLI returns
`SYNTHETIC_ENCRYPTED_CATALOG_DEMO_PASS` on successful execution;
it always reports
`clinical_use_authorized=false`,
`full_fhir_r4_conformance_established=false` and
`publication_authorized=false`. This is a proof of synthetic
encryption and catalog plumbing only, not a clinical validation
or Windows console-launcher chain-of-custody certificate.
The existing `fhir workspace-demo` command and its receipt
schema are **untouched** for ongoing Desktop integrations.

## Trust boundary and safe index shape

The Workspace catalog explicitly requires:
- `synthetic_only=True`, independently
  `allow_in_memory_listing=True`;
- the same **exact** `InMemoryTestKeyProvider` object originally
  supplied to the opened store. Any production or different provider
  is denied;
- caller's source-controlled fictional actor-id assertion, **not a
  login credential or production authorization check**;
- a syntactically valid 64-hex current audit-head SHA256 that must
  equal the fully verified chained event log's current head;
- transaction-consistent seal-verified snapshots bounded by
  object count (128), encrypted bytes (8 MiB), decrypted bytes
  (6 MiB), and source event count (1–16 requested, upper max 16).

Only exact three-field source-import audit events for that actor
are admitted, with source SHA, resource count (1–16) and event
sequence. The entire candidate list is validated, then each
candidate's actual encrypted manifest, original FHIR source digest,
normalized resource versions, all provenance records and post-import
audit restrictions are rechecked using #927's existing fail-closed
in-memory readback. **No partial catalog is returned** if one
entry is bad or max_imports was exceeded.

The result is stable and ordered chronologically by audit sequence.
Each entry contains exactly
`{source_content_sha256, import_audit_event_digest, audit_sequence,
resource_count}`. The enclosing receipt holds a verified current
audit digest, import count and five **false** clinical/export/release
authority flags. No extra UI-facing patient labels or descriptions.
An actor with no matching imports gets an empty list under an
otherwise valid verified audit chain; this is **not authorization**.

The original source data is transiently decrypted within the bounded
in-memory verifier and **discarded**, never logged, returned from
the catalog or written in plaintext. Caller-resolved source digests
can themselves reveal information for real patient datasets, therefore
the entire catalog is explicitly restricted to fabricated synthetic
data. No automatic public sharing or remote telemetry.

If the audited store changes concurrently, the caller must retain
and re-verify the latest audit head before relying on the index;
the receipt describes **the externally anchored verified state**,
not an unconditional promise that no newer event has occurred.

## Regression plan and evidence

- New source test modules:
  `tests/test_core_verified_synthetic_import_catalog.py`,
  `tests/test_core_portable_synthetic_catalog_cli.py`.
- Real encrypted two-import cycle with unrelated audit event,
  close/reopen, verify safe index order/digests/counts, and
  select/reconstruct original source with existing Core readback.
- Wrong provider, absent consent, malformed/forged audit digest,
  invalid or too-small limits, missing encrypted manifest,
  later protected-object audit changes, and sensitive error/CLI
  arguments are denied without partial metadata disclosure.
- The original Core FHIR/Workspace importer, historical readback,
  native public Core dispatcher and previous demo remain covered.

**Still NO-GO**: real patient data, production OS key custody and
role permissions, qualified full HL7 FHIR R4 structural/profile/
terminology/invariant validation, independently reviewed security and
clinical acceptance, dependency vulnerabilities, source-qualified
native Windows console launcher, hosted exact-head CI, signing,
main merge or release/publication.


## Exact-source offline package and installed-runtime evidence

**Functional Git commit:** `a3eb7b4b29ee031df4a891a1bc091614ebb7d1f8`.

A task-only Ubuntu WSL2 ext4 Git checkout pinned to that exact SHA
was projected with the existing repository Core staging script.
Both Core and Workspace were built **offline** using
`uv build --offline --no-create-gitignore`; the protected source tree's
root `pyproject.toml` and `uv.lock` were unchanged.

Pre-existing Core artifact identity gates for both Wheel and sdist
completed with **zero issues**:
`SOURCE_BOUND_WHEEL_QUALIFIED_ONLY` and
`SDIST_SCOPE_QUALIFIED_ONLY`. Six Core source modules including
the new public CLI and catalog APIs, and **all 35 Workspace Python
modules**, were byte-identical inside the exact built Wheels.

Unpublished local artifact SHA-256 digests:

- Core Wheel `medscale-0.3.0-py3-none-any.whl`:
  `b23dd717189218f40c8154ea2905c5e20901f1a7a94d4cee584ef83e6b87f7a8`.
- Core sdist `medscale-0.3.0.tar.gz`:
  `0614936321d71181be48442cd8261114385bc1db362f8cc67a3e6fe86639d6f1`.
- Workspace Wheel `medscale_workspace-0.1.0.dev1-py3-none-any.whl`:
  `9a957dceaeac0ea8678999a87c472ae73d64cb8454235038aa007d1c5078a8fd`.
- Workspace sdist `medscale_workspace-0.1.0.dev1.tar.gz`:
  `ca83d5321d11b48575ebde48dc6fa9a777eb4b20cca993364e066ffa239e08b3`.

**Both exact SHA-checked Wheels** were installed side by side via
`pip --no-index --no-deps --target` into a disposable Windows
directory (no global package mutation). The isolated test script
asserted **eight imported Core/Workspace modules** including the
new catalog and CLI entry-point resolve from the Wheel install
destination, not the repository sources.

The same real installed-Wheel verification completed **exit0 on all
three native Windows versions Python 3.14, 3.11.15 and 3.12.13**:

- Two independent fictional encrypted FHIR Bundle imports with
  a benign intervening audit event, **13 encrypted objects**;
  close/reopen and verify source/canonical FHIR resource digests,
  immutable provenance and original/current audit anchors for both
  old and recent Bundle entries.
- Return **only** two source/audit digests and resource/sequence
  counts, no original payload fields. Using each safe selector,
  independently read back and match the original fictional
  FHIR Bundle in memory. Bytes of the encrypted SQLite file
  contain no invented name or `urn:uuid:` strings.
- Temporary encrypted workspace deleted; proof
  `EXACT_TWO_INSTALLED_WHEELS_VERIFIED_CATALOG_PASS`, clinical/full-R4
  flags **false**.
- Installed public Core **Python CLI dispatcher**
  `fhir workspace-catalog-demo --synthetic-only --ephemeral-demo`
  returned exit0, `SYNTHETIC_ENCRYPTED_CATALOG_DEMO_PASS`,
  `import_count=2`, `resource_count=4`, and cleaned the
  temporary store on all three runtimes.
- Python 3.11/3.12 used separate task-only pinned binary
  `cryptography==50.0.1` and `cffi==2.1.1` local dependencies.
  These are NOT independently production-approved supply-chain
  attestations.

The wider native Windows Python3.14 source/Core/Workspace/FHIR
adversarial regression completed **157 PASS, 2 DESELECTED**.
The two excluded historical raw-Wheel fixture tests need an unavailable
external build executable and are not represented as passes.
Ruff checks/format and Git whitespace checks PASSED.

**No hosted exact-HEAD CI, independent security or medical review
or native installed `medscale.exe` console launcher provenance
is implied by this evidence.** The packaged CLI validation was through
the installed Python dispatcher, not the OS console shim. PR remains
private DRAFT and full release/clinical status **NO-GO**. No
artifact was signed, merged to protected main, uploaded or published.
