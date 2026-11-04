//! One-shot fixed fictional metadata-only import history from actual Core.
//! SHA-matching a source-compiled receipt is NOT sender authentication.
//! No PHI, raw FHIR, network, subprocess, live patient store, or clinical use.
use serde_json::Value;
use sha2::{Digest, Sha256};

const FIXED_CATALOG: &[u8] = include_bytes!("../fixtures/core/encrypted-import-catalog-demo.json");
const FIXED_SHA: &str = "cfa5c71cd07763b6a1b32f7e6de8c51c565c4b6caf09224c51fcba095263b623";
pub const MAX_CATALOG_BYTES: usize = 1024;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FictionalImportEntry {
    pub source_content_sha256: String,
    pub import_audit_event_digest: String,
    pub audit_sequence: u64,
    pub resource_count: u64,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FictionalEncryptedImportCatalog {
    pub report_sha256: String,
    pub imports: Vec<FictionalImportEntry>,
    pub resource_count: u64,
    pub verified_audit_events: u64,
    pub ephemeral_store_removed: bool,
    pub disclosure: &'static str,
}

pub fn admit_exact_fictional_import_history(
    raw: &[u8],
) -> Result<FictionalEncryptedImportCatalog, &'static str> {
    if raw.is_empty() || raw.len() > MAX_CATALOG_BYTES {
        return Err("fictional_import_catalog_size_refused");
    }
    // Byte equality rejects duplicate keys, trailing text/whitespace,
    // reordering, extra fields, forged clinical claims, and noncanonical JSON.
    if raw != FIXED_CATALOG {
        return Err("fictional_import_catalog_unreviewed_source_bytes");
    }
    let digest = Sha256::digest(raw)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    if digest != FIXED_SHA {
        return Err("fictional_import_catalog_source_digest_refused");
    }
    let source: Value =
        serde_json::from_slice(raw).map_err(|_| "fictional_import_catalog_json_refused")?;
    let value = |key: &str| {
        source
            .get(key)
            .and_then(Value::as_u64)
            .ok_or("fictional_import_catalog_numeric_field_refused")
    };
    let flag_false = |key| source.get(key).and_then(Value::as_bool) == Some(false);
    if source.get("schema").and_then(Value::as_str)
        != Some("medorigin-ephemeral-fhir-import-catalog-demo/v1")
        || source.get("status").and_then(Value::as_str)
            != Some("SYNTHETIC_ENCRYPTED_CATALOG_DEMO_PASS")
        || value("import_count")? != 2
        || value("resource_count")? != 4
        || value("verified_audit_events")? != 3
        || source
            .get("ephemeral_store_removed")
            .and_then(Value::as_bool)
            != Some(true)
        || !flag_false("payload_included")
        || !flag_false("clinical_use_authorized")
        || !flag_false("full_fhir_r4_conformance_established")
        || !flag_false("publication_authorized")
    {
        return Err("fictional_import_catalog_false_clinical_proof");
    }
    let records = source
        .get("imports")
        .and_then(Value::as_array)
        .ok_or("fictional_import_catalog_entries_missing")?;
    if records.len() != 2 {
        return Err("fictional_import_catalog_entry_count_refused");
    }
    let mut imports = Vec::with_capacity(2);
    for (index, record) in records.iter().enumerate() {
        let sha = |key| {
            let digest = record
                .get(key)
                .and_then(Value::as_str)
                .ok_or("fictional_import_catalog_entry_sha_missing")?;
            if digest.len() != 64
                || !digest
                    .bytes()
                    .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
            {
                return Err("fictional_import_catalog_entry_sha_refused");
            }
            Ok::<String, &'static str>(digest.to_owned())
        };
        let audit_sequence = record
            .get("audit_sequence")
            .and_then(Value::as_u64)
            .ok_or("fictional_import_catalog_audit_sequence_missing")?;
        let resource_count = record
            .get("resource_count")
            .and_then(Value::as_u64)
            .ok_or("fictional_import_catalog_import_count_missing")?;
        if (index == 0 && (audit_sequence, resource_count) != (1, 3))
            || (index == 1 && (audit_sequence, resource_count) != (3, 1))
        {
            return Err("fictional_import_catalog_sequence_or_count_refused");
        }
        imports.push(FictionalImportEntry {
            source_content_sha256: sha("source_content_sha256")?,
            import_audit_event_digest: sha("import_audit_event_digest")?,
            audit_sequence,
            resource_count,
        });
    }
    if imports[0].source_content_sha256 == imports[1].source_content_sha256
        || imports[0].import_audit_event_digest == imports[1].import_audit_event_digest
    {
        return Err("fictional_import_catalog_duplicate_history_refused");
    }
    Ok(FictionalEncryptedImportCatalog {
        report_sha256: digest,
        imports,
        resource_count: 4,
        verified_audit_events: 3,
        ephemeral_store_removed: true,
        disclosure: "FICTIONAL ENCRYPTED IMPORT HISTORY ONLY. Sender/freshness NOT authenticated. FHIR R4 NOT validated. No patient data, production keys or release permission.",
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_core_generated_catalog_contains_two_historical_encrypted_imports() {
        let catalog = admit_exact_fictional_import_history(FIXED_CATALOG).unwrap();
        assert_eq!(catalog.report_sha256, FIXED_SHA);
        assert_eq!(catalog.imports.len(), 2);
        assert_eq!(catalog.imports[0].audit_sequence, 1);
        assert_eq!(catalog.imports[0].resource_count, 3);
        assert_eq!(catalog.imports[1].audit_sequence, 3);
        assert_eq!(catalog.imports[1].resource_count, 1);
        assert_eq!(catalog.resource_count, 4);
        assert!(catalog.disclosure.contains("NOT authenticated"));
    }

    #[test]
    fn arbitrary_or_forged_clinical_history_is_not_admitted() {
        let candidates = [
            Vec::new(),
            b"{}".to_vec(),
            [FIXED_CATALOG, b"\n"].concat(),
            [FIXED_CATALOG, b" "].concat(),
            FIXED_CATALOG[..FIXED_CATALOG.len() - 1].to_vec(),
            vec![b'A'; MAX_CATALOG_BYTES + 1],
        ];
        for candidate in candidates {
            assert!(admit_exact_fictional_import_history(&candidate).is_err());
        }
        for (from, to) in [
            (
                b"clinical_use_authorized\":false".as_slice(),
                b"clinical_use_authorized\":true ".as_slice(),
            ),
            (
                b"publication_authorized\":false".as_slice(),
                b"publication_authorized\":true ".as_slice(),
            ),
            (
                b"import_count\":2".as_slice(),
                b"import_count\":3".as_slice(),
            ),
        ] {
            let mut candidate = FIXED_CATALOG.to_vec();
            let offset = candidate
                .windows(from.len())
                .position(|match_| match_ == from)
                .unwrap();
            candidate.splice(offset..offset + from.len(), to.iter().copied());
            assert!(admit_exact_fictional_import_history(&candidate).is_err());
        }
    }
}
