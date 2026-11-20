# D2 fictional JSON path difference — nonpublishing evidence

Source lineage: private Draft #861, parent a42515f67983d53ff9f3c73cc65dc9f22d14f935.
Scope: Native eframe GUI, fixed source-compiled fictional Patient, Observation and Bundle JSON only.

## Product behavior
- A developer can compare two separately SHA-256-verified, allowlisted fictional JSON payloads.
- In addition to raw byte and bounded HEX comparisons, the GUI displays the first differing JSON Pointer path, with escaped tilde and slash keys and array indices.
- Deterministic shared-key-first comparison distinguishes a changed value, JSON type, missing field, or array length.
- A bounded depth of 32 and parser failure refuse the semantic hint. The result is cleared on selection change, re-verification or any failed comparison.
- A semantic hint is NOT FHIR R4 clinical validation, network packet containment, or a release authorization.
- No user file import, PHI, EHR, network, telemetry, clipboard, or persistence.

## Evidence boundary
- Tests cover structural equality with different formatting, changed resourceType, escaped pointer keys, arrays, missing fields, malformed JSON, invalid selection, and stale-result clearing.
- Native Windows cargo test, cargo fmt, cargo clippy receipts must be recorded at the exact committed head.
- Hosted CI is not claimed unless the private free-minute budget and exact-head runs are verified.
- All release blockers #574 #603 #622 #662 #673 #676 remain NO-GO; no protected-main merge or publication.
