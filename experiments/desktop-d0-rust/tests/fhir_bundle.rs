use medorigin_desktop_d0_rust_prototype::{
    HashError, hash_fixture_raw_v1, inspect_named_synthetic_fhir_envelope_v1,
};

#[test]
fn fictional_bundle_reference_graph_is_consistent_and_fail_closed() {
    for (name, size, sha, status) in [
        (
            "bundle-valid",
            531,
            "3a530a66c0f2b71908b1282985432e405f0f2f412c7ccc0143aa1972d9447983",
            "BUNDLE_GRAPH_OK",
        ),
        (
            "bundle-bad-reference",
            528,
            "4aabcfa54309c83052d62b4fdcf1c6635a6cd3d937551e2ab947899345f9f082",
            "INVALID_REFERENCE",
        ),
        (
            "bundle-duplicate",
            531,
            "813f8a3b8fee59ba74abdb293c6cac5cca103b390153730e6e3bc4656540f15b",
            "DUPLICATE_ENTRY",
        ),
        (
            "bundle-wrong-type",
            532,
            "293c10c8abf055e8c1f84bae4913c7246bf9be5bf53dee0fb3c918e32a8346a7",
            "INVALID_BUNDLE_TYPE",
        ),
        (
            "bundle-linked",
            559,
            "1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88",
            "BUNDLE_GRAPH_OK",
        ),
        (
            "bundle-dangling",
            559,
            "1bbc0bac94b3ff19dce3502164f3243748cf5aa7e869433bdb09e7ec2266b229",
            "INVALID_REFERENCE",
        ),
    ] {
        let hashed = hash_fixture_raw_v1(name, 65_536).unwrap();
        assert_eq!(hashed.bytes, size);
        assert_eq!(hashed.sha256_hex, sha);
        let inspected = inspect_named_synthetic_fhir_envelope_v1(name, 65_536).unwrap();
        assert_eq!(inspected.status, status);
        assert_eq!(inspected.bytes, size);
        assert!(inspected.synthetic_only);
        assert!(!inspected.full_fhir_r4_validated);
        assert!(!inspected.release_authorized);
    }
}

#[test]
fn fictional_bundle_only_compiled_ids_and_bounded_inputs() {
    assert_eq!(
        inspect_named_synthetic_fhir_envelope_v1("bundle-valid", 530),
        Err(HashError::InputTooLarge)
    );
    for forbidden in [
        "../bundle-valid",
        "bundle-valid.json",
        "http://example.org",
        "bundle-real-record",
    ] {
        assert_eq!(
            hash_fixture_raw_v1(forbidden, 65_536),
            Err(HashError::UnknownFixture)
        );
    }
}
