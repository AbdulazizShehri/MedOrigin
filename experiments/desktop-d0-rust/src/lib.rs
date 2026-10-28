//! Offline-only experimental SHA-256 on four exact, fictional D0 fixture byte sequences.
//!
//! This module accepts ONLY named in-memory, synthetic fixtures. It never opens
//! paths, executes commands, starts servers, reads secrets, or emits telemetry.
//! It is neither a FHIR validator nor a production Tauri command.
//! No public release or Rust parity qualification follows from this source.

use sha2::{Digest, Sha256};

const PATIENT: &[u8] = br#"{"resourceType":"Patient","id":"synthetic","active":true}"#;
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

#[cfg(test)]
mod tests {
    use super::*;

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
