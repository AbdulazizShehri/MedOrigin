// Nonpublishing policy: the synthetic Tauri/WebView2 desktop has observed
// external TCP egress. Debug/testing is permitted; release/custom profiles
// must remain compile-time blocked until independent security acceptance.
mod build_gate;

fn main() {
    let profile = std::env::var("PROFILE").unwrap_or_default();
    build_gate::enforce_nonreleasable_profile(&profile)
        .unwrap_or_else(|message| panic!("{message}"));
    println!("cargo:rerun-if-env-changed=PROFILE");
    tauri_build::build();
}
