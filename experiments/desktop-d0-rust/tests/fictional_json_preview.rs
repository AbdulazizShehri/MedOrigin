use medorigin_desktop_d0_rust_prototype::{
    HashError, fictional_json_preview_v1, hash_fixture_raw_v1,
};

#[test]
fn all_nine_real_fictional_json_vectors_are_raw_and_sha_pinned() {
    for id in [
        "patient-minimal",
        "observation-minimal",
        "observation-bad-subject",
        "bundle-valid",
        "bundle-bad-reference",
        "bundle-duplicate",
        "bundle-wrong-type",
        "bundle-linked",
        "bundle-dangling",
    ] {
        let preview = fictional_json_preview_v1(id).expect("fixed fictional JSON");
        let digest = hash_fixture_raw_v1(id, 65_536).expect("fixed SHA reference");
        assert_eq!(preview.contract, "medorigin-d0-fictional-json-preview-v1");
        assert_eq!(preview.fixture_id, id);
        assert_eq!(preview.bytes, digest.bytes);
        assert_eq!(preview.sha256_hex, digest.sha256_hex);
        assert_eq!(preview.raw_json.len(), digest.bytes);
        assert!(preview.bytes <= 2048);
        assert!(preview.raw_json.contains("resourceType"));
        assert!(preview.synthetic_only);
        assert!(!preview.release_authorized);
    }
    let duplicate = fictional_json_preview_v1("bundle-duplicate").unwrap();
    assert_eq!(duplicate.raw_json.matches("\"fullUrl\"").count(), 2);
    // Preserve wire text and duplicate entry semantics; never JSON-normalize it.
}

#[test]
fn no_preview_for_raw_boundary_cases_or_unapproved_fixture_ids() {
    for id in [
        "patient-invalid-utf8",
        "patient-over-limit",
        "patient-exact-limit",
    ] {
        assert_eq!(
            fictional_json_preview_v1(id),
            Err(HashError::PreviewUnavailable)
        );
    }
    for id in [
        "",
        "../EHR",
        "file:///secret",
        "https://example.org/Patient/7",
        "unknown",
    ] {
        assert_eq!(
            fictional_json_preview_v1(id),
            Err(HashError::UnknownFixture)
        );
    }
}
