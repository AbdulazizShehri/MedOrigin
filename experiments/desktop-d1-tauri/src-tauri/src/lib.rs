//! Experimental offline, synthetic-only desktop window. Not clinical or releasable.
//! No network, arbitrary files, Python subprocess, telemetry, updater or shell.

use medorigin_desktop_d0_rust_prototype::hash_fixture_raw_v1;
use serde::Serialize;

#[derive(Serialize)]
struct PreviewStatus {
    mode: &'static str,
    data_access: &'static str,
    release_authorized: bool,
    production_parity_qualified: bool,
    outbound_network_enabled: bool,
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

#[tauri::command]
fn preview_status() -> PreviewStatus {
    PreviewStatus {
        mode: "SYNTHETIC_DEVELOPER_PREVIEW",
        data_access: "four_allowlisted_in_memory_fixtures_only",
        release_authorized: false,
        production_parity_qualified: false,
        outbound_network_enabled: false,
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![preview_status, hash_fixture])
        .run(tauri::generate_context!())
        .expect("MedOrigin D1 preview bootstrap failed");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn preview_is_explicitly_nonpublishing_and_local() {
        let status = preview_status();
        assert!(!status.release_authorized);
        assert!(!status.production_parity_qualified);
        assert!(!status.outbound_network_enabled);
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
