//! Experimental offline, synthetic-only desktop window. Not clinical or releasable.
//! No network, arbitrary files, Python subprocess, telemetry, updater or shell.

use medorigin_desktop_d0_rust_prototype::{
    hash_fixture_raw_v1, inspect_named_synthetic_fhir_envelope_v1,
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

/// Only ten built-in fictional test fixtures are accepted. No arbitrary
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
        data_access: "ten_allowlisted_in_memory_fixtures_only",
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
            inspect_fhir_fixture_envelope
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
}
