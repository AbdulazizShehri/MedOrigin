use medorigin_desktop_d0_rust_prototype::{HashError, inspect_named_synthetic_fhir_envelope_v1};

#[test]
fn local_fhir_envelope_is_an_explicitly_limited_structural_check() {
    let valid = inspect_named_synthetic_fhir_envelope_v1("patient-minimal", 65_536).unwrap();
    assert_eq!(valid.contract, "medorigin-d0-synthetic-fhir-envelope-v1");
    assert_eq!(valid.fixture_id, "patient-minimal");
    assert_eq!(valid.status, "FHIR_ENVELOPE_OK");
    assert_eq!(valid.bytes, 57);
    assert!(valid.synthetic_only);
    assert!(!valid.full_fhir_r4_validated);
    assert!(!valid.release_authorized);

    let edge = inspect_named_synthetic_fhir_envelope_v1("patient-exact-limit", 65_536).unwrap();
    assert_eq!(edge.status, "FHIR_ENVELOPE_OK");
    assert_eq!(edge.bytes, 32_768);

    let invalid = inspect_named_synthetic_fhir_envelope_v1("patient-invalid-utf8", 65_536).unwrap();
    assert_eq!(invalid.status, "INVALID_UTF8");

    let oversized = inspect_named_synthetic_fhir_envelope_v1("patient-over-limit", 65_536).unwrap();
    assert_eq!(oversized.status, "RESOURCE_TOO_LARGE");
    assert_eq!(oversized.bytes, 32_769);
}

#[test]
fn forged_fixture_ids_or_invalid_limits_are_not_accepted() {
    for name in [
        "",
        "../secret",
        "patient-minimal/../private",
        "file:///secret",
        "patient-MINIMAL",
    ] {
        assert_eq!(
            inspect_named_synthetic_fhir_envelope_v1(name, 65_536),
            Err(HashError::UnknownFixture)
        );
    }
    for limit in [0, 65_537, usize::MAX] {
        assert_eq!(
            inspect_named_synthetic_fhir_envelope_v1("patient-minimal", limit),
            Err(HashError::InvalidLimit)
        );
    }
    assert_eq!(
        inspect_named_synthetic_fhir_envelope_v1("patient-minimal", 56),
        Err(HashError::InputTooLarge)
    );
}
