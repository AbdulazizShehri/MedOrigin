//! Source-shaped, bounded, redacted Core fictional encrypted file-batch receipt.
//! Exact Core PR #963 schema v1 (2026-11-05), NOT patient records.
//! The stdin sender is untrusted. Claims about Core execution, encryption,
//! authenticated user, key custody or source freshness are NOT attested here.
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::BTreeSet;

pub const FILE_BATCH_RECEIPT_MAX_BYTES: usize = 4096;
const TOP_FIELDS: &[&str] = &[
    "schema",
    "status",
    "import_count",
    "resource_count",
    "verified_timeline_event_count",
    "verified_audit_events",
    "current_audit_head_digest",
    "imports",
    "physically_closed_and_reopened",
    "source_filenames_included",
    "patient_identity_included",
    "resource_payload_included",
    "permanent_workspace_created",
    "production_key_provider_used",
    "cross_import_patient_identity_join_performed",
    "network_access_performed",
    "fhir_r4_conformance_validated",
    "clinical_use_authorized",
    "release_authorized",
    "ephemeral_store_removed",
];
const IMPORT_FIELDS: &[&str] = &[
    "import_ordinal",
    "source_content_sha256",
    "import_audit_event_digest",
    "resource_count",
    "verified_timeline_event_count",
    "patient_count_within_import",
];

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FictionalCoreFileImport {
    pub ordinal: usize,
    pub source_sha256: String,
    pub audit_sha256: String,
    pub resource_count: usize,
    pub timeline_event_count: usize,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FictionalCoreFileBatch {
    pub receipt_sha256: String,
    pub audit_head_sha256: String,
    pub resource_count: usize,
    pub timeline_event_count: usize,
    pub imports: Vec<FictionalCoreFileImport>,
}

fn keys_match(value: &Value, fields: &[&str]) -> bool {
    value.as_object().is_some_and(|obj| {
        obj.len() == fields.len() && obj.keys().all(|key| fields.contains(&key.as_str()))
    })
}
fn lowercase_sha(value: &Value) -> Option<&str> {
    let s = value.as_str()?;
    (s.len() == 64
        && s.bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b)))
    .then_some(s)
}
fn count(value: &Value, min: u64, max: u64) -> Option<usize> {
    let v = value.as_u64()?;
    (min..=max).contains(&v).then_some(v as usize)
}

/// Accept *only* a source-shaped, canonical, LF-terminated nonclinical summary
/// from the Core file-batch encrypted demo. Never a FHIR Bundle, patient field,
/// path, arbitrary note or reimportable persisted patient record.
pub fn admit_fictional_core_file_batch(raw: &[u8]) -> Result<FictionalCoreFileBatch, &'static str> {
    if raw.is_empty() || raw.len() > FILE_BATCH_RECEIPT_MAX_BYTES {
        return Err("fictional_file_batch_receipt_size_refused");
    }
    let source: Value =
        serde_json::from_slice(raw).map_err(|_| "fictional_file_batch_receipt_json_refused")?;
    if !keys_match(&source, TOP_FIELDS) {
        return Err("fictional_file_batch_receipt_extra_or_missing_fields");
    }
    // serde_json canonical rendering gives sorted unique keys. Raw equality
    // rejects duplicate keys, whitespace, concatenated JSON and LF changes.
    let mut canonical = serde_json::to_vec(&source)
        .map_err(|_| "fictional_file_batch_receipt_canonical_refused")?;
    canonical.push(b'\n');
    if raw != canonical {
        return Err("fictional_file_batch_receipt_noncanonical");
    }
    if source["schema"] != "medorigin-core-fictional-file-encrypted-batch-reopen/v1"
        || source["status"] != "FICTIONAL_FILE_BATCH_ENCRYPTED_REOPEN_VERIFIED"
        || source["physically_closed_and_reopened"] != true
        || source["ephemeral_store_removed"] != true
        || [
            "source_filenames_included",
            "patient_identity_included",
            "resource_payload_included",
            "permanent_workspace_created",
            "production_key_provider_used",
            "cross_import_patient_identity_join_performed",
            "network_access_performed",
            "fhir_r4_conformance_validated",
            "clinical_use_authorized",
            "release_authorized",
        ]
        .iter()
        .any(|field| source[*field] != false)
    {
        return Err("fictional_file_batch_receipt_false_safety_claim");
    }
    let imports = source["imports"]
        .as_array()
        .ok_or("fictional_file_batch_receipt_imports_missing")?;
    let import_count = count(&source["import_count"], 2, 4)
        .ok_or("fictional_file_batch_receipt_import_count_refused")?;
    let total = count(&source["resource_count"], 2, 64)
        .ok_or("fictional_file_batch_receipt_total_refused")?;
    let events = count(&source["verified_timeline_event_count"], 0, 64)
        .ok_or("fictional_file_batch_receipt_timeline_total_refused")?;
    if imports.len() != import_count
        || count(&source["verified_audit_events"], 2, 4) != Some(import_count)
    {
        return Err("fictional_file_batch_receipt_audit_count_refused");
    }
    let final_head = lowercase_sha(&source["current_audit_head_digest"])
        .ok_or("fictional_file_batch_receipt_head_refused")?;
    let mut seen_sources = BTreeSet::new();
    let mut seen_audits = BTreeSet::new();
    let mut recovered = Vec::with_capacity(import_count);
    let mut counted_resources = 0usize;
    let mut counted_events = 0usize;
    for (index, entry) in imports.iter().enumerate() {
        if !keys_match(entry, IMPORT_FIELDS)
            || count(&entry["import_ordinal"], 1, 4) != Some(index + 1)
            || count(&entry["patient_count_within_import"], 1, 1) != Some(1)
        {
            return Err("fictional_file_batch_receipt_import_shape_refused");
        }
        let sha = lowercase_sha(&entry["source_content_sha256"])
            .ok_or("fictional_file_batch_receipt_source_sha_refused")?;
        let audit = lowercase_sha(&entry["import_audit_event_digest"])
            .ok_or("fictional_file_batch_receipt_audit_sha_refused")?;
        let resource_count = count(&entry["resource_count"], 1, 16)
            .ok_or("fictional_file_batch_receipt_import_size_refused")?;
        let timeline_event_count = count(&entry["verified_timeline_event_count"], 0, 16)
            .ok_or("fictional_file_batch_receipt_import_events_refused")?;
        if timeline_event_count > resource_count
            || !seen_sources.insert(sha)
            || !seen_audits.insert(audit)
        {
            return Err("fictional_file_batch_receipt_import_identity_refused");
        }
        counted_resources += resource_count;
        counted_events += timeline_event_count;
        recovered.push(FictionalCoreFileImport {
            ordinal: index + 1,
            source_sha256: sha.to_owned(),
            audit_sha256: audit.to_owned(),
            resource_count,
            timeline_event_count,
        });
    }
    if counted_resources != total
        || counted_events != events
        || recovered
            .last()
            .is_none_or(|item| item.audit_sha256 != final_head)
    {
        return Err("fictional_file_batch_receipt_aggregate_or_head_refused");
    }
    let receipt_sha256 = Sha256::digest(raw)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect();
    Ok(FictionalCoreFileBatch {
        receipt_sha256,
        audit_head_sha256: final_head.to_owned(),
        resource_count: total,
        timeline_event_count: events,
        imports: recovered,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn sample(n: usize) -> Value {
        let imports: Vec<Value> = (1..=n)
            .map(|i| {
                json!({
                    "import_ordinal": i,
                    "source_content_sha256": format!("{i:064x}"),
                    "import_audit_event_digest": format!("{:064x}", i + 256),
                    "resource_count": 3,
                    "verified_timeline_event_count": 2,
                    "patient_count_within_import": 1
                })
            })
            .collect();
        json!({
            "schema": "medorigin-core-fictional-file-encrypted-batch-reopen/v1",
            "status": "FICTIONAL_FILE_BATCH_ENCRYPTED_REOPEN_VERIFIED",
            "import_count": n,
            "resource_count": 3*n,
            "verified_timeline_event_count": 2*n,
            "verified_audit_events": n,
            "current_audit_head_digest": format!("{:064x}", n+256),
            "imports": imports,
            "physically_closed_and_reopened": true,
            "source_filenames_included": false,
            "patient_identity_included": false,
            "resource_payload_included": false,
            "permanent_workspace_created": false,
            "production_key_provider_used": false,
            "cross_import_patient_identity_join_performed": false,
            "network_access_performed": false,
            "fhir_r4_conformance_validated": false,
            "clinical_use_authorized": false,
            "release_authorized": false,
            "ephemeral_store_removed": true
        })
    }
    fn bytes(value: &Value) -> Vec<u8> {
        let mut b = serde_json::to_vec(value).unwrap();
        b.push(b'\n');
        b
    }
    #[test]
    fn actual_core963_windows_encrypted_cold_reopen_receipt_is_admitted_redacted_only() {
        let raw = include_bytes!(
            "../fixtures/core/core963-real-encrypted-fictional-file-batch-redacted.json"
        );
        assert_eq!(raw.len(), 1341);
        let receipt = admit_fictional_core_file_batch(raw).unwrap();
        assert_eq!(
            receipt.receipt_sha256,
            "34beba4dd887ab5e26fb8ceaf91d06f85a6ebaca349359aa0f9ecccb612d2292"
        );
        assert_eq!(receipt.imports.len(), 2);
        assert_eq!(receipt.resource_count, 6);
        assert_eq!(receipt.timeline_event_count, 4);
        assert_eq!(receipt.imports[0].resource_count, 3);
        assert_eq!(receipt.imports[1].resource_count, 3);
        let content = std::str::from_utf8(raw).unwrap();
        for sensitive in [
            "urn:uuid:",
            "fictional-patient",
            "invented-file-",
            "patient_name",
            "name",
            "resource_payload",
        ] {
            if sensitive == "resource_payload" || sensitive == "name" {
                // These occur only in explicit negative flag names.
                continue;
            }
            assert!(!content.contains(sensitive));
        }
        let mut wrong = raw.to_vec();
        wrong.extend(b" ");
        assert!(admit_fictional_core_file_batch(&wrong).is_err());
    }

    #[test]
    fn accepts_only_two_to_four_redacted_source_scoped_imports() {
        for n in 2..=4 {
            let b = bytes(&sample(n));
            let result = admit_fictional_core_file_batch(&b).unwrap();
            assert_eq!(result.imports.len(), n);
            assert_eq!(result.resource_count, 3 * n);
            assert_eq!(result.timeline_event_count, 2 * n);
            assert_eq!(result.audit_head_sha256, format!("{:064x}", n + 256));
            assert_eq!(result.receipt_sha256.len(), 64);
        }
        for n in [0, 1, 5] {
            assert!(admit_fictional_core_file_batch(&bytes(&sample(n))).is_err());
        }
    }
    #[test]
    fn denies_noncanonical_duplicate_keys_extra_patient_fields_and_forged_flags() {
        let good = bytes(&sample(2));
        assert!(admit_fictional_core_file_batch(&good).is_ok());
        assert!(admit_fictional_core_file_batch(&good[..good.len() - 1]).is_err());
        assert!(
            admit_fictional_core_file_batch(&[b" ".as_slice(), good.as_slice()].concat()).is_err()
        );
        let mut inject = good.clone();
        *inject.last_mut().unwrap() = b' ';
        assert!(admit_fictional_core_file_batch(&inject).is_err());
        let mut v = sample(2);
        v["patient_name"] = json!("NOT_ALLOWED");
        assert!(admit_fictional_core_file_batch(&bytes(&v)).is_err());
        let mut v = sample(2);
        v["imports"][0]["patient_id"] = json!("fictional-but-still-unallowed");
        assert!(admit_fictional_core_file_batch(&bytes(&v)).is_err());
        for key in [
            "clinical_use_authorized",
            "fhir_r4_conformance_validated",
            "network_access_performed",
            "patient_identity_included",
            "cross_import_patient_identity_join_performed",
        ] {
            let mut v = sample(2);
            v[key] = json!(true);
            assert!(
                admit_fictional_core_file_batch(&bytes(&v)).is_err(),
                "{key}"
            );
        }
        let mut duplicate = String::from_utf8(good).unwrap();
        duplicate = duplicate.replacen(
            "\"import_count\":2",
            "\"import_count\":2,\"import_count\":2",
            1,
        );
        assert!(admit_fictional_core_file_batch(duplicate.as_bytes()).is_err());
    }
    #[test]
    fn refuses_corrupt_provenance_counts_cross_import_mixups_and_oversize() {
        for field in [
            "resource_count",
            "verified_timeline_event_count",
            "verified_audit_events",
            "import_count",
        ] {
            let mut v = sample(3);
            v[field] = json!(64);
            assert!(
                admit_fictional_core_file_batch(&bytes(&v)).is_err(),
                "{field}"
            );
        }
        for field in ["source_content_sha256", "import_audit_event_digest"] {
            let mut v = sample(2);
            v["imports"][1][field] = v["imports"][0][field].clone();
            assert!(
                admit_fictional_core_file_batch(&bytes(&v)).is_err(),
                "{field}"
            );
        }
        let mut v = sample(3);
        v["current_audit_head_digest"] = json!(format!("{:064x}", 999));
        assert!(admit_fictional_core_file_batch(&bytes(&v)).is_err());
        let mut v = sample(3);
        v["imports"][0]["patient_count_within_import"] = json!(2);
        assert!(admit_fictional_core_file_batch(&bytes(&v)).is_err());
        let mut v = sample(3);
        v["imports"][0]["source_content_sha256"] = json!("A".repeat(64));
        assert!(admit_fictional_core_file_batch(&bytes(&v)).is_err());
        assert!(admit_fictional_core_file_batch(&vec![b'0'; 4097]).is_err());
    }
}
