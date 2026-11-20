//! Synthetic-only *real encrypted Core readback projection* to native D2.
//! Never accepts arbitrary patient records: only exact, compiled, reviewed
//! source bytes emitted by the explicit Core+Workspace temporary demo.
//! Matching bytes are NOT a proof of authenticated sender or freshness.
use serde_json::Value;
use sha2::{Digest, Sha256};

const SOURCE: &[u8] = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
const SOURCE_SHA256: &str = "c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49";
const SOURCE_PERSISTENT: &[u8] =
    include_bytes!("../fixtures/core/encrypted-persistent-readback-projection.json");
const SOURCE_PERSISTENT_SHA256: &str =
    "3673eb77b2dbef25fd6cb33d9c345d2f37d38a86bcf1652ed9defae4da139243";
pub const ENCRYPTED_READBACK_MAX_BYTES: usize = 2048;

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FictionalReadbackLink {
    pub field: String,
    pub target: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FictionalReadbackResource {
    pub resource_type: String,
    pub resource_id: String,
    pub full_url: String,
    pub links: Vec<FictionalReadbackLink>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct FictionalEncryptedReadback {
    pub report_sha256: String,
    pub source_content_sha256: String,
    pub resources: Vec<FictionalReadbackResource>,
    pub audit_chain_verified: bool,
    pub encrypted_reopen_verified: bool,
    pub ephemeral_store_removed: bool,
    pub persistent_test_vault_reopened: bool,
    pub disclosure: &'static str,
}

pub fn admit_exact_encrypted_readback_projection(
    raw: &[u8],
) -> Result<FictionalEncryptedReadback, &'static str> {
    if raw.is_empty() || raw.len() > ENCRYPTED_READBACK_MAX_BYTES {
        return Err("fictional_encrypted_readback_size_refused");
    }
    let is_persistent = if raw == SOURCE {
        false
    } else if raw == SOURCE_PERSISTENT {
        true
    } else {
        return Err("fictional_encrypted_readback_unreviewed_bytes");
    };
    let digest = Sha256::digest(raw)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>();
    if digest
        != if is_persistent {
            SOURCE_PERSISTENT_SHA256
        } else {
            SOURCE_SHA256
        }
    {
        return Err("fictional_encrypted_readback_sha_refused");
    }
    let source: Value =
        serde_json::from_slice(raw).map_err(|_| "fictional_encrypted_readback_json_refused")?;
    let flag_true = |key| source.get(key).and_then(Value::as_bool) == Some(true);
    let flag_false = |key| source.get(key).and_then(Value::as_bool) == Some(false);
    let expected_schema = if is_persistent {
        "medorigin-d2-persistent-fhir-memory-readback-projection/v1"
    } else {
        "medorigin-d2-encrypted-fhir-memory-readback-projection/v1"
    };
    let expected_status = if is_persistent {
        "SYNTHETIC_PERSISTENT_ENCRYPTED_READBACK_VERIFIED"
    } else {
        "SYNTHETIC_ENCRYPTED_READBACK_VERIFIED"
    };
    if source.get("schema").and_then(Value::as_str) != Some(expected_schema)
        || source.get("status").and_then(Value::as_str) != Some(expected_status)
        || source.get("resource_count").and_then(Value::as_u64) != Some(3)
        || !flag_true("audit_chain_verified")
        || !flag_true("encrypted_reopen_verified")
        || if is_persistent {
            !flag_true("persistent_test_vault_reopened") || !flag_false("ephemeral_store_removed")
        } else {
            !flag_true("ephemeral_store_removed")
                || source.get("persistent_test_vault_reopened").is_some()
        }
        || !flag_false("payload_included")
        || !flag_false("clinical_use_authorized")
        || !flag_false("production_key_provider_used")
        || !flag_false("full_fhir_r4_conformance_established")
        || !flag_false("transport_sender_authenticated")
        || !flag_false("release_authorized")
    {
        return Err("fictional_encrypted_readback_false_safety_claim");
    }
    let source_sha = source
        .get("source_content_sha256")
        .and_then(Value::as_str)
        .ok_or("fictional_encrypted_readback_source_sha_missing")?;
    if source_sha.len() != 64 || !source_sha.bytes().all(|c| c.is_ascii_hexdigit()) {
        return Err("fictional_encrypted_readback_source_sha_invalid");
    }
    let entries = source
        .get("resources")
        .and_then(Value::as_array)
        .ok_or("fictional_encrypted_readback_list_missing")?;
    if entries.len() != 3 {
        return Err("fictional_encrypted_readback_count_refused");
    }
    // The three IDs come ONLY from the recovered *decrypted* Core Bundle
    // projection, after exact compiled byte equality and bounded admission.
    let mut resources = Vec::with_capacity(3);
    for entry in entries {
        let property = |key| {
            entry
                .get(key)
                .and_then(Value::as_str)
                .map(str::to_owned)
                .ok_or("fictional_encrypted_readback_field_missing")
        };
        let links = entry
            .get("links")
            .and_then(Value::as_array)
            .ok_or("fictional_encrypted_readback_links_missing")?
            .iter()
            .map(|link| {
                Ok(FictionalReadbackLink {
                    field: link
                        .get("field")
                        .and_then(Value::as_str)
                        .ok_or("fictional_encrypted_readback_link_field")?
                        .to_owned(),
                    target: link
                        .get("target")
                        .and_then(Value::as_str)
                        .ok_or("fictional_encrypted_readback_link_target")?
                        .to_owned(),
                })
            })
            .collect::<Result<Vec<_>, &'static str>>()?;
        if links.len() > 2 {
            return Err("fictional_encrypted_readback_excess_links");
        }
        resources.push(FictionalReadbackResource {
            resource_type: property("resource_type")?,
            resource_id: property("id")?,
            full_url: property("full_url")?,
            links,
        });
    }
    if resources[0].resource_type != "Observation"
        || resources[1].resource_type != "Patient"
        || resources[2].resource_type != "Encounter"
        || resources[0].links.len() != 2
        || !resources[1].links.is_empty()
        || resources[2].links.len() != 1
    {
        return Err("fictional_encrypted_readback_resource_shape_refused");
    }
    Ok(FictionalEncryptedReadback {
        report_sha256: digest,
        source_content_sha256: source_sha.to_owned(),
        resources,
        audit_chain_verified: true,
        encrypted_reopen_verified: true,
        ephemeral_store_removed: !is_persistent,
        persistent_test_vault_reopened: is_persistent,
        disclosure: if is_persistent {
            "Real persistent fictional Core readback from Windows user-DPAPI-wrapped test-only root key. Sender/freshness NOT authenticated. NOT production key custody, clinical FHIR validation or patient use."
        } else {
            "Encrypted Core readback from fictional in-memory test key only. Sender/freshness NOT authenticated. NOT production key custody, clinical FHIR validation or patient use."
        },
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn actual_source_compiled_encrypted_readback_has_three_recovered_resources() {
        let recovered = admit_exact_encrypted_readback_projection(SOURCE).unwrap();
        assert_eq!(recovered.report_sha256, SOURCE_SHA256);
        assert_eq!(recovered.resources.len(), 3);
        assert_eq!(
            recovered.resources[0].resource_id,
            "fictional-observation-001"
        );
        assert_eq!(recovered.resources[1].resource_id, "fictional-patient-001");
        assert_eq!(
            recovered.resources[2].resource_id,
            "fictional-encounter-001"
        );
        assert_eq!(recovered.resources[0].links[0].field, "subject");
        assert_eq!(
            recovered.resources[0].links[0].target,
            recovered.resources[1].full_url
        );
        assert_eq!(
            recovered.resources[0].links[1].target,
            recovered.resources[2].full_url
        );
        assert!(recovered.disclosure.contains("NOT authenticated"));
    }

    #[test]
    fn real_cold_reopened_fixed_fictional_workspace_is_separate_pinned_schema() {
        let recovered = admit_exact_encrypted_readback_projection(SOURCE_PERSISTENT).unwrap();
        assert_eq!(recovered.report_sha256, SOURCE_PERSISTENT_SHA256);
        assert_eq!(recovered.resources.len(), 3);
        assert_eq!(recovered.resources[0].resource_type, "Observation");
        assert_eq!(recovered.resources[1].resource_id, "fictional-patient-001");
        assert_eq!(recovered.resources[2].resource_type, "Encounter");
        assert_eq!(recovered.resources[0].links.len(), 2);
        assert!(recovered.encrypted_reopen_verified);
        assert!(recovered.audit_chain_verified);
        assert!(!recovered.ephemeral_store_removed);
        assert!(recovered.persistent_test_vault_reopened);
        assert!(recovered.disclosure.contains("NOT production key custody"));

        for (old, new) in [
            (
                "persistent_test_vault_reopened\":true",
                "persistent_test_vault_reopened\":false",
            ),
            (
                "ephemeral_store_removed\":false",
                "ephemeral_store_removed\":true",
            ),
            (
                "production_key_provider_used\":false",
                "production_key_provider_used\":true",
            ),
            (
                "clinical_use_authorized\":false",
                "clinical_use_authorized\":true",
            ),
        ] {
            let str_source = std::str::from_utf8(SOURCE_PERSISTENT).unwrap();
            assert!(str_source.contains(old));
            let altered = str_source.replacen(old, new, 1);
            assert!(admit_exact_encrypted_readback_projection(altered.as_bytes()).is_err());
        }
        assert!(
            admit_exact_encrypted_readback_projection(&[SOURCE_PERSISTENT, b" "].concat()).is_err()
        );
    }

    #[test]
    fn arbitrary_patient_like_json_or_forged_release_claim_refused() {
        for bad in [
            Vec::new(),
            b"{}".to_vec(),
            [SOURCE, b" "].concat(),
            [SOURCE, b"\n"].concat(),
            SOURCE[..SOURCE.len() - 1].to_vec(),
            vec![b'A'; ENCRYPTED_READBACK_MAX_BYTES + 1],
        ] {
            assert!(admit_exact_encrypted_readback_projection(&bad).is_err());
        }
        for (old, new) in [
            (
                b"clinical_use_authorized\":false".as_slice(),
                b"clinical_use_authorized\":true ".as_slice(),
            ),
            (
                b"release_authorized\":false".as_slice(),
                b"release_authorized\":true ".as_slice(),
            ),
            (
                b"transport_sender_authenticated\":false".as_slice(),
                b"transport_sender_authenticated\":true ".as_slice(),
            ),
            (
                b"payload_included\":false".as_slice(),
                b"payload_included\":true ".as_slice(),
            ),
        ] {
            let mut changed = SOURCE.to_vec();
            let offset = SOURCE
                .windows(old.len())
                .position(|span| span == old)
                .unwrap();
            changed.splice(offset..offset + old.len(), new.iter().copied());
            assert!(admit_exact_encrypted_readback_projection(&changed).is_err());
        }
    }
}
