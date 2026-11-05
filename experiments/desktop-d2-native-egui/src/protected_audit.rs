//! Strict Core #981 source-shaped fictional protected-audit verification receipt.
//! Read-only source metadata: NEVER a patient record or clinical consent.
//! Sender admission is a separately domain-bound per-launch HMAC session.
use serde_json::Value;
use sha2::{Digest, Sha256};

pub const MAX_AUDIT_RECEIPT_BYTES: usize = 1024;
const FIELDS: &[&str] = &[
    "schema",
    "status",
    "operation",
    "verified_audit_events",
    "audit_head_sha256",
    "anchor_matched",
    "protected_credential_destroyed",
    "encrypted_workspace_store_preserved",
    "patient_data_admitted",
    "fhir_r4_conformance_validated",
    "clinical_use_authorized",
    "production_key_provider_selected",
    "publication_authorized",
];

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FictionalProtectedAudit {
    pub verified_events: usize,
    pub receipt_sha256: String,
}

/// Bounded, canonical, *verify-only* status of an already existing imaginary
/// Windows OS-protected encrypted Workspace. No create/forget or patient data.
pub fn admit_protected_audit_verification(
    raw: &[u8],
) -> Result<FictionalProtectedAudit, &'static str> {
    if raw.is_empty() || raw.len() > MAX_AUDIT_RECEIPT_BYTES {
        return Err("fictional_protected_audit_size_refused");
    }
    let value: Value =
        serde_json::from_slice(raw).map_err(|_| "fictional_protected_audit_json_refused")?;
    let object = value
        .as_object()
        .ok_or("fictional_protected_audit_not_object")?;
    if object.len() != FIELDS.len() || !FIELDS.iter().all(|name| object.contains_key(*name)) {
        return Err("fictional_protected_audit_unknown_or_missing_field");
    }
    // Equality to serde_json's sorted canonical output rejects duplicate keys,
    // whitespace, CRLF and malicious extra source fields.
    let mut canonical =
        serde_json::to_vec(&value).map_err(|_| "fictional_protected_audit_canonical_refused")?;
    canonical.push(b'\n');
    if canonical != raw {
        return Err("fictional_protected_audit_noncanonical");
    }
    if value["schema"] != "medorigin-core-windows-synthetic-protected-audit-preview/v1"
        || value["status"] != "FICTIONAL_WINDOWS_PROTECTED_AUDIT_PREVIEW_ONLY"
        || value["operation"] != "verify"
        || value["verified_audit_events"].as_u64() != Some(1)
        || !value["audit_head_sha256"].is_null()
        || value["anchor_matched"] != true
        || value["protected_credential_destroyed"] != false
        || value["encrypted_workspace_store_preserved"] != false
        || [
            "patient_data_admitted",
            "fhir_r4_conformance_validated",
            "clinical_use_authorized",
            "production_key_provider_selected",
            "publication_authorized",
        ]
        .iter()
        .any(|name| value[*name] != false)
    {
        return Err("fictional_protected_audit_unapproved_operation_or_claim");
    }
    Ok(FictionalProtectedAudit {
        verified_events: 1,
        receipt_sha256: Sha256::digest(raw)
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn sample() -> Value {
        json!({
            "schema":"medorigin-core-windows-synthetic-protected-audit-preview/v1",
            "status":"FICTIONAL_WINDOWS_PROTECTED_AUDIT_PREVIEW_ONLY",
            "operation":"verify",
            "verified_audit_events":1,
            "audit_head_sha256":null,
            "anchor_matched":true,
            "protected_credential_destroyed":false,
            "encrypted_workspace_store_preserved":false,
            "patient_data_admitted":false,
            "fhir_r4_conformance_validated":false,
            "clinical_use_authorized":false,
            "production_key_provider_selected":false,
            "publication_authorized":false
        })
    }
    fn bytes(value: &Value) -> Vec<u8> {
        let mut raw = serde_json::to_vec(value).unwrap();
        raw.push(b'\n');
        raw
    }

    #[test]
    fn only_verified_read_only_audit_admitted() {
        let source = admit_protected_audit_verification(&bytes(&sample())).unwrap();
        assert_eq!(source.verified_events, 1);
        assert_eq!(source.receipt_sha256.len(), 64);
    }

    #[test]
    fn destructive_actions_or_positive_patient_clinical_claims_rejected() {
        for field in FIELDS {
            let mut altered = sample();
            altered.as_object_mut().unwrap().remove(*field);
            assert!(admit_protected_audit_verification(&bytes(&altered)).is_err());
        }
        for (field, value) in [
            ("operation", json!("forget")),
            ("operation", json!("create")),
            ("verified_audit_events", json!(0)),
            ("verified_audit_events", json!(true)),
            ("audit_head_sha256", json!("0".repeat(64))),
            ("anchor_matched", json!(false)),
            ("protected_credential_destroyed", json!(true)),
            ("encrypted_workspace_store_preserved", json!(true)),
            ("patient_data_admitted", json!(true)),
            ("fhir_r4_conformance_validated", json!(true)),
            ("clinical_use_authorized", json!(true)),
            ("production_key_provider_selected", json!(true)),
            ("publication_authorized", json!(true)),
        ] {
            let mut altered = sample();
            altered[field] = value;
            assert!(
                admit_protected_audit_verification(&bytes(&altered)).is_err(),
                "unreviewed field {field}"
            );
        }
        let mut extra = sample();
        extra["patient_id"] = json!("NOT_ALLOWED");
        assert!(admit_protected_audit_verification(&bytes(&extra)).is_err());
    }

    #[test]
    fn rejects_duplicate_names_extra_bytes_and_noncanonical_serialization() {
        let raw = bytes(&sample());
        for invalid in [
            vec![],
            raw[..raw.len() - 1].to_vec(),
            [raw.as_slice(), b" "].concat(),
            [raw.as_slice(), b"\n"].concat(),
            [b" ".as_slice(), raw.as_slice()].concat(),
            vec![b'x'; MAX_AUDIT_RECEIPT_BYTES + 1],
        ] {
            assert!(admit_protected_audit_verification(&invalid).is_err());
        }
        let duplicate = String::from_utf8(raw).unwrap().replace(
            "\"anchor_matched\":true",
            "\"anchor_matched\":true,\"anchor_matched\":true",
        );
        assert!(admit_protected_audit_verification(duplicate.as_bytes()).is_err());
    }
}
