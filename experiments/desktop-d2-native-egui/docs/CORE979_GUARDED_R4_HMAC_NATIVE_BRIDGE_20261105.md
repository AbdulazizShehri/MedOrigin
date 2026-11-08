# MedOrigin D2: exact guarded Core #979 to official R4 and native HMAC worklist

**2026-11-05 | Owner-private, synthetic-only, no clinical approval.**

## Product correctness upgrade

Native Desktop #978 already supports genuine local Core #971, official HL7 R4 v4.0.1 JSON Schema structural preflight, real temporary AES-GCM encrypted FHIR file import and cold reopen, an HMAC-SHA256 per-launch framed redacted native worklist, read-only exploration and real Windows UIAutomation. The separate Core lineage progressed: #973 prevents Observation.subject referencing an Encounter belonging to a different Patient; #977 adds opt-in non-production Windows Credential Manager *synthetic* key preview; #979 repairs four guarded Workspace SHA256 admission modules without expanding package permissions.

This new opt-in launcher targets **exact clean private Core #979 SHA 440cee21494a62c458106631931f3610c05d1ea8**, not an unbounded arbitrary repository hash. Existing Core #971 source pin and CLI remain compatible. Before any encrypted import or GUI, it independently executes the actual Core #979 module's six-resource invented two-Patient Bundle preflight: correctly matched Observation/Encounter subjects must pass, mismatched persons must be refused with exact redacted observation_encounter_patient_mismatch, under both original and reversed entry ordering. The check is bounded, captures but never displays stderr/stdout, requires zero output and reattests the exact clean Git tree. It does not read user patient files, require login or make network requests.

The new runner passes only two compiled-in invented FHIR Bundles into the existing source-reviewed bridge: exact genuine offline official HL7 FHIR R4 JSON Schema ZIP SHA256 75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6, pinned jsonschema==4.25.1, structure-only gate BEFORE temporary AES-GCM encrypted Workspace import, independent physical close/reopen and audit/readback, disposable cleanup, strict negative clinical fields and source-redacted v1 report, fresh OS nonce/secret with domain-separated HMAC bound to the Rust native GUI worklist. The GUI remains strict read-only/source-scoped with no patient payload.

Crucially the Core #977 Windows Credential Manager persistent key adapter is **not** used in the new launcher; the original synthetic-only in-memory key path remains. This does not grant real patient key custody, PHI import, RBAC or clinical operation.

## Testing

- Physical owner Windows source Core #979 two-person positive and cross-person negative with reverse ordering: PASS.
- New Core979 pure Python contracts: 7/7 PASS Windows; existing legacy Core971 contracts: 7/7 PASS Windows; new Core979: 7/7 PASS Linux; Ruff lint and format PASS.
- Physical Windows owner actual clean Core979 source SHA 440cee21494a62c458106631931f3610c05d1ea8 and genuine offline HL7 FHIR R4 v4.0.1 ZIP SHA 75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6; isolated jsonschema 4.25.1. Real two-fictional-file structural preflight BEFORE ephemeral AES-GCM encrypted Workspace import, physical close/reopen, audit/readback and cleanup: PASS intentional nonclinical exit 2 with 0 stderr, canonical redacted receipt 1,837 bytes SHA256 41c04dca118a550f9d21976b9cc5f87a58954c96b125748ecb40729153eba057.
- Full native owner Windows offline locked Rust tests **91 lib + 15 CLI + 7 browser/network = 113/113 PASS**. Cargo fmt --check, strict clippy -D warnings, cargo build PASS. Actual Windows executable SHA256 a3c2bf608be83bf523300b77002541ef3a49f550803a78d7d03e89ed43ecf11f.
- ACTUAL compiled Windows GUI UIAutomation with live Core979 official R4/HMAC-bound session and source-scoped worklist, navigation/facet/reset/Clear: **PASS exit 0** (source script reuses older Core971 UIA marker, but explicit guarded Core979 opt-in source SHA and cross-person preflight are newly enforced). Real HMAC-bound normal GUI auto-close: **PASS exit 0**; 6 independent actual malicious-frame native subprocess denial tests (**unbound, tampered, stale nonce, wrong domain, missing secret, oversize**) **6/6 PASS** and no forbidden GUI admitted. New guarded Core979 wrapper marker GUARDED_CORE979_CROSS_PATIENT_PROBE_AND_R4_HMAC_WORKLIST_PASS_NONCLINICAL verified.
- Hosted exact-head native Windows 2025 / Ubuntu 24.04 CI and evidence validation: **PENDING independent GitHub completion after this evidence-only documentation update**; do not claim production qualification from it.

## Release restrictions

PRIVATE DRAFT / NO-GO. A narrow local reference check is not full FHIR R4 semantics, terminology/profile/FHIRPath or clinical safety validation. No persistent patient key custody, authenticated human roles, consent, production Core process attestation, packet-level isolation, approved signed Windows installer or security/clinical review. Do not enable real patient data, public publishing, protected-main merge, deployments or paid network services.
