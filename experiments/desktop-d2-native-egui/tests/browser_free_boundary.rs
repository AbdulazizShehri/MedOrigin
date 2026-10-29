//! Conservative, source-only D2 regression contract: no embedded browser,
//! HTTP client/server or explicit socket/process-launch APIs.
//! This is NOT a runtime packet-capture proof or a transitive code audit.
use std::fs;
use std::path::Path;

const FORBIDDEN_PACKAGES: &[&str] = &[
    "tauri",
    "wry",
    "webview2",
    "webview2-com",
    "webview2-com-sys",
    "reqwest",
    "ureq",
    "hyper",
    "hyper-util",
    "tungstenite",
    "async-tungstenite",
    "websocket",
    "axum",
    "actix-web",
    "warp",
    "quinn",
    "curl",
    "isahc",
    "aws-sdk-",
];
const FORBIDDEN_SOURCE_APIS: &[&str] = &[
    "std::net::",
    "tokio::net::",
    "TcpStream::",
    "UdpSocket::",
    "reqwest::",
    "ureq::",
    "hyper::",
    "tauri::",
    "wry::",
    "webview2::",
    "webbrowser::",
    "std::process::Command",
    "Command::new(",
];

fn disallowed_package(name: &str) -> bool {
    FORBIDDEN_PACKAGES
        .iter()
        .any(|blocked| name == *blocked || (blocked.ends_with('-') && name.starts_with(blocked)))
}

fn lockfile_package_names(lockfile: &str) -> Vec<&str> {
    let mut names = Vec::new();
    let mut in_package = false;
    for line in lockfile.lines() {
        match line.trim() {
            "[[package]]" => in_package = true,
            line if line.starts_with('[') => in_package = false,
            line if in_package && line.starts_with("name = \"") => {
                if let Some(name) = line
                    .strip_prefix("name = \"")
                    .and_then(|rest| rest.strip_suffix('"'))
                {
                    names.push(name);
                }
            }
            _ => {}
        }
    }
    names
}

fn disallowed_source_api(source: &str) -> Option<&'static str> {
    FORBIDDEN_SOURCE_APIS
        .iter()
        .copied()
        .find(|pattern| source.contains(pattern))
}

#[test]
fn runtime_lock_has_no_known_browser_or_network_stack() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let lock = fs::read_to_string(root.join("Cargo.lock")).expect("committed Cargo.lock");
    let packages = lockfile_package_names(&lock);
    assert!(
        packages.len() > 30,
        "unexpectedly empty or malformed Cargo.lock"
    );
    for package in packages {
        assert!(
            !disallowed_package(package),
            "D2 forbidden resolved dependency: {package}"
        );
    }
    // Some platform deps (including web-sys and tokio) can appear in the
    // lockfile without being outbound networking or a browser engine.
}

#[test]
fn authored_native_source_has_no_network_or_browser_entrypoints() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("src");
    let mut count = 0;
    for entry in fs::read_dir(root).expect("native D2 source directory") {
        let path = entry.expect("source entry").path();
        if path.extension().is_some_and(|ext| ext == "rs") {
            count += 1;
            let source = fs::read_to_string(&path).expect("UTF-8 native source");
            assert!(
                disallowed_source_api(&source).is_none(),
                "D2 source {} acquired forbidden networking/browser/process entrypoint",
                path.display(),
            );
        }
    }
    assert_eq!(
        count, 3,
        "review new native source layout before extending D2"
    );
}

#[test]
fn direct_dependencies_remain_limited_to_native_ui_and_existing_d0() {
    let manifest = fs::read_to_string(Path::new(env!("CARGO_MANIFEST_DIR")).join("Cargo.toml"))
        .expect("D2 Cargo manifest");
    let dependencies = manifest
        .split_once("\n[dependencies]\n")
        .and_then(|(_, rest)| rest.split_once("\n["))
        .map(|(section, _)| section)
        .expect("one ordinary dependencies section");
    let declared: Vec<_> = dependencies
        .lines()
        .filter(|line| !line.trim().is_empty() && !line.trim().starts_with('#'))
        .map(|line| {
            line.split_once('=')
                .map(|(name, _)| name.trim())
                .expect("dependency assignment")
        })
        .collect();
    assert_eq!(
        declared,
        ["eframe", "medorigin-desktop-d0-rust-prototype"],
        "D2 dependency additions require a separate safety review"
    );
    assert!(
        dependencies.contains("default-features = false")
            && dependencies.contains("\"accesskit\"")
            && dependencies.contains("\"glow\""),
        "D2 must preserve explicit native-only eframe features and AccessKit"
    );
}

#[test]
fn guard_refuses_synthetic_dependency_and_source_mutations() {
    for package in [
        "tauri",
        "webview2-com",
        "reqwest",
        "hyper-util",
        "aws-sdk-s3",
    ] {
        assert!(
            disallowed_package(package),
            "missed forbidden package {package}"
        );
    }
    for source in [
        "let stream = std::net::TcpStream::connect(endpoint)?;",
        "webbrowser::open(url)?;",
        "std::process::Command::new(\"curl\")",
    ] {
        assert!(
            disallowed_source_api(source).is_some(),
            "missed forbidden source API"
        );
    }
    assert_eq!(
        lockfile_package_names("[[package]]\nname = \"reqwest\"\nversion = \"0.1\"\n"),
        vec!["reqwest"]
    );
}
