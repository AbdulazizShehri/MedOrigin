//! Experimental offline, synthetic-only desktop window. Not clinical or releasable.
//! No network, arbitrary files, Python subprocess, telemetry, updater or shell.

use medorigin_desktop_d0_rust_prototype::{
    hash_fictional_batch_rows_v1, hash_fixture_raw_v1, inspect_named_synthetic_fhir_envelope_v1,
};
use serde::Serialize;

#[derive(Serialize)]
struct PreviewStatus {
    mode: &'static str,
    data_access: &'static str,
    release_authorized: bool,
    production_parity_qualified: bool,
    app_network_plugins_enabled: bool,
    webview_runtime_egress_qualified: bool,
}

#[derive(Debug, Serialize)]
struct FixtureHashResponse {
    contract: &'static str,
    fixture_id: &'static str,
    bytes: usize,
    sha256_hex: String,
    synthetic_only: bool,
    release_authorized: bool,
}

#[derive(Debug, Serialize)]
struct FhirEnvelopeResponse {
    contract: &'static str,
    fixture_id: &'static str,
    bytes: usize,
    status: &'static str,
    synthetic_only: bool,
    full_fhir_r4_validated: bool,
    release_authorized: bool,
}

/// Only twelve built-in fictional test fixtures are accepted. No arbitrary
/// JSON, filesystem access, references, terminology lookup or PHI.
#[tauri::command]
fn inspect_fhir_fixture_envelope(
    fixture_id: String,
    max_input_bytes: usize,
) -> Result<FhirEnvelopeResponse, String> {
    let checked = inspect_named_synthetic_fhir_envelope_v1(&fixture_id, max_input_bytes)
        .map_err(|err| err.code().to_string())?;
    Ok(FhirEnvelopeResponse {
        contract: checked.contract,
        fixture_id: checked.fixture_id,
        bytes: checked.bytes,
        status: checked.status,
        synthetic_only: checked.synthetic_only,
        full_fhir_r4_validated: false,
        release_authorized: false,
    })
}

#[tauri::command]
fn preview_status() -> PreviewStatus {
    PreviewStatus {
        mode: "SYNTHETIC_DEVELOPER_PREVIEW",
        data_access: "twelve_allowlisted_in_memory_fixtures_only",
        release_authorized: false,
        production_parity_qualified: false,
        app_network_plugins_enabled: false,
        webview_runtime_egress_qualified: false,
    }
}

/// Never accepts a filesystem path or bytes from the WebView.
#[tauri::command]
fn hash_fixture(fixture_id: String, max_input_bytes: usize) -> Result<FixtureHashResponse, String> {
    let hashed =
        hash_fixture_raw_v1(&fixture_id, max_input_bytes).map_err(|err| err.code().to_string())?;
    Ok(FixtureHashResponse {
        contract: hashed.contract,
        fixture_id: hashed.fixture_id,
        bytes: hashed.bytes,
        sha256_hex: hashed.sha256_hex,
        synthetic_only: true,
        release_authorized: false,
    })
}

// One Rust IPC call owns the complete, fixed fictional batch. It cannot accept
// WebView-supplied fixture names, arbitrary JSON, paths, or network destinations.
#[derive(Debug, Serialize)]
struct NativeBatchRow {
    fixture_id: &'static str,
    bytes: usize,
    sha256_hex: String,
    status: &'static str,
}

#[derive(Debug, Serialize)]
struct NativeBatchResponse {
    contract: &'static str,
    rows: Vec<NativeBatchRow>,
    batch_sha256_hex: String,
    synthetic_only: bool,
    full_fhir_r4_validated: bool,
    release_authorized: bool,
    webview_runtime_egress_qualified: bool,
}

const NATIVE_BATCH_GOLDENS: [(&str, usize, &str, &str); 12] = [
    (
        "patient-minimal",
        57,
        "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0",
        "FHIR_ENVELOPE_OK",
    ),
    (
        "patient-invalid-utf8",
        1,
        "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89",
        "INVALID_UTF8",
    ),
    (
        "patient-over-limit",
        32769,
        "b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538",
        "RESOURCE_TOO_LARGE",
    ),
    (
        "patient-exact-limit",
        32768,
        "ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e",
        "FHIR_ENVELOPE_OK",
    ),
    (
        "observation-minimal",
        251,
        "527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19",
        "FHIR_ENVELOPE_OK",
    ),
    (
        "observation-bad-subject",
        253,
        "d2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838",
        "INVALID_REFERENCE",
    ),
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
];

#[tauri::command]
fn verify_all_fixtures(max_input_bytes: usize) -> Result<NativeBatchResponse, String> {
    if max_input_bytes == 0 || max_input_bytes > 65_536 {
        return Err("invalid_limit".to_string());
    }
    let mut rows = Vec::with_capacity(NATIVE_BATCH_GOLDENS.len());
    for (id, expected_bytes, expected_sha, expected_status) in NATIVE_BATCH_GOLDENS {
        let hash =
            hash_fixture_raw_v1(id, max_input_bytes).map_err(|err| err.code().to_string())?;
        if hash.bytes != expected_bytes || hash.sha256_hex != expected_sha {
            return Err("batch_integrity_mismatch".to_string());
        }
        let inspected = inspect_named_synthetic_fhir_envelope_v1(id, max_input_bytes)
            .map_err(|err| err.code().to_string())?;
        if inspected.bytes != expected_bytes
            || inspected.status != expected_status
            || !inspected.synthetic_only
            || inspected.full_fhir_r4_validated
            || inspected.release_authorized
        {
            return Err("batch_integrity_mismatch".to_string());
        }
        rows.push(NativeBatchRow {
            fixture_id: id,
            bytes: hash.bytes,
            sha256_hex: hash.sha256_hex,
            status: inspected.status,
        });
    }
    // The stable SHA-256 fingerprints the complete ordered synthetic row
    // metadata. It is not an authentication signature or release attestation.
    let batch_sha256_hex = hash_fictional_batch_rows_v1(
        &rows
            .iter()
            .map(|row| {
                (
                    row.fixture_id,
                    row.bytes,
                    row.sha256_hex.as_str(),
                    row.status,
                )
            })
            .collect::<Vec<_>>(),
    );
    // No intermediate rows escape Rust if any one check fails.
    Ok(NativeBatchResponse {
        contract: "medorigin-d1-native-fictional-batch-v1",
        rows,
        batch_sha256_hex,
        synthetic_only: true,
        full_fhir_r4_validated: false,
        release_authorized: false,
        webview_runtime_egress_qualified: false,
    })
}

/// Reject app-host navigation to remote destinations, embedded credentials and
/// unexpected ports. This is webview-level defense in depth only, not OS egress proof.
fn allow_preview_navigation(url: &tauri::Url) -> bool {
    if !url.username().is_empty() || url.password().is_some() {
        return false;
    }
    match (url.scheme(), url.host_str(), url.port()) {
        ("http", Some("tauri.localhost"), None) => true,
        ("tauri", Some("localhost"), None) => true,
        ("http", Some("localhost"), Some(1420)) if cfg!(debug_assertions) => true,
        _ => false,
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Windows D1 preview only: reject direct non-AppContainer launches
    // before creating Tauri or WebView2. An AppContainer token does not
    // independently establish that MXC or network-denial policy was used.
    #[cfg(windows)]
    if let Err(reason) =
        medorigin_d1_windows_token_gate::require_windows_appcontainer_primary_token()
    {
        eprintln!("D1_WINDOWS_APPCONTAINER_REQUIRED_NO_GO: {reason}");
        std::process::exit(76);
    }
    tauri::Builder::default()
        // Do not auto-create the default WebView before hooks are registered.
        // Deny all popups. Neither callback covers WebView2 broker background
        // traffic: Windows packet-level OS verification remains mandatory.
        .setup(|app| {
            let config = app
                .config()
                .app
                .windows
                .first()
                .ok_or("D1 window config missing")?;
            tauri::WebviewWindowBuilder::from_config(app.handle(), config)?
                .on_navigation(allow_preview_navigation)
                .on_new_window(|_, _| tauri::webview::NewWindowResponse::Deny)
                .build()?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            preview_status,
            hash_fixture,
            inspect_fhir_fixture_envelope,
            verify_all_fixtures
        ])
        .run(tauri::generate_context!())
        .expect("MedOrigin D1 preview bootstrap failed");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn synthetic_envelope_command_reports_explicit_nonclinical_outcomes() {
        for (id, expected) in [
            ("patient-minimal", "FHIR_ENVELOPE_OK"),
            ("patient-exact-limit", "FHIR_ENVELOPE_OK"),
            ("patient-invalid-utf8", "INVALID_UTF8"),
            ("patient-over-limit", "RESOURCE_TOO_LARGE"),
            ("observation-minimal", "FHIR_ENVELOPE_OK"),
            ("observation-bad-subject", "INVALID_REFERENCE"),
            ("bundle-valid", "BUNDLE_GRAPH_OK"),
            ("bundle-bad-reference", "INVALID_REFERENCE"),
            ("bundle-duplicate", "DUPLICATE_ENTRY"),
            ("bundle-wrong-type", "INVALID_BUNDLE_TYPE"),
            ("bundle-linked", "BUNDLE_GRAPH_OK"),
            ("bundle-dangling", "INVALID_REFERENCE"),
        ] {
            let observed = inspect_fhir_fixture_envelope(id.to_owned(), 65_536).unwrap();
            assert_eq!(observed.status, expected);
            assert_eq!(observed.fixture_id, id);
            assert!(observed.synthetic_only);
            assert!(!observed.full_fhir_r4_validated);
            assert!(!observed.release_authorized);
        }
        assert_eq!(
            inspect_fhir_fixture_envelope("../secret".to_owned(), 65_536).unwrap_err(),
            "unknown_fixture"
        );
    }

    #[test]
    fn preview_navigation_allows_only_local_app_origin() {
        for raw in ["http://tauri.localhost/", "tauri://localhost/"] {
            let url = tauri::Url::parse(raw).unwrap();
            assert!(
                allow_preview_navigation(&url),
                "should allow local app: {raw}"
            );
        }
        let dev_url = tauri::Url::parse("http://localhost:1420/").unwrap();
        assert_eq!(allow_preview_navigation(&dev_url), cfg!(debug_assertions));
    }

    #[test]
    fn preview_navigation_denies_remote_credentials_and_unexpected_schemes() {
        for raw in [
            "https://example.org/",
            "http://example.org/",
            "https://tauri.localhost/",
            "http://tauri.localhost.evil.example/",
            "http://evil@tauri.localhost/",
            "http://tauri.localhost:1337/",
            "http://localhost:1421/",
            "http://127.0.0.1:1420/",
            "file:///C:/sensitive.txt",
            "data:text/html,external",
            "javascript:alert(1)",
        ] {
            let url = tauri::Url::parse(raw).unwrap();
            assert!(!allow_preview_navigation(&url), "must deny navigation");
        }
    }

    #[test]
    fn preview_is_nonpublishing_and_disclaims_runtime_network_isolation() {
        let status = preview_status();
        assert!(!status.release_authorized);
        assert!(!status.production_parity_qualified);
        assert!(!status.app_network_plugins_enabled);
        assert!(!status.webview_runtime_egress_qualified);
        assert_eq!(status.mode, "SYNTHETIC_DEVELOPER_PREVIEW");
    }

    #[test]
    fn command_returns_python_golden_hash_and_no_physical_file_access() {
        let output = hash_fixture("patient-minimal".to_owned(), 57).unwrap();
        assert_eq!(
            output.sha256_hex,
            "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0"
        );
        assert!(output.synthetic_only);
        assert!(!output.release_authorized);
        assert_eq!(
            hash_fixture("../secrets".to_owned(), 65_536).unwrap_err(),
            "unknown_fixture"
        );
        assert_eq!(
            hash_fixture("patient-minimal".to_owned(), 0).unwrap_err(),
            "invalid_limit"
        );
    }

    #[test]
    fn native_batch_verifies_all_twelve_without_partial_or_clinical_claims() {
        let result = verify_all_fixtures(65_536).expect("fixed fictional batch");
        assert_eq!(result.contract, "medorigin-d1-native-fictional-batch-v1");
        assert_eq!(result.rows.len(), 12);
        assert_eq!(
            result.batch_sha256_hex,
            "af062a37ed639a6df5c769bb0e9cb2e0e792b3f68760853ff8ea8e97e2ab5088"
        );
        assert_eq!(result.rows[0].fixture_id, "patient-minimal");
        assert_eq!(result.rows[11].fixture_id, "bundle-dangling");
        assert!(result.synthetic_only);
        assert!(!result.release_authorized);
        assert!(!result.full_fhir_r4_validated);
        assert!(!result.webview_runtime_egress_qualified);
        assert!(result.rows.iter().all(|row| row.sha256_hex.len() == 64));
        assert_eq!(verify_all_fixtures(0).unwrap_err(), "invalid_limit");
        assert_eq!(verify_all_fixtures(65_537).unwrap_err(), "invalid_limit");
    }
}
