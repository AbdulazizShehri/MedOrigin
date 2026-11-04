# Encrypted, source-attested synthetic FHIR R4 structural result

**MedOrigin Core/Clinical Workspace — private developer test only, 2026-11-04.**

## Missing product capability closed

The Core product could previously **(a)** import a fictional FHIR collection
Bundle into an AES-GCM encrypted Workspace with immutable source manifest,
per-resource provenance and audit, and **(b)** compute a truthful,
source-pinned **partial** R4 structural-only `OperationOutcome` using the
official HL7 v4.0.1 JSON Schema. These paths were not connected: the result
could not be bound to an already encrypted imported Bundle and recovered
with the exact same source and audit lineage.

This feature connects them with one executable end-to-end workflow:

1. Admit the fictional Bundle using Core's existing strict synthetic-only
   preflight; commit all resources, their provenance, the original source
   manifest and one audit event in **one** encrypted Workspace transaction.
2. Core reads back the **original** Bundle from its encrypted manifest,
   verifying externally retained source SHA-256 and **two audit anchors**,
   the complete chained audit, normalized FHIR/resource revisions,
   provenance and local `urn:uuid` reference closure. No caller-provided
   report or alternate plaintext Bundle can replace the stored source.
3. Core validates this exact original Bundle with the **offline,
   SHA-pinned official HL7 FHIR R4 4.0.1 JSON Schema** and
   `jsonschema==4.25.1`, producing a **structural-only** report
   (`invalid` or `not_validated`, NEVER `valid`). Using the
   restricted Core OperationOutcome converter, the result carries
   only fixed allowlisted error **keyword names** and a mandatory
   incomplete-coverage warning.
4. Workspace independently validates the bounded, redacted
   `OperationOutcome` vocabulary, actor and key-provider exact
   identity, source/current audit digests, and encrypted original
   import. It persists **three encrypted objects in one transaction**:
   a deterministic immutable `FhirStructuralOutcome` object, its
   content-bound provenance referencing the source SHA and original
   import audit event, and one append-only chained audit object
   referencing the exact Outcome bytes/digest. No partial writes.
5. Reopening the encrypted database and supplying the same exact
   test key plus **externally retained** source/import, current
   audit-head and stored receipt digests allows Core to reverify
   original imported Bundle, immutable encrypted receipt payload,
   provenance and complete audit chain before returning the in-memory
   **already-redacted** Outcome.

The explicit Core APIs are:

- `medscale.fhirkit.workspace_structural.validate_and_store_imported_synthetic_bundle_structure`
- `medscale.fhirkit.workspace_structural.read_imported_synthetic_structural_result`

Workspace exclusively owns the real storage transaction and key internals.
No Core private-storage writes or Desktop/UI changes.

## Public, source-only demonstration

```text
medscale fhir encrypted-structural-demo --synthetic-only --ephemeral-demo --offline-r4-schema OFFICIAL_R4_ZIP
```

This command runs one built-in, **invented** three-resource FHIR Bundle only.
It accepts **no arbitrary FHIR file**, no output directory, no patient
record, and no EHR/network target. The supplied official schema ZIP must
pass Core's exact archival SHA, metadata/size checks; the local validator
must be the exact pinned version. Unknown flags are refused without
echoing unknown paths. A task-local in-memory test key powers disposable
encrypted SQLite storage. The source is imported, truly checked,
its truthful structural Outcome encrypted and audited, the store
closed/reopened and the Outcome reverified. Then the temporary database
is deleted **before** printing a **metadata-only** JSON summary.

On working *demo plumbing*, the CLI exit code is **0** and its status is
`SYNTHETIC_ENCRYPTED_R4_STRUCTURAL_RECEIPT_PASS`. This is **NOT**
a structural/FHIR conformance success. A separate
`structural_status` is always either **`not_validated`** or
**`invalid`**, and **all three** authority flags for FHIR validation,
clinical use and release are **false**. The prior independent
`structural-outcome` command continues to exit **2** for both
structural pass and invalid input, and the pre-existing
`workspace-demo`/catalog demo commands are unaffected.

## Enforced restrictions and evidence

- Both import and encrypted-result writes/readbacks require literal
  `synthetic_only=True` with independent explicitly admitted
  `allow_encrypted_receipt_write=True` or
  `allow_in_memory_readback=True`.
- `test_key_provider` must be the **exact**
  `InMemoryTestKeyProvider` instance used to open the encrypted
  Workspace; a production OS-key provider is NOT admitted.
- Stores are bounded by <=128 encrypted objects and <=8 MiB of
  encrypted envelopes before any sensitive reconstruction.
  Original FHIR source is bounded by existing Core import contracts.
- Structural receipts must have exactly the declared finite
  `OperationOutcome` shape. Error issues admit only a fixed known
  JSON Schema keyword set (maximum 12 plus optional truncation),
  and every report must include the exact nonconformance warning.
  `valid`, patient names, arbitrary diagnostics, extra members,
  missing warnings or mixed status/issue counts are refused.
- Each `FhirStructuralOutcome` immutable object is deterministically
  identified by source SHA + source import event digest. Repeating
  a commit fails on immutable store conflict, without partially
  writing a new audit event or overwriting the old one.
- Original sources are rechecked against both the original import
  event and the current anchored chain. Output readback rechecks
  the exact receipt bytes SHA-256, canonical JSON, provenance
  source reference and full audit event reference/digest.
- The **stored** Outcome is encrypted despite containing only
  static redacted diagnostics; no file-plaintext export API is
  introduced. The public demo emits only digests/counts/status.
- No real patient data, clinical diagnosis, external EHR write,
  network service or new dependency is enabled. Synthetic assertion
  is NOT a PHI classifier, caller actor string is NOT authentication,
  and a scoped test key is NOT production key custody.

## Source testing and independent release limits

`tests/test_core_encrypted_r4_structural_receipt.py` performs real
encrypted source import -> structured partial R4 check -> atomic
receipt/provenance/audit persistence -> close/reopen -> source/audit-
anchored readback. It tests no plaintext SQLite substrings,
invalid structural errors versus structural-only passing status,
missing/fake FHIR source anchors, unqualified schema, wrong test key,
unauthorized read/write, forged `valid` or data-bearing Outcome,
attempted overwrites, missing provenance, and public demo
misuse/refusal. Source-controlled opt-in real HL7 ZIP integration
is run using `MEDORIGIN_OFFICIAL_R4_SCHEMA_ZIP`.

The official ZIP downloaded into a *task-only* Windows QA directory
matched the pinned official SHA-256
`75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6`.
The test dependency `jsonschema==4.25.1` was installed in a
separate task-owned directory; the user's general Python package
set was not modified. In the initial source test matrix:
**24 passed, 1 skipped** (the real ZIP was not provided to that
run); when supplied, **25 passed** and the installed-style Core
CLI executed against real pinned HL7 schema, returning an
ephemeral encrypted-proof receipt with **11 encrypted objects**,
**2 audit events**, verified close/reopen and removed temp store,
still `not_validated` and no clinical/release authority.

Expanded source tests, exact-source package verification and
native installed Wheel results should be added below only when
independently demonstrated.

**Release NO-GO.** Full HL7 FHIR R4 profiles, terminology, FHIRPath
invariants, reference conformance and clinical use remain
unimplemented/unqualified. OS-managed production key custody,
RBAC, independent security and medical review, dependency
advisories, native console-shim provenance, hosted CI, signed
release, founder approval and protected-main merge remain
separate blocked gates. This is not a healthcare production
certificate or a justification to process actual PHI.


### Post-readback audit and expanded regression evidence

The source test suite was extended with a **separate** negative case:
a later independently anchored `WORKSPACE_OPEN` audit event leaves
an immutable structural result readable, while a later
`OBJECT_CREATE` audit reference touching its encrypted
`FhirStructuralOutcome` object explicitly blocks readback.
Readback also compares the complete stored provenance bytes with
canonical provenance, verifies the producer/version and rejects
unrecognized post-receipt destructive event types or later
references to that outcome/provenance object.

On the final changed source, native Windows Python3.14 executed
a wider Core/Workspace encryption, provenance, audit, FHIR, installed
CLI source and adversarial test subset with the real official
SHA-qualified HL7 R4 ZIP and test-only qualified jsonschema 4.25.1:
**276 PASSED, 2 DESELECTED**, Ruff lint/format PASS, Git
whitespace PASS. The two historical raw-Wheel fixture tests
depend on an external build executable missing in this
harness; these are NOT treated as passes. No deployed source,
OS-native signed launcher, independent security review or
clinical acceptance is claimed from this result.
