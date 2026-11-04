# MedOrigin Core: verified synthetic FHIR Bundle encrypted readback

**Private developer/test-only feature, 2026-11-04. No PHI or production release authorization.**

## Product gap closed in this slice

Issue #921 observed that Core could atomically encrypt a synthetic FHIR
collection Bundle and its normalized Patient/Encounter/Observation resources,
but could not reconstruct the **original** `urn:uuid` `fullUrl` mappings
after reopening. Parent Draft #922 added a deterministic, encrypted original
Bundle manifest in the **same transaction** as the normalized resources,
their provenance, and one audit event.

This new slice builds on #922 and adds:
- `medscale_workspace.fhir_readback.read_synthetic_fhir_bundle_in_memory`
  as a narrow Workspace-owned, in-RAM, fail-closed test-only reader.
- `medscale.fhirkit.workspace_readback.read_synthetic_bundle_in_memory`
  as an optional Core wrapper that **re-runs Core synthetic Bundle
  preflight** on the reconstructed original and checks its canonical
  source SHA-256 and resource count.
- Real `medscale fhir workspace-demo --synthetic-only --ephemeral-demo`
  and the committed source-only encrypted fictional demo now reopen,
  verify and reconstruct their built-in fictional collections. They
  correctly expect **8** encrypted objects (3 FHIR resources + 3
  provenance + 1 audit event + 1 original Bundle manifest), not 7.
  The public CLI's **existing output shape** is retained, so downstream
  UI source-pinned receipts are not silently changed.

## Trust and consistency checks

The read API requires all of:

1. Explicit literal `synthetic_only=True` **and**
   `allow_in_memory_readback=True` (separate from import admission).
2. An **exact**, un-subclassed `InMemoryTestKeyProvider` object, identical
   to the provider originally bound to the open encrypted WorkspaceStore.
   No OS-protected production provider is enabled or bypassed.
3. The original import's SHA-256 source digest, an **externally retained
   audit-head digest**, and the original import's actor identifier.
   The actor ID is a local test assertion, **not authentication**.
4. A bounded, seal-verified, transaction-consistent in-memory Workspace
   snapshot. A capped object/envelope count is checked **before**
   snapshot decryption, followed by aggregate plaintext-size bounds.
5. The original Bundle's encrypted manifest, deterministic object
   identity, exact canonical JSON bytes, SHA-256 source digest, fixed
   `collection` shape and finite membership.
6. The **complete chain** of imported audit events, its externally
   retained head digest and one unambiguous **latest** import event for
   this source/actor, with the exact source digest, resource count,
   object order, immutable identities, revisions and content digests.
7. Every normalized stored FHIR resource revision, content bytes and
   deterministic resource identity against the original manifest;
   translation of only the two previously admitted local
   `subject`/`encounter` references; no unexpected revisions.
8. Each stored FHIR resource's immutable producer/source provenance:
   binding, producer actor/kind, source locator/version, review state,
   canonical bytes and digest. Any missing or mismatched record fails
   the whole read before a Bundle is returned.
9. The Core preflight re-verifies the reconstructed original Bundle:
   local `urn:uuid` reference closure, unique admitted resource
   entries, explicit synthetic marker and deterministic hash.

All failures return **fixed redacted reason tokens**. Neither API
writes recovered FHIR to a file or opens a network endpoint. No
clinical data is admitted; caller-supplied synthetic tags are
assertions and **not a PHI detector**. The authorized in-memory
response intentionally includes the fictional source payload; callers
must not log it, echo it to CLI, or persist it.

### Deliberate strictness

The readback requires the original import event to remain the most
recent audit event, and its head hash must match a separate caller
anchor. If additional events occurred, the caller must complete a
separately reviewed anchoring/read policy; this narrow developer
contract does not silently relax the consistency check.

The receipt remains `filesystem_export_performed=false`,
`clinical_use_authorized=false`,
`full_fhir_r4_conformance_established=false`, and
`release_authorized=false`. There is **no plaintext export API**,
production role-based authorization, EHR import/export, full FHIR R4
profile/terminology/invariant validation, signing, or publication.

## Evidence and regression tests

`tests/test_core_synthetic_bundle_encrypted_readback.py` exercises
the real AES-GCM encrypted SQLite store, closes/reopens, exact
`urn:uuid` original reassembly and canonical digest equality,
data-mutation immunity, missing manifest/provenance, unauthorized
actor, wrong test key, altered audit anchor, unexpected extra
resource revisions, modified snapshot, and denied implicit readback.

The existing original manifest, Core atomic ingestion, public Workspace
batch, Bundle preflight, and installed-CLI source test sets are
regression-checked. The CLI demo's public JSON schema and redacted
aggregate output remain unchanged. All testing is synthetic-only.

Source-owned package and runtime verification evidence is recorded
separately below after exact-source artifact qualification. The host
demonstration is **not** a release/certification gate.
