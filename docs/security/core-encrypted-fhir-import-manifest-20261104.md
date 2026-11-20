# Core encrypted synthetic FHIR import manifest — 2026-11-04

## Scope

Private, unpublished incremental product work stacked on Draft #918. The Core synthetic-only atomic Bundle ingestion now supplies its immutable preflighted original collection Bundle to the public Workspace batch facade. Workspace independently checks the canonical JSON SHA-256, collection type, resource count and exact resource-type/ID membership, then writes one additional encrypted `FhirImportManifest` object in the **same SQLite transaction** as N normalized FHIR resources, N provenance records and one audit event.

The manifest is addressed by a deterministic workspace-scoped object identity derived from the original source digest and has immutable revision `1`. It preserves original `urn:uuid` fullUrls and references that were lost during normalized Workspace import. The original source bytes are canonical JSON bytes, not the original whitespace or file encoding; the source digest contract is canonical JSON SHA-256. The caller-visible receipt contains only the new manifest count, not payload/IDs.

## Evidence and limits

On native Windows Python 3.14, the three relevant source-controlled test modules passed **31/31** with a task-owned pytest base temp, disabled plugin autoload and `--noconftest`. Added positive encrypted manifest read-after-reopen, ciphertext-only SQLite inspection, source digest mismatch and resource membership mismatch rejection. Existing rollback/replay/audit tests passed with the new eight-object transaction contract. Ruff lint and git diff checks passed. These are author-side source tests only, not installed-Wheel or hosted CI qualification.

**Not complete:** No authorized public readback/export facade yet. The manifest is a prerequisite for a future readback that independently checks each normalized stored resource, provenance revision, audit chain and original UUID reference closure against the manifest before returning an in-memory collection Bundle. No plaintext filesystem export is authorized. A direct Workspace caller can supply a syntactically matched manifest with fields that do not correspond to normalized resource payloads; future readback must independently detect that mismatch. This patch is **not** proof of full FHIR R4 conformance, production key custody, security audit or release readiness.

No UI/native Desktop, frozen root project/lock/MRL, publisher, protected main or clinical data was touched. Keep issue #921 OPEN until the full authenticated readback vertical slice passes source and installed-artifact E2E.
