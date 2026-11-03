//! MedOrigin Desktop v1 — synthetic developer preview (Slice 1).
//! Not clinical, not releasable, not egress-qualified. No network, arbitrary
//! files, Python subprocess, telemetry, updater or shell. Commands are
//! allowlisted, typed and fail closed.

use serde::Serialize;
use sha2::{Digest, Sha256};

/// Private defensive cap retained for D0 parity; no caller-visible knob.
const MAX_INPUT_BYTES: usize = 65_536;
/// Longest accepted fixture identifier.
const MAX_FIXTURE_ID_BYTES: usize = 64;

const CONTRACT_STATUS: &str = "medorigin-desktop-status-v1";
const CONTRACT_LIST: &str = "medorigin-fixtures-list-v1";
const CONTRACT_VERIFY: &str = "medorigin-fixture-verify-v1";
const CONTRACT_SOURCE: &str = "medorigin-fixture-source-v1";

/// Fixture byte strings are committed under `src-tauri/fixtures/` (LF, see
/// `.gitattributes`) and hashed as raw bytes. Never re-serialized.
const FIXTURES: &[(&str, &str, &[u8])] = &[
    (
        "fixture-patient-alpha",
        "FICTIONAL patient (example person)",
        include_bytes!("../fixtures/fixture-patient-alpha.json"),
    ),
    (
        "fixture-allergy-beta",
        "FICTIONAL allergy intolerance (example substance)",
        include_bytes!("../fixtures/fixture-allergy-beta.json"),
    ),
    (
        "fixture-observation-gamma",
        "FICTIONAL observation (example finding)",
        include_bytes!("../fixtures/fixture-observation-gamma.json"),
    ),
    (
        "fixture-bundle-delta",
        "FICTIONAL bundle, hash-verified only",
        include_bytes!("../fixtures/fixture-bundle-delta.json"),
    ),
];

#[derive(Serialize)]
#[serde(deny_unknown_fields)]
pub struct DesktopStatus {
    pub contract: &'static str,
    pub mode: &'static str,
    pub app_network_plugins_enabled: bool,
    pub webview_egress_qualified: bool,
    pub release_authorized: bool,
    pub production_parity_qualified: bool,
    pub app_version: &'static str,
    pub token_contract: &'static str,
}

#[derive(Serialize)]
pub struct FixtureMeta {
    pub id: &'static str,
    pub label: &'static str,
    pub media_type: &'static str,
    pub byte_len: usize,
    pub sha256_hex: String,
}

#[derive(Serialize)]
#[serde(deny_unknown_fields)]
pub struct FixturesList {
    pub contract: &'static str,
    pub fixtures: Vec<FixtureMeta>,
}

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
pub struct VerifyFixtureRequest {
    pub fixture_id: String,
}

#[derive(Serialize, Debug)]
#[serde(deny_unknown_fields)]
pub struct FixtureVerification {
    pub contract: &'static str,
    pub fixture_id: &'static str,
    pub byte_len: usize,
    pub sha256_hex: String,
    pub synthetic_only: bool,
    pub release_authorized: bool,
}

/// Read-only content of a bundled fictional fixture. Neither arbitrary paths nor
/// caller-provided bytes can enter this API. Parsing is JSON syntax-only:
/// this does NOT establish FHIR semantic validity or clinical suitability.
#[derive(Serialize, Debug)]
#[serde(deny_unknown_fields)]
pub struct FixtureSource {
    pub contract: &'static str,
    pub fixture_id: &'static str,
    pub media_type: &'static str,
    pub byte_len: usize,
    pub sha256_hex: String,
    pub text: &'static str,
    pub synthetic_only: bool,
    pub release_authorized: bool,
}

/// Fixed-code error envelope; the submitted input is never echoed.
#[derive(Serialize, Debug, Clone, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CommandError {
    pub code: String,
}

impl CommandError {
    fn new(code: &str) -> Self {
        CommandError {
            code: code.to_string(),
        }
    }
}

fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

fn fixture_entry(id: &str) -> Option<(&'static str, &'static str, &'static [u8])> {
    FIXTURES.iter().find(|(fid, _, _)| *fid == id).copied()
}

#[tauri::command]
fn get_desktop_status() -> DesktopStatus {
    DesktopStatus {
        contract: CONTRACT_STATUS,
        mode: "SYNTHETIC_DEVELOPER_PREVIEW",
        app_network_plugins_enabled: false,
        webview_egress_qualified: false,
        release_authorized: false,
        production_parity_qualified: false,
        app_version: "0.0.0",
        token_contract: "0.1.0-design-review",
    }
}

#[tauri::command]
fn list_synthetic_fixtures() -> FixturesList {
    let fixtures = FIXTURES
        .iter()
        .map(|(id, label, bytes)| FixtureMeta {
            id,
            label,
            media_type: "application/fhir+json",
            byte_len: bytes.len(),
            sha256_hex: sha256_hex(bytes),
        })
        .collect();
    FixturesList {
        contract: CONTRACT_LIST,
        fixtures,
    }
}

/// Never accepts a filesystem path, bytes, or an expected hash from the WebView.
#[tauri::command]
fn verify_synthetic_fixture(
    req: VerifyFixtureRequest,
) -> Result<FixtureVerification, CommandError> {
    let id = req.fixture_id;
    if id.len() > MAX_FIXTURE_ID_BYTES {
        return Err(CommandError::new("invalid_input"));
    }
    let (fixture_id, _, bytes) =
        fixture_entry(&id).ok_or_else(|| CommandError::new("unknown_fixture"))?;
    if bytes.len() > MAX_INPUT_BYTES {
        return Err(CommandError::new("input_limit_exceeded"));
    }
    Ok(FixtureVerification {
        contract: CONTRACT_VERIFY,
        fixture_id,
        byte_len: bytes.len(),
        sha256_hex: sha256_hex(bytes),
        synthetic_only: true,
        release_authorized: false,
    })
}

/// Return source bytes ONLY for exact, compile-time allowlisted fictional IDs.
/// Never take a path or a caller-side hash. No filesystem, network, sidecar or
/// research-workspace operations are invoked by this command.
#[tauri::command]
fn read_synthetic_fixture_source(req: VerifyFixtureRequest) -> Result<FixtureSource, CommandError> {
    let id = req.fixture_id;
    if id.len() > MAX_FIXTURE_ID_BYTES {
        return Err(CommandError::new("invalid_input"));
    }
    let (fixture_id, _, bytes) =
        fixture_entry(&id).ok_or_else(|| CommandError::new("unknown_fixture"))?;
    if bytes.len() > MAX_INPUT_BYTES {
        return Err(CommandError::new("input_limit_exceeded"));
    }
    let text = std::str::from_utf8(bytes).map_err(|_| CommandError::new("invalid_fixture"))?;
    let document: serde_json::Value =
        serde_json::from_str(text).map_err(|_| CommandError::new("invalid_fixture"))?;
    // A shape sanity check is not a FHIR parser or semantic validation.
    if !document.is_object()
        || document
            .get("resourceType")
            .and_then(serde_json::Value::as_str)
            .is_none()
        || !text.contains("FICTIONAL")
    {
        return Err(CommandError::new("invalid_fixture"));
    }
    Ok(FixtureSource {
        contract: CONTRACT_SOURCE,
        fixture_id,
        media_type: "application/fhir+json",
        byte_len: bytes.len(),
        sha256_hex: sha256_hex(bytes),
        text,
        synthetic_only: true,
        release_authorized: false,
    })
}

/// Deny-all navigation: the webview may only host the bundled app origin.
/// This is webview-level defense in depth only, not OS egress proof.
fn allow_desktop_navigation(url: &tauri::Url) -> bool {
    if !url.username().is_empty() || url.password().is_some() {
        return false;
    }
    matches!(
        (url.scheme(), url.host_str(), url.port()),
        ("http", Some("tauri.localhost"), None)
            | ("tauri", Some("localhost"), None)
            | ("http", Some("localhost"), Some(1420))
    )
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            let config = app
                .config()
                .app
                .windows
                .first()
                .ok_or("MedOrigin v1 window config missing")?;
            tauri::WebviewWindowBuilder::from_config(app.handle(), config)?
                .on_navigation(allow_desktop_navigation)
                .on_new_window(|_, _| tauri::webview::NewWindowResponse::Deny)
                .build()?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            get_desktop_status,
            list_synthetic_fixtures,
            verify_synthetic_fixture,
            read_synthetic_fixture_source
        ])
        .run(tauri::generate_context!())
        .expect("MedOrigin Desktop v1 bootstrap failed");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn status_is_nonpublishing_and_not_egress_qualified() {
        let s = get_desktop_status();
        assert_eq!(s.contract, CONTRACT_STATUS);
        assert_eq!(s.mode, "SYNTHETIC_DEVELOPER_PREVIEW");
        assert!(!s.app_network_plugins_enabled);
        assert!(!s.webview_egress_qualified);
        assert!(!s.release_authorized);
        assert!(!s.production_parity_qualified);
    }

    #[test]
    fn status_serialization_round_trips() {
        let s = get_desktop_status();
        let json = serde_json::to_string(&s).unwrap();
        let back: serde_json::Value = serde_json::from_str(&json).unwrap();
        assert_eq!(back["contract"], CONTRACT_STATUS);
        assert_eq!(back["webview_egress_qualified"], false);
    }

    #[test]
    fn fixture_goldens_pinned() {
        let list = list_synthetic_fixtures();
        assert_eq!(list.contract, CONTRACT_LIST);
        let got: Vec<(&str, usize, &str)> = list
            .fixtures
            .iter()
            .map(|f| (f.id, f.byte_len, f.sha256_hex.as_str()))
            .collect();
        let expected = [
            (
                "fixture-patient-alpha",
                425usize,
                "1761586b0d285d61b44c8ecd7f37fecac1f627b19cb65a7853ced1ba6b9fce3f",
            ),
            (
                "fixture-allergy-beta",
                431,
                "e5719012514e6a858f238da9fcdd46cc61c04828af60c00c31a3887c8f8dddca",
            ),
            (
                "fixture-observation-gamma",
                474,
                "b086dee0c87c59ea853a927eba928f9c06703ca14b4dda75e75f46a91511cfb5",
            ),
            (
                "fixture-bundle-delta",
                533,
                "7971da4c949507fcfb6d3679f7a63ad2840c93206ea4749545b274f6ee49f399",
            ),
        ];
        for (id, len, sha) in expected {
            assert!(
                got.iter()
                    .any(|(gid, glen, gsha)| *gid == id && *glen == len && *gsha == sha),
                "golden mismatch for {id}"
            );
        }
    }

    #[test]
    fn verify_accepts_allowlisted_fixture() {
        let v = verify_synthetic_fixture(VerifyFixtureRequest {
            fixture_id: "fixture-patient-alpha".to_owned(),
        })
        .unwrap();
        assert_eq!(v.contract, CONTRACT_VERIFY);
        assert_eq!(
            v.sha256_hex,
            "1761586b0d285d61b44c8ecd7f37fecac1f627b19cb65a7853ced1ba6b9fce3f"
        );
        assert_eq!(v.byte_len, 425);
        assert!(v.synthetic_only);
        assert!(!v.release_authorized);
    }

    #[test]
    fn verify_rejects_unknown_and_traversal_ids() {
        for id in [
            "unknown",
            "../secrets",
            "fixture-patient-alpha/../../x",
            "FIXTURE-PATIENT-ALPHA",
            "",
        ] {
            let err = verify_synthetic_fixture(VerifyFixtureRequest {
                fixture_id: id.to_owned(),
            })
            .unwrap_err();
            assert_eq!(err.code, "unknown_fixture");
        }
    }

    #[test]
    fn verify_rejects_oversized_id_and_unknown_fields() {
        let err = verify_synthetic_fixture(VerifyFixtureRequest {
            fixture_id: "x".repeat(65),
        })
        .unwrap_err();
        assert_eq!(err.code, "invalid_input");
        let parsed: Result<VerifyFixtureRequest, _> =
            serde_json::from_str(r#"{"fixture_id":"fixture-patient-alpha","path":"/etc/passwd"}"#);
        assert!(parsed.is_err(), "unknown fields must be rejected");
    }

    #[test]
    fn error_envelope_never_echoes_submitted_input() {
        let nasty = "C:\\Users\\secret\\patient.json";
        let err = verify_synthetic_fixture(VerifyFixtureRequest {
            fixture_id: nasty.to_owned(),
        })
        .unwrap_err();
        let json = serde_json::to_string(&err).unwrap();
        assert!(!json.contains("secret"));
        assert!(matches!(
            err.code.as_str(),
            "unknown_fixture"
                | "invalid_input"
                | "invalid_limit"
                | "input_limit_exceeded"
                | "internal"
        ));
    }

    #[test]
    fn source_view_returns_only_pinned_fictional_json() {
        for fixture in list_synthetic_fixtures().fixtures {
            let source = read_synthetic_fixture_source(VerifyFixtureRequest {
                fixture_id: fixture.id.to_owned(),
            })
            .unwrap();
            assert_eq!(source.contract, CONTRACT_SOURCE);
            assert_eq!(source.fixture_id, fixture.id);
            assert_eq!(source.media_type, "application/fhir+json");
            assert_eq!(source.sha256_hex, fixture.sha256_hex);
            assert_eq!(source.byte_len, fixture.byte_len);
            assert_eq!(sha256_hex(source.text.as_bytes()), fixture.sha256_hex);
            assert_eq!(source.text.len(), fixture.byte_len);
            assert!(source.text.contains("FICTIONAL"));
            assert!(source.synthetic_only);
            assert!(!source.release_authorized);
            let parsed: serde_json::Value = serde_json::from_str(source.text).unwrap();
            assert!(parsed.get("resourceType").is_some());
        }
    }

    #[test]
    fn source_view_refuses_unknown_traversal_and_oversized_input() {
        for id in [
            "../secret",
            "fixture-unknown",
            "",
            "fixture-patient-alpha/../other",
        ] {
            let err = read_synthetic_fixture_source(VerifyFixtureRequest {
                fixture_id: id.to_owned(),
            })
            .unwrap_err();
            assert_eq!(err.code, "unknown_fixture");
            if !id.is_empty() {
                assert!(!serde_json::to_string(&err).unwrap().contains(id));
            }
        }
        let err = read_synthetic_fixture_source(VerifyFixtureRequest {
            fixture_id: "x".repeat(65),
        })
        .unwrap_err();
        assert_eq!(err.code, "invalid_input");
        let forged: Result<VerifyFixtureRequest, _> = serde_json::from_str(
            r#"{"fixture_id":"fixture-patient-alpha","path":"C:/users/private"}"#,
        );
        assert!(forged.is_err());
    }

    #[test]
    fn navigation_denies_remote_and_allows_local_app_origin() {
        for raw in [
            "https://example.org/",
            "https://tauri.localhost/",
            "http://tauri.localhost:1337/",
            "http://evil@tauri.localhost/",
            "http://localhost:1421/",
            "file:///C:/sensitive.txt",
            "data:text/html,external",
            "javascript:alert(1)",
        ] {
            let url = tauri::Url::parse(raw).unwrap();
            assert!(!allow_desktop_navigation(&url), "must deny {raw}");
        }
        for raw in ["http://tauri.localhost/", "tauri://localhost/"] {
            let url = tauri::Url::parse(raw).unwrap();
            assert!(allow_desktop_navigation(&url), "must allow {raw}");
        }
    }
}
