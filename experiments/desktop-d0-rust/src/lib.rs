//! Offline-only experimental SHA-256 on eight exact, fictional D0 fixture byte sequences.
//!
//! This module accepts ONLY named in-memory, synthetic fixtures. It never opens
//! paths, executes commands, starts servers, reads secrets, or emits telemetry.
//! It is neither a FHIR validator nor a production Tauri command.
//! No public release or Rust parity qualification follows from this source.

use sha2::{Digest, Sha256};

const PATIENT: &[u8] = br#"{"resourceType":"Patient","id":"synthetic","active":true}"#;
const OBSERVATION: &[u8] = br#"{"resourceType":"Observation","id":"synthetic-observation","status":"final","code":{"coding":[{"system":"urn:synthetic:code","code":"fictional-measurement"}]},"subject":{"reference":"Patient/synthetic"},"valueQuantity":{"value":37,"unit":"fictional"}}"#;
const OBSERVATION_BAD_SUBJECT: &[u8] = br#"{"resourceType":"Observation","id":"synthetic-observation","status":"final","code":{"coding":[{"system":"urn:synthetic:code","code":"fictional-measurement"}]},"subject":{"reference":"Patient/nonexistent"},"valueQuantity":{"value":37,"unit":"fictional"}}"#;
const BUNDLE_LINKED: &[u8] = br#"{"resourceType":"Bundle","type":"collection","entry":[{"fullUrl":"urn:uuid:00000000-0000-4000-8000-000000000001","resource":{"resourceType":"Patient","id":"synthetic","active":true}},{"fullUrl":"urn:uuid:00000000-0000-4000-8000-000000000002","resource":{"resourceType":"Observation","id":"synthetic-observation","status":"final","code":{"coding":[{"system":"urn:synthetic:code","code":"fictional-measurement"}]},"subject":{"reference":"urn:uuid:00000000-0000-4000-8000-000000000001"},"valueQuantity":{"value":37,"unit":"fictional"}}}]}"#;
const BUNDLE_DANGLING: &[u8] = br#"{"resourceType":"Bundle","type":"collection","entry":[{"fullUrl":"urn:uuid:00000000-0000-4000-8000-000000000001","resource":{"resourceType":"Patient","id":"synthetic","active":true}},{"fullUrl":"urn:uuid:00000000-0000-4000-8000-000000000002","resource":{"resourceType":"Observation","id":"synthetic-observation","status":"final","code":{"coding":[{"system":"urn:synthetic:code","code":"fictional-measurement"}]},"subject":{"reference":"urn:uuid:00000000-0000-4000-8000-000000000099"},"valueQuantity":{"value":37,"unit":"fictional"}}}]}"#;
const BUNDLE_PATIENT_URN: &str = "urn:uuid:00000000-0000-4000-8000-000000000001";
const BUNDLE_OBSERVATION_URN: &str = "urn:uuid:00000000-0000-4000-8000-000000000002";
const MAX_PROTOTYPE_INPUT_BYTES: usize = 65_536;
const FHIR_RESOURCE_LIMIT_BYTES: usize = 32_768;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HashError {
    UnknownFixture,
    InvalidLimit,
    InputTooLarge,
}

impl HashError {
    #[must_use]
    pub const fn code(self) -> &'static str {
        match self {
            Self::UnknownFixture => "unknown_fixture",
            Self::InvalidLimit => "invalid_limit",
            Self::InputTooLarge => "input_too_large",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct HashOutcome {
    pub contract: &'static str,
    pub fixture_id: &'static str,
    pub bytes: usize,
    pub sha256_hex: String,
}

/// Return the SHA-256 of exact raw fixture bytes. Never JSON-canonicalize.
///
/// The limit is checked before a fixture is allocated and must itself be
/// bounded. An arbitrary user path or network resource cannot be supplied.
pub fn hash_fixture_raw_v1(
    fixture_id: &str,
    max_input_bytes: usize,
) -> Result<HashOutcome, HashError> {
    if max_input_bytes == 0 || max_input_bytes > MAX_PROTOTYPE_INPUT_BYTES {
        return Err(HashError::InvalidLimit);
    }
    let (identity, required_bytes) = match fixture_id {
        "observation-minimal" => ("observation-minimal", OBSERVATION.len()),
        "observation-bad-subject" => ("observation-bad-subject", OBSERVATION_BAD_SUBJECT.len()),
        "bundle-linked" => ("bundle-linked", BUNDLE_LINKED.len()),
        "bundle-dangling" => ("bundle-dangling", BUNDLE_DANGLING.len()),
        "patient-minimal" => ("patient-minimal", PATIENT.len()),
        "patient-invalid-utf8" => ("patient-invalid-utf8", 1),
        "patient-over-limit" => ("patient-over-limit", FHIR_RESOURCE_LIMIT_BYTES + 1),
        "patient-exact-limit" => ("patient-exact-limit", FHIR_RESOURCE_LIMIT_BYTES),
        _ => return Err(HashError::UnknownFixture),
    };
    if required_bytes > max_input_bytes {
        return Err(HashError::InputTooLarge);
    }

    let bytes = match identity {
        "patient-minimal" => PATIENT.to_vec(),
        "observation-minimal" => OBSERVATION.to_vec(),
        "observation-bad-subject" => OBSERVATION_BAD_SUBJECT.to_vec(),
        "bundle-linked" => BUNDLE_LINKED.to_vec(),
        "bundle-dangling" => BUNDLE_DANGLING.to_vec(),
        "patient-invalid-utf8" => vec![0xff],
        "patient-over-limit" => vec![b' '; required_bytes],
        "patient-exact-limit" => {
            let mut padded = PATIENT.to_vec();
            padded.resize(required_bytes, b' ');
            padded
        }
        _ => unreachable!("already matched an allowlisted in-memory fixture"),
    };
    let digest = Sha256::digest(&bytes);
    let mut hex = String::with_capacity(64);
    for byte in digest {
        use core::fmt::Write as _;
        // Writing into a String cannot fail.
        write!(&mut hex, "{byte:02x}").expect("String write");
    }
    Ok(HashOutcome {
        contract: "medorigin-desktop-d0-raw-sha256-v1",
        fixture_id: identity,
        bytes: bytes.len(),
        sha256_hex: hex,
    })
}

/// A narrow offline envelope check for eight BUILT-IN fictional test fixtures.
///
/// This does not implement FHIR R4 conformance, terminology, profiles,
/// clinical validation, or arbitrary user-file parsing.
/// The only allowed Observation subject is the built-in synthetic Patient.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SyntheticFhirEnvelope {
    pub contract: &'static str,
    pub fixture_id: &'static str,
    pub bytes: usize,
    pub status: &'static str,
    pub synthetic_only: bool,
    pub full_fhir_r4_validated: bool,
    pub release_authorized: bool,
}

pub fn inspect_named_synthetic_fhir_envelope_v1(
    fixture_id: &str,
    max_input_bytes: usize,
) -> Result<SyntheticFhirEnvelope, HashError> {
    if max_input_bytes == 0 || max_input_bytes > MAX_PROTOTYPE_INPUT_BYTES {
        return Err(HashError::InvalidLimit);
    }
    let (name, len) = match fixture_id {
        "observation-minimal" => ("observation-minimal", OBSERVATION.len()),
        "observation-bad-subject" => ("observation-bad-subject", OBSERVATION_BAD_SUBJECT.len()),
        "bundle-linked" => ("bundle-linked", BUNDLE_LINKED.len()),
        "bundle-dangling" => ("bundle-dangling", BUNDLE_DANGLING.len()),
        "patient-minimal" => ("patient-minimal", PATIENT.len()),
        "patient-invalid-utf8" => ("patient-invalid-utf8", 1),
        "patient-exact-limit" => ("patient-exact-limit", FHIR_RESOURCE_LIMIT_BYTES),
        "patient-over-limit" => ("patient-over-limit", FHIR_RESOURCE_LIMIT_BYTES + 1),
        _ => return Err(HashError::UnknownFixture),
    };
    if len > max_input_bytes {
        return Err(HashError::InputTooLarge);
    }
    // Reject oversize before allocating or attempting to parse its bytes.
    let status = if len > FHIR_RESOURCE_LIMIT_BYTES {
        "RESOURCE_TOO_LARGE"
    } else {
        let mut payload: Vec<u8> = match name {
            "patient-minimal" | "patient-exact-limit" => PATIENT.to_vec(),
            "patient-invalid-utf8" => vec![0xff],
            "observation-minimal" => OBSERVATION.to_vec(),
            "observation-bad-subject" => OBSERVATION_BAD_SUBJECT.to_vec(),
            "bundle-linked" => BUNDLE_LINKED.to_vec(),
            "bundle-dangling" => BUNDLE_DANGLING.to_vec(),
            _ => unreachable!("allowlisted fixture"),
        };
        if name == "patient-exact-limit" {
            payload.resize(FHIR_RESOURCE_LIMIT_BYTES, b' ');
        }
        match serde_json::from_slice::<serde_json::Value>(&payload) {
            Ok(value)
                if value.get("resourceType").and_then(|v| v.as_str()) == Some("Patient")
                    && value.get("id").and_then(|v| v.as_str()) == Some("synthetic")
                    && value.get("active").and_then(|v| v.as_bool()) == Some(true) =>
            {
                "FHIR_ENVELOPE_OK"
            }
            Ok(value)
                if value.get("resourceType").and_then(|v| v.as_str()) == Some("Observation") =>
            {
                let complete = value.get("id").and_then(|v| v.as_str())
                    == Some("synthetic-observation")
                    && value.get("status").and_then(|v| v.as_str()) == Some("final")
                    && value
                        .pointer("/code/coding/0/system")
                        .and_then(|v| v.as_str())
                        == Some("urn:synthetic:code")
                    && value
                        .pointer("/code/coding/0/code")
                        .and_then(|v| v.as_str())
                        == Some("fictional-measurement")
                    && value
                        .pointer("/valueQuantity/value")
                        .and_then(|v| v.as_i64())
                        == Some(37)
                    && value
                        .pointer("/valueQuantity/unit")
                        .and_then(|v| v.as_str())
                        == Some("fictional");
                if !complete {
                    "INVALID_FHIR_ENVELOPE"
                } else if value.pointer("/subject/reference").and_then(|v| v.as_str())
                    != Some("Patient/synthetic")
                {
                    "INVALID_REFERENCE"
                } else {
                    "FHIR_ENVELOPE_OK"
                }
            }
            Ok(value) if value.get("resourceType").and_then(|v| v.as_str()) == Some("Bundle") => {
                // Only the two exact built-in entries are inspected. This is NOT
                // general FHIR Bundle resolution or FHIR R4 validation.
                let entries = value.get("entry").and_then(|v| v.as_array());
                let patient = value.pointer("/entry/0/resource");
                let observation = value.pointer("/entry/1/resource");
                let structure_ok = value.get("type").and_then(|v| v.as_str()) == Some("collection")
                    && entries.is_some_and(|items| items.len() == 2)
                    && value.pointer("/entry/0/fullUrl").and_then(|v| v.as_str())
                        == Some(BUNDLE_PATIENT_URN)
                    && value.pointer("/entry/1/fullUrl").and_then(|v| v.as_str())
                        == Some(BUNDLE_OBSERVATION_URN)
                    && patient
                        .and_then(|v| v.get("resourceType"))
                        .and_then(|v| v.as_str())
                        == Some("Patient")
                    && patient.and_then(|v| v.get("id")).and_then(|v| v.as_str())
                        == Some("synthetic")
                    && patient
                        .and_then(|v| v.get("active"))
                        .and_then(|v| v.as_bool())
                        == Some(true)
                    && observation
                        .and_then(|v| v.get("resourceType"))
                        .and_then(|v| v.as_str())
                        == Some("Observation")
                    && observation
                        .and_then(|v| v.get("id"))
                        .and_then(|v| v.as_str())
                        == Some("synthetic-observation")
                    && observation
                        .and_then(|v| v.get("status"))
                        .and_then(|v| v.as_str())
                        == Some("final")
                    && value
                        .pointer("/entry/1/resource/code/coding/0/system")
                        .and_then(|v| v.as_str())
                        == Some("urn:synthetic:code")
                    && value
                        .pointer("/entry/1/resource/code/coding/0/code")
                        .and_then(|v| v.as_str())
                        == Some("fictional-measurement")
                    && value
                        .pointer("/entry/1/resource/valueQuantity/value")
                        .and_then(|v| v.as_i64())
                        == Some(37)
                    && value
                        .pointer("/entry/1/resource/valueQuantity/unit")
                        .and_then(|v| v.as_str())
                        == Some("fictional");
                if !structure_ok {
                    "INVALID_FHIR_ENVELOPE"
                } else if value
                    .pointer("/entry/1/resource/subject/reference")
                    .and_then(|v| v.as_str())
                    != Some(BUNDLE_PATIENT_URN)
                {
                    "INVALID_REFERENCE"
                } else {
                    "FHIR_ENVELOPE_OK"
                }
            }
            Ok(_) => "INVALID_FHIR_ENVELOPE",
            Err(_) if std::str::from_utf8(&payload).is_err() => "INVALID_UTF8",
            Err(_) => "INVALID_JSON",
        }
    };
    Ok(SyntheticFhirEnvelope {
        contract: "medorigin-d0-synthetic-fhir-envelope-v1",
        fixture_id: name,
        bytes: len,
        status,
        synthetic_only: true,
        full_fhir_r4_validated: false,
        release_authorized: false,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn two_fixed_bundle_entries_require_exact_local_patient_reference() {
        for (id, digest, status) in [
            (
                "bundle-linked",
                "390c5ef339b785294d5f20a707b4909d2a316d676d5450a7a76397afb29e5089",
                "FHIR_ENVELOPE_OK",
            ),
            (
                "bundle-dangling",
                "def250325fb64858d2083550cf42b5fc4b680dc94a9d8d0b162801562d2adf02",
                "INVALID_REFERENCE",
            ),
        ] {
            let hashed = hash_fixture_raw_v1(id, 535).expect("allowlisted in-memory Bundle");
            assert_eq!(hashed.bytes, 535);
            assert_eq!(hashed.sha256_hex, digest);
            let inspected = inspect_named_synthetic_fhir_envelope_v1(id, 535).unwrap();
            assert_eq!(inspected.status, status);
            assert!(!inspected.full_fhir_r4_validated);
            assert!(!inspected.release_authorized);
            assert_eq!(
                inspect_named_synthetic_fhir_envelope_v1(id, 534),
                Err(HashError::InputTooLarge)
            );
        }
        assert_eq!(
            inspect_named_synthetic_fhir_envelope_v1("bundle-external", 65_536),
            Err(HashError::UnknownFixture)
        );
    }

    #[test]
    fn all_four_synthetic_golden_raw_byte_vectors_match_python() {
        let golden = [
            (
                "patient-minimal",
                57,
                "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0",
            ),
            (
                "patient-invalid-utf8",
                1,
                "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89",
            ),
            (
                "patient-over-limit",
                32_769,
                "b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538",
            ),
            (
                "patient-exact-limit",
                32_768,
                "ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e",
            ),
        ];
        for (fixture_id, bytes, digest) in golden {
            let actual = hash_fixture_raw_v1(fixture_id, MAX_PROTOTYPE_INPUT_BYTES)
                .expect("known synthetic fixture");
            assert_eq!(actual.contract, "medorigin-desktop-d0-raw-sha256-v1");
            assert_eq!(actual.fixture_id, fixture_id);
            assert_eq!(actual.bytes, bytes);
            assert_eq!(actual.sha256_hex, digest);
        }
    }

    #[test]
    fn unknown_fixture_and_untrusted_paths_never_gain_file_access() {
        for invalid in [
            "",
            "patient-minimal/../secret",
            "../secret",
            "C:\\secret",
            "/etc/passwd",
            "patient-minimal\0",
        ] {
            assert_eq!(
                hash_fixture_raw_v1(invalid, 65_536),
                Err(HashError::UnknownFixture)
            );
        }
        assert_eq!(HashError::UnknownFixture.code(), "unknown_fixture");
    }

    #[test]
    fn bounds_enforced_before_allocation() {
        assert_eq!(
            hash_fixture_raw_v1("patient-minimal", 0),
            Err(HashError::InvalidLimit)
        );
        assert_eq!(
            hash_fixture_raw_v1("patient-minimal", 65_537),
            Err(HashError::InvalidLimit)
        );
        assert_eq!(
            hash_fixture_raw_v1("patient-over-limit", 32_768),
            Err(HashError::InputTooLarge)
        );
        assert_eq!(
            hash_fixture_raw_v1("patient-exact-limit", 32_767),
            Err(HashError::InputTooLarge)
        );
        assert_eq!(
            hash_fixture_raw_v1("patient-minimal", 56),
            Err(HashError::InputTooLarge)
        );
        assert_eq!(
            hash_fixture_raw_v1("patient-minimal", 57)
                .expect("limit inclusive")
                .bytes,
            57
        );
    }

    #[test]
    fn raw_sha256_does_not_canonicalize_or_parse_invalid_json() {
        let invalid = hash_fixture_raw_v1("patient-invalid-utf8", 1).unwrap();
        let padded = hash_fixture_raw_v1("patient-exact-limit", 32_768).unwrap();
        let base = hash_fixture_raw_v1("patient-minimal", 57).unwrap();
        assert_ne!(invalid.sha256_hex, base.sha256_hex);
        assert_ne!(padded.sha256_hex, base.sha256_hex);
    }
}
