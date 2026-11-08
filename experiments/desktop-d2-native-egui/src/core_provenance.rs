//! D2 in-memory admission for two source-reviewed, fictional Core FHIR reports.
//!
//! Deliberately **not** a launcher, file importer, validator or clinical bridge.
//! This pure function accepts only canonical Core provenance-only JSON from
//! two fixed synthetic Core QA inputs. No actual patient data can be admitted.
use serde_json::Value;
use sha2::{Digest, Sha256};

const MAX_REPORT_BYTES: usize = 2048;
const FORMAT: &str = "fhirkit-validation-report/v1";
const WARNING: &str = "FHIR R4 schema, terminology, and profile validation were not performed; this local report records deterministic provenance only.";
const TIMESTAMP: &str = "2026-10-24T00:00:00Z";
const VALIDATOR: &str = "medscale-fhirkit-local";
const VERSION: &str = "0.1.0";

/// Pin source-reviewed Core fixture hashes; no free-form user-supplied hashes.
const KNOWN_STRUCTURE_DEFINITION_HASH: &str =
    "d1f1167a352bbce42e851336d33d0e292902463c1656860bd7cce3ec67598faf";
const UNKNOWN_FICTIONAL_NEGATIVE_HASH: &str =
    "493bdfef2855ab2bb997d56ee7e4afca4b5ae0c4cc75eef39461b00517ef177c";

/// Intentional positive/negative *synthetic* input classification, not validity.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FictionalCoreInput {
    KnownStructureDefinition,
    UnknownResourceNegativeControl,
}

/// Non-sensitive receipt only: never retain the untrusted raw report or payload.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CoreProvenanceReceipt {
    pub case: FictionalCoreInput,
    pub report_sha256: String,
    pub status: &'static str,
    pub disclosure: &'static str,
}

/// Admission is source-contract-only; it never asserts FHIR R4 compliance.
pub fn admit_fixed_fictional_core_report(
    raw: &[u8],
) -> Result<CoreProvenanceReceipt, &'static str> {
    if raw.is_empty() || raw.len() > MAX_REPORT_BYTES {
        return Err("core_report_size_refused");
    }
    let parsed: Value = serde_json::from_slice(raw).map_err(|_| "core_report_unreadable_json")?;
    let obj = parsed.as_object().ok_or("core_report_not_object")?;

    // The installed Core report_to_json uses canonical, sorted, compact JSON
    // with a SINGLE trailing newline. Requiring exact representation also
    // refuses duplicate object keys silently collapsed by a generic JSON map,
    // alternate escapes, unapproved whitespace and trailing JSON documents.
    let expected = serde_json::to_string(&parsed).map_err(|_| "core_report_not_canonical")?;
    if raw != format!("{expected}\n").as_bytes() {
        return Err("core_report_not_canonical");
    }

    const KEYS: [&str; 9] = [
        "created_at",
        "errors",
        "format_version",
        "input_hash",
        "report_id",
        "status",
        "validator_name",
        "validator_version",
        "warnings",
    ];
    if obj.len() != KEYS.len() || !KEYS.iter().all(|key| obj.contains_key(*key)) {
        return Err("core_report_fields_refused");
    }
    let text = |key: &str| obj.get(key).and_then(Value::as_str);
    if text("report_id") != Some("")
        || text("created_at") != Some(TIMESTAMP)
        || text("format_version") != Some(FORMAT)
        || text("validator_name") != Some(VALIDATOR)
        || text("validator_version") != Some(VERSION)
        || text("status") != Some("not_validated")
    {
        return Err("core_report_validation_claim_or_version_refused");
    }
    let warnings = obj.get("warnings").and_then(Value::as_array);
    if warnings.is_none_or(|entries| entries.len() != 1 || entries[0].as_str() != Some(WARNING))
        || obj
            .get("errors")
            .and_then(Value::as_array)
            .is_none_or(|entries| !entries.is_empty())
    {
        return Err("core_report_warning_or_errors_refused");
    }
    let case = match text("input_hash") {
        Some(KNOWN_STRUCTURE_DEFINITION_HASH) => FictionalCoreInput::KnownStructureDefinition,
        Some(UNKNOWN_FICTIONAL_NEGATIVE_HASH) => FictionalCoreInput::UnknownResourceNegativeControl,
        _ => return Err("core_report_input_not_allowlisted"),
    };

    Ok(CoreProvenanceReceipt {
        case,
        report_sha256: Sha256::digest(raw)
            .iter()
            .map(|byte| format!("{byte:02x}"))
            .collect(),
        status: "not_validated",
        disclosure: "Synthetic Core provenance only. FHIR R4 NOT validated. Not for patient data.",
    })
}

/// Stable labels for two Source-PINNED reports actually emitted by Python Core
/// at the reviewed synthetic QA commit. Not a live Python or clinical bridge.
pub const PINNED_CORE_CASE_LABELS: [&str; 2] = [
    "Known fictional StructureDefinition — provenance only",
    "Unknown fictional resource — negative control",
];

const CORE_KNOWN_REPORT: &[u8] = include_bytes!("../fixtures/core/known-structure-definition.json");
const CORE_NEGATIVE_REPORT: &[u8] =
    include_bytes!("../fixtures/core/unknown-fictional-negative.json");

const CORE_KNOWN_REPORT_HASH: &str =
    "165b41acdc416617e8f207366d454ac6a713ecf4c9a5efd740d14a0af882bd08";
const CORE_NEGATIVE_REPORT_HASH: &str =
    "7962d747049185ce33f252d8760e1197942e6f945d22e9f640df27eaeff1129c";

/// Inspect the exact two compiled, source-backed synthetic Core reports.
/// Refuses source mutations at runtime; no file opens, processes, network
/// access, patient data or inference. Only a bounded non-sensitive receipt
/// reaches the native UI.
pub fn inspect_pinned_core_report(index: usize) -> Result<CoreProvenanceReceipt, &'static str> {
    let (raw, digest, expected_case) = match index {
        0 => (
            CORE_KNOWN_REPORT,
            CORE_KNOWN_REPORT_HASH,
            FictionalCoreInput::KnownStructureDefinition,
        ),
        1 => (
            CORE_NEGATIVE_REPORT,
            CORE_NEGATIVE_REPORT_HASH,
            FictionalCoreInput::UnknownResourceNegativeControl,
        ),
        _ => return Err("core_report_unknown_source_refused"),
    };
    let receipt = admit_fixed_fictional_core_report(raw)?;
    if receipt.report_sha256 != digest || receipt.case != expected_case {
        return Err("core_report_compiled_source_changed");
    }
    Ok(receipt)
}

/// Admit ONE external synthetic Core report only if it is byte-identical
/// to a source-compiled, known Core report. This never proves transport
/// authenticity or freshness; it is an allowlist, NOT a digital signature.
pub fn admit_exact_source_reviewed_external_core_report(
    raw: &[u8],
) -> Result<CoreProvenanceReceipt, &'static str> {
    let receipt = admit_fixed_fictional_core_report(raw)?;
    let expected = match receipt.case {
        FictionalCoreInput::KnownStructureDefinition => inspect_pinned_core_report(0)?,
        FictionalCoreInput::UnknownResourceNegativeControl => inspect_pinned_core_report(1)?,
    };
    if receipt != expected {
        return Err("external_core_report_not_exact_source_bound");
    }
    Ok(receipt)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::{Value, json};

    #[test]
    fn two_real_core_source_embedded_reports_have_exact_pinned_hashes_and_disclosure() {
        for (index, expected, actual_bytes, pinned_hash) in [
            (
                0usize,
                FictionalCoreInput::KnownStructureDefinition,
                CORE_KNOWN_REPORT,
                CORE_KNOWN_REPORT_HASH,
            ),
            (
                1usize,
                FictionalCoreInput::UnknownResourceNegativeControl,
                CORE_NEGATIVE_REPORT,
                CORE_NEGATIVE_REPORT_HASH,
            ),
        ] {
            let receipt =
                inspect_pinned_core_report(index).expect("exact source-reviewed Core QA report");
            assert_eq!(receipt.case, expected);
            assert_eq!(receipt.status, "not_validated");
            assert_eq!(receipt.report_sha256, pinned_hash);
            assert!(receipt.disclosure.contains("FHIR R4 NOT validated"));
            assert!(actual_bytes.len() <= MAX_REPORT_BYTES);
            assert_eq!(
                Sha256::digest(actual_bytes)
                    .iter()
                    .map(|byte| format!("{byte:02x}"))
                    .collect::<String>(),
                pinned_hash
            );
        }
    }

    #[test]
    fn embedded_source_refuses_modified_claim_or_unknown_selection() {
        for index in [2, usize::MAX] {
            assert_eq!(
                inspect_pinned_core_report(index),
                Err("core_report_unknown_source_refused")
            );
        }
        let mut changed = CORE_KNOWN_REPORT.to_vec();
        let value = std::str::from_utf8(&changed).expect("known source-only fixture");
        let position = value.find("not_validated").expect("expected status marker");
        changed[position] = b'x';
        assert!(admit_fixed_fictional_core_report(&changed).is_err());

        let mut forged = CORE_NEGATIVE_REPORT.to_vec();
        forged.push(b' ');
        assert!(admit_fixed_fictional_core_report(&forged).is_err());
        let wrong_id = String::from_utf8(CORE_KNOWN_REPORT.to_vec())
            .expect("known source-only fixture")
            .replace(
                KNOWN_STRUCTURE_DEFINITION_HASH,
                "ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            );
        assert!(admit_fixed_fictional_core_report(wrong_id.as_bytes()).is_err());
    }

    fn packet(hash: &str) -> Value {
        json!({
            "created_at": TIMESTAMP,
            "errors": [],
            "format_version": FORMAT,
            "input_hash": hash,
            "report_id": "",
            "status": "not_validated",
            "validator_name": VALIDATOR,
            "validator_version": VERSION,
            "warnings": [WARNING]
        })
    }

    fn canonical(value: &Value) -> Vec<u8> {
        format!("{}\n", serde_json::to_string(value).expect("test JSON")).into_bytes()
    }

    #[test]
    fn two_exact_source_reviewed_synthetic_core_receipts_are_admitted_as_not_validated() {
        for (hash, expected) in [
            (
                KNOWN_STRUCTURE_DEFINITION_HASH,
                FictionalCoreInput::KnownStructureDefinition,
            ),
            (
                UNKNOWN_FICTIONAL_NEGATIVE_HASH,
                FictionalCoreInput::UnknownResourceNegativeControl,
            ),
        ] {
            let raw = canonical(&packet(hash));
            let receipt =
                admit_fixed_fictional_core_report(&raw).expect("fixed synthetic contract");
            assert_eq!(receipt.case, expected);
            assert_eq!(receipt.status, "not_validated");
            assert!(receipt.disclosure.contains("NOT validated"));
            assert_eq!(
                receipt.report_sha256,
                Sha256::digest(&raw)
                    .iter()
                    .map(|byte| format!("{byte:02x}"))
                    .collect::<String>()
            );
        }
    }

    #[test]
    fn false_validation_claims_and_missing_disclosure_are_refused() {
        for (field, replacement) in [
            ("status", json!("valid")),
            ("status", json!("invalid")),
            ("warnings", json!([])),
            ("warnings", json!(["Clinical FHIR validated"])),
            ("errors", json!(["PHI leaked"])),
            ("validator_name", json!("external-claim")),
            ("validator_version", json!("0.2.0")),
            ("created_at", json!("2026-11-04T00:00:00Z")),
            ("format_version", json!("v2")),
            ("report_id", json!("user-report")),
        ] {
            let mut sample = packet(KNOWN_STRUCTURE_DEFINITION_HASH);
            sample[field] = replacement;
            assert!(
                admit_fixed_fictional_core_report(&canonical(&sample)).is_err(),
                "{field}"
            );
        }
    }

    #[test]
    fn arbitrary_input_or_payload_is_refused_even_when_formatted_correctly() {
        for hash in ["", "0", "c".repeat(64).as_str()] {
            assert!(admit_fixed_fictional_core_report(&canonical(&packet(hash))).is_err());
        }
        let mut sample = packet(KNOWN_STRUCTURE_DEFINITION_HASH);
        sample["patient"] = json!({"name": "not permitted"});
        assert_eq!(
            admit_fixed_fictional_core_report(&canonical(&sample)),
            Err("core_report_fields_refused")
        );
        sample = packet(KNOWN_STRUCTURE_DEFINITION_HASH);
        sample["input_hash"] = json!(null);
        assert!(admit_fixed_fictional_core_report(&canonical(&sample)).is_err());
    }

    #[test]
    fn ambiguous_or_noncanonical_json_is_refused_before_receipt_creation() {
        let good = canonical(&packet(KNOWN_STRUCTURE_DEFINITION_HASH));
        let mut cases = vec![
            vec![],
            vec![b'a'; MAX_REPORT_BYTES + 1],
            b"null\n".to_vec(),
            b"{\"status\":\"valid\",\"status\":\"not_validated\"}\n".to_vec(),
            good[..good.len() - 1].to_vec(),
            [good.as_slice(), b"\n"].concat(),
            [b" ", good.as_slice()].concat(),
            [good.as_slice(), b"{}"].concat(),
        ];
        let malformed_unicode = vec![0xff, 0x00];
        cases.push(malformed_unicode);
        for raw in cases {
            assert!(admit_fixed_fictional_core_report(&raw).is_err());
        }
    }

    #[test]
    fn nested_duplicate_keys_are_refused_by_canonical_byte_equality() {
        let good = String::from_utf8(canonical(&packet(KNOWN_STRUCTURE_DEFINITION_HASH))).unwrap();
        let altered = good.replace("\"errors\":[]", "\"errors\":[],\"errors\":[]");
        assert_ne!(good, altered);
        assert_eq!(
            admit_fixed_fictional_core_report(altered.as_bytes()),
            Err("core_report_not_canonical")
        );
    }

    #[test]
    fn no_raw_report_bytes_are_retained_in_approved_receipt() {
        let raw = canonical(&packet(KNOWN_STRUCTURE_DEFINITION_HASH));
        let receipt = admit_fixed_fictional_core_report(&raw).unwrap();
        assert!(!format!("{receipt:?}").contains(KNOWN_STRUCTURE_DEFINITION_HASH));
        assert!(!format!("{receipt:?}").contains("FHIR R4 schema, terminology"));
    }
}
