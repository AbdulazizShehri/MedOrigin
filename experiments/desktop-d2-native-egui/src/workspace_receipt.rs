//! Exact, source-pinned summary from the independently executed encrypted
//! Core + Workspace synthetic demo. No raw FHIR, DB/key or network capability.
//! Byte equality proves ONLY source membership, not origin or freshness.
use sha2::{Digest, Sha256};

const SOURCE_RECEIPT: &[u8] = include_bytes!("../fixtures/core/workspace-ephemeral-demo.json");
const SOURCE_SHA256: &str = "25acdb57db8ca3f11d353cf311167973760caaa95bb64de7339fe21e3b05cc2e";
const MAX_RECEIPT_BYTES: usize = 1024;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FictionalEncryptedWorkspaceReceipt {
    pub report_sha256: String,
    pub resource_count: u8,
    pub provenance_records: u8,
    pub audit_events: u8,
    pub verified_reopen: bool,
    pub ephemeral_store_removed: bool,
    pub disclosure: &'static str,
}

pub fn admit_source_pinned_encrypted_workspace_receipt(
    raw: &[u8],
) -> Result<FictionalEncryptedWorkspaceReceipt, &'static str> {
    if raw.is_empty() || raw.len() > MAX_RECEIPT_BYTES {
        return Err("fictional_workspace_receipt_size_refused");
    }
    // Exact canonical bytes means all JSON keys, types, boolean safety flags,
    // aggregate counts, ordering, duplicate keys and lack of trailing data
    // agree with the independently reviewed Core demo output.
    if raw != SOURCE_RECEIPT {
        return Err("fictional_workspace_receipt_not_source_pinned");
    }
    let digest: String = Sha256::digest(raw)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect();
    if digest != SOURCE_SHA256 {
        return Err("fictional_workspace_receipt_source_sha_refused");
    }
    Ok(FictionalEncryptedWorkspaceReceipt {
        report_sha256: digest,
        resource_count: 3,
        provenance_records: 3,
        audit_events: 1,
        verified_reopen: true,
        ephemeral_store_removed: true,
        disclosure: "Synthetic encrypted ephemeral Workspace QA only. NOT a patient record, authenticated Core receipt, persistent clinical workspace, or FHIR R4 validation.",
    })
}

pub fn inspect_compiled_encrypted_workspace_receipt()
-> Result<FictionalEncryptedWorkspaceReceipt, &'static str> {
    admit_source_pinned_encrypted_workspace_receipt(SOURCE_RECEIPT)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_compiled_encrypted_demo_metadata_is_source_bound() {
        let receipt = inspect_compiled_encrypted_workspace_receipt().unwrap();
        assert_eq!(receipt.report_sha256, SOURCE_SHA256);
        assert_eq!(
            (
                receipt.resource_count,
                receipt.provenance_records,
                receipt.audit_events
            ),
            (3, 3, 1)
        );
        assert!(receipt.verified_reopen && receipt.ephemeral_store_removed);
        assert!(receipt.disclosure.contains("NOT a patient record"));
    }

    #[test]
    fn modified_or_forged_encrypted_or_clinical_flag_refused() {
        for pattern in [
            (
                b"clinical_use_authorized\":false".as_slice(),
                b"clinical_use_authorized\":true ".as_slice(),
            ),
            (
                b"production_key_provider_used\":false".as_slice(),
                b"production_key_provider_used\":true ".as_slice(),
            ),
            (
                b"publication_authorized\":false".as_slice(),
                b"publication_authorized\":true ".as_slice(),
            ),
            (
                b"verified_reopen\":true".as_slice(),
                b"verified_reopen\":false".as_slice(),
            ),
            (
                b"resource_count\":3".as_slice(),
                b"resource_count\":4".as_slice(),
            ),
        ] {
            let (old, new) = pattern;
            let start = SOURCE_RECEIPT
                .windows(old.len())
                .position(|w| w == old)
                .unwrap();
            let mut altered = SOURCE_RECEIPT.to_vec();
            altered.splice(start..start + old.len(), new.iter().copied());
            assert!(admit_source_pinned_encrypted_workspace_receipt(&altered).is_err());
        }
    }

    #[test]
    fn trailing_bytes_malformed_partial_and_oversize_fail_closed() {
        for candidate in [
            Vec::new(),
            b"{}".to_vec(),
            [SOURCE_RECEIPT, b" "].concat(),
            [SOURCE_RECEIPT, b"\n"].concat(),
            SOURCE_RECEIPT[..SOURCE_RECEIPT.len() - 1].to_vec(),
            vec![b'x'; MAX_RECEIPT_BYTES + 1],
        ] {
            assert!(admit_source_pinned_encrypted_workspace_receipt(&candidate).is_err());
        }
    }
}
