//! Conservative, source-only D2 regression contract: no embedded browser,
//! HTTP client/server or explicit socket/process-launch APIs.
//! This is NOT a runtime packet-capture proof or a transitive code audit.
use std::fs;
use std::path::{Path, PathBuf};

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
    // Whitespace cannot turn an unsafe import into a safe one. This is a
    // conservative tripwire, not a Rust parser or a complete code audit.
    let compact: String = source.chars().filter(|c| !c.is_whitespace()).collect();
    const INDIRECT_APIS: &[&str] = &[
        "std::net",
        "std::{net",
        "std::process",
        "std::{process",
        "include!(",
        "#[path=",
        "path=",
        "extern\"C\"",
    ];
    FORBIDDEN_SOURCE_APIS
        .iter()
        .copied()
        .chain(INDIRECT_APIS.iter().copied())
        .find(|pattern| compact.contains(pattern))
}

// Freeze the entire authored source layout, not just the number of .rs files.
// An uninspected nested module, symlink or non-Rust file is a review boundary.
fn audited_native_source_files(root: &Path) -> Vec<PathBuf> {
    let mut names = Vec::new();
    for entry in fs::read_dir(root).expect("native D2 source directory") {
        let entry = entry.expect("native source entry");
        let kind = entry.file_type().expect("native source file type");
        assert!(
            kind.is_file() && !kind.is_symlink(),
            "unexpected native D2 source directory, symlink or special entry"
        );
        let name = entry
            .file_name()
            .into_string()
            .expect("UTF-8 native source filename");
        assert!(name.ends_with(".rs"), "unexpected non-Rust native source");
        names.push(name);
    }
    names.sort();
    assert_eq!(
        names,
        [
            "app.rs",
            "core_file_batch.rs",
            "core_provenance.rs",
            "encrypted_readback.rs",
            "lib.rs",
            "main.rs",
            "session.rs",
            "synthetic_bundle.rs",
            "workspace_receipt.rs"
        ],
        "new, missing or nested native D2 source requires explicit review"
    );
    names.into_iter().map(|name| root.join(name)).collect()
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
    for path in audited_native_source_files(&root) {
        let source = fs::read_to_string(&path).expect("UTF-8 native source");
        assert!(
            disallowed_source_api(&source).is_none(),
            "D2 source {} acquired forbidden networking/browser/process entrypoint",
            path.display(),
        );
    }
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
        [
            "eframe",
            "medorigin-desktop-d0-rust-prototype",
            "serde_json",
            "sha2",
        ],
        "D2 dependency additions require a separate safety review"
    );
    assert!(
        dependencies.contains("default-features = false")
            && dependencies.contains("\"accesskit\"")
            && dependencies.contains("\"glow\""),
        "D2 must preserve explicit native-only eframe features and AccessKit"
    );
    // SHA-256 is an additional explicitly reviewed direct dependency for
    // the two in-memory fictional preview byte checks. Do not silently admit
    // another crate version, extra default features or a new network library.
    const PINNED_SHA2_DEPENDENCY: &str =
        "sha2 = { version = \"=0.11.1\", default-features = false }";
    assert!(
        dependencies
            .lines()
            .any(|line| line.trim() == PINNED_SHA2_DEPENDENCY),
        "D2 SHA-256 source integrity requires reviewed, exact locked sha2"
    );
    let lock = fs::read_to_string(Path::new(env!("CARGO_MANIFEST_DIR")).join("Cargo.lock"))
        .expect("committed Cargo lock");
    assert!(
        lock.contains("name = \"sha2\"\nversion = \"0.11.1\""),
        "reviewed sha2 version absent from lockfile"
    );
    let own_package = lock
        .split("[[package]]\nname = \"medorigin-desktop-d2-native-egui\"")
        .nth(1)
        .and_then(|s| s.split("[[package]]").next())
        .expect("locked D2 root package");
    assert!(
        own_package.contains("\"sha2\""),
        "D2 must pin its direct SHA-256 runtime dependency in Cargo.lock"
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

#[test]
fn guard_rejects_aliased_socket_imports_and_external_rust_inclusion() {
    // These are adversarial examples, never executed network operations.
    for source in [
        "use std::net;",
        "use std::{net::TcpStream};",
        "use std::{ net :: TcpStream };",
        "include!(\"hidden_network.rs\");",
        "#[path = \"nested/hidden_network.rs\"] mod hidden;",
    ] {
        assert!(
            disallowed_source_api(source).is_some(),
            "source-only guard missed dangerous indirection: {source}"
        );
    }
}

#[test]
fn synthetic_core_reader_example_is_explicitly_reviewed_for_network_and_process_imports() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR"));
    let example = root.join("examples/core_provenance_stdin.rs");
    let source = fs::read_to_string(example).expect("source controlled nonclinical QA reader");
    assert!(
        disallowed_source_api(&source).is_none(),
        "synthetic Core reader must remain process-free and browser/network-free"
    );
    assert!(source.contains("admit_fixed_fictional_core_report"));
    assert!(source.contains("FHIR_R4_NOT_VALIDATED"));
}

#[test]
fn guard_refuses_unreviewed_nested_module_layout() {
    use std::time::{SystemTime, UNIX_EPOCH};
    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .expect("clock")
        .as_nanos();
    let root = std::env::temp_dir().join(format!(
        "medorigin-d2-layout-{}-{unique}",
        std::process::id()
    ));
    fs::create_dir(&root).expect("create owned test directory");
    for name in [
        "app.rs",
        "core_file_batch.rs",
        "core_provenance.rs",
        "encrypted_readback.rs",
        "lib.rs",
        "main.rs",
        "session.rs",
        "synthetic_bundle.rs",
        "workspace_receipt.rs",
    ] {
        fs::write(root.join(name), "// synthetic, no execution").expect("fixture");
    }
    assert_eq!(audited_native_source_files(&root).len(), 9);
    let nested = root.join("hidden");
    fs::create_dir(&nested).expect("create nested fixture");
    fs::write(nested.join("socket.rs"), "// unreviewed nested source").expect("fixture");
    let refused = std::panic::catch_unwind(|| audited_native_source_files(&root)).is_err();
    fs::remove_dir_all(&root).expect("remove only owned test fixture");
    assert!(refused, "nested source directory must fail closed");
}
