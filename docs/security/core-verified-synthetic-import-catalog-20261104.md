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
