use medorigin_desktop_d0_rust_prototype::{
    hash_fixture_raw_v1, inspect_named_synthetic_fhir_envelope_v1,
};

#[test]
fn synthetic_observation_with_local_patient_reference_passes_bounded_envelope() {
    let hashed = hash_fixture_raw_v1("observation-minimal", 65_536).unwrap();
    assert_eq!(hashed.bytes, 251);
    assert_eq!(
        hashed.sha256_hex,
        "527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19"
    );
    let inspected =
        inspect_named_synthetic_fhir_envelope_v1("observation-minimal", 65_536).unwrap();
    assert_eq!(inspected.status, "FHIR_ENVELOPE_OK");
    assert_eq!(inspected.bytes, 251);
    assert!(!inspected.full_fhir_r4_validated);
    assert!(!inspected.release_authorized);
}

#[test]
fn synthetic_observation_with_broken_subject_reference_is_refused() {
    let hashed = hash_fixture_raw_v1("observation-bad-subject", 65_536).unwrap();
    assert_eq!(hashed.bytes, 253);
    assert_eq!(
        hashed.sha256_hex,
        "d2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838"
    );
    let inspected =
        inspect_named_synthetic_fhir_envelope_v1("observation-bad-subject", 65_536).unwrap();
    assert_eq!(inspected.status, "INVALID_REFERENCE");
    assert!(!inspected.full_fhir_r4_validated);
}

#[test]
fn observation_is_not_arbitrary_user_data_or_a_path() {
    assert!(hash_fixture_raw_v1("observation/../../secret", 65_536).is_err());
    assert!(inspect_named_synthetic_fhir_envelope_v1("observation-minimal", 250).is_err());
}
