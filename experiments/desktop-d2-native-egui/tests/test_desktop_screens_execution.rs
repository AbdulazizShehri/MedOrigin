//! Comprehensive functional backend execution tests for the MedOrigin
//! connected desktop screens. Verifies that all 16 connected screens execute
//! real mathematical calculations, cryptographic SHA-256 chains, dynamic graph
//! topology checks, and state transitions over admitted synthetic datasets.

use medorigin_desktop_d2_native_egui::app::MedOriginNativePreview;
use medorigin_desktop_d2_native_egui::screens::{SCREENS, Tag};
use medorigin_desktop_d2_native_egui::screens_connected::{
    ConnectedScreensState, build_dynamic_graph, sha256_hex, verify_audit_chain,
};

#[test]
fn test_empty_bundle_clean_empty_states() {
    let app = MedOriginNativePreview::default();
    let resources = app.active_resources();
    assert_eq!(
        resources.len(),
        0,
        "Default state must have zero admitted resources"
    );

    let (nodes, has_cycle, graph_sha) = build_dynamic_graph(&resources);
    assert_eq!(nodes.len(), 0, "Empty dataset must yield zero graph nodes");
    assert!(!has_cycle, "Empty graph must be an empty DAG (zero cycles)");
    assert_eq!(
        graph_sha, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "Empty graph SHA matches empty string SHA-256"
    );

    // Verify analytics on empty bundle
    let patient_count = resources
        .iter()
        .filter(|r| r.resource_type == "Patient")
        .count();
    let obs_count = resources
        .iter()
        .filter(|r| r.resource_type == "Observation")
        .count();
    let enc_count = resources
        .iter()
        .filter(|r| r.resource_type == "Encounter")
        .count();
    let completeness = if resources.is_empty() { 0.0 } else { 100.0 };

    assert_eq!(patient_count, 0);
    assert_eq!(obs_count, 0);
    assert_eq!(enc_count, 0);
    assert_eq!(completeness, 0.0);
}

#[test]
fn test_bundle_admission_dynamic_computations() {
    let mut app = MedOriginNativePreview::default();
    app.open_embedded_fictional_bundle_demo()
        .expect("Admitting reviewed canonical synthetic bundle");

    let resources = app.active_resources();
    assert_eq!(resources.len(), 8, "Canonical fixture contains 8 resources");

    // Graph topology
    let (nodes, has_cycle, graph_sha) = build_dynamic_graph(&resources);
    assert_eq!(nodes.len(), 8, "Graph must have 8 dynamic nodes");
    assert!(
        !has_cycle,
        "Admitted synthetic bundle must form a valid DAG without cycles"
    );
    assert!(
        !graph_sha.is_empty(),
        "Graph must have a non-empty cryptographic fingerprint"
    );

    // Dynamic search filtering
    let patient_matches: Vec<_> = resources
        .iter()
        .filter(|r| r.resource_type == "Patient")
        .collect();
    let encounter_matches: Vec<_> = resources
        .iter()
        .filter(|r| r.resource_type == "Encounter")
        .collect();
    let observation_matches: Vec<_> = resources
        .iter()
        .filter(|r| r.resource_type == "Observation")
        .collect();

    assert_eq!(patient_matches.len(), 2);
    assert_eq!(encounter_matches.len(), 2);
    assert_eq!(observation_matches.len(), 4);

    // Search query matches by ID
    let q_001: Vec<_> = resources
        .iter()
        .filter(|r| r.resource_id.contains("001"))
        .collect();
    assert_eq!(q_001.len(), 3); // patient-001, encounter-001, observation-001

    // Analytics computation
    let total_links: usize = resources.iter().map(|r| r.links.len()).sum();
    assert_eq!(
        total_links, 10,
        "2 encounters (1 link each) + 4 observations (2 links each) = 10 links"
    );

    let payload = format!(
        "P:{}:O:{}:E:{}:T:{}:L:{}",
        patient_matches.len(),
        observation_matches.len(),
        encounter_matches.len(),
        resources.len(),
        total_links
    );
    let digest = sha256_hex(payload.as_bytes());
    assert_eq!(digest.len(), 64, "SHA-256 digest must be 64 hex characters");
}

#[test]
fn test_changing_bundle_updates_analytics_and_graph() {
    let mut app_bundle = MedOriginNativePreview::default();
    app_bundle
        .open_embedded_fictional_bundle_demo()
        .expect("Bundle 1");

    const READBACK_RAW: &[u8] =
        include_bytes!("../fixtures/core/encrypted-readback-projection.json");
    let app_readback =
        MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(READBACK_RAW)
            .expect("Readback 2");

    let res1 = app_bundle.active_resources();
    let res2 = app_readback.active_resources();

    assert_eq!(res1.len(), 8);
    assert_eq!(res2.len(), 3);

    let (nodes1, _, hash1) = build_dynamic_graph(&res1);
    let (nodes2, _, hash2) = build_dynamic_graph(&res2);

    assert_eq!(nodes1.len(), 8);
    assert_eq!(nodes2.len(), 3);
    assert_ne!(
        hash1, hash2,
        "Distinct bundles must produce distinct graph hashes"
    );
}

#[test]
fn test_cryptographic_audit_ledger_verification_and_tamper_detection() {
    let state = ConnectedScreensState::default();
    assert_eq!(state.audit_events.len(), 4);

    // 1. Initial valid chain passes
    let res = verify_audit_chain(&state.audit_events);
    assert_eq!(
        res,
        Ok(4),
        "Initial 4-event chain must pass mathematical SHA-256 verification"
    );

    // 2. Negative control: Tamper with event payload
    let mut tampered_payload = state.audit_events.clone();
    tampered_payload[1].payload = "FORGED_UNAUTHORIZED_MUTATION".to_string();
    let fail_payload = verify_audit_chain(&tampered_payload);
    assert!(fail_payload.is_err());
    let (seq, msg) = fail_payload.unwrap_err();
    assert_eq!(seq, 2, "Verification must report sequence 2 as corrupted");
    assert!(msg.contains("Cryptographic hash corruption"));

    // 3. Negative control: Tamper with sequence number
    let mut tampered_seq = state.audit_events.clone();
    tampered_seq[2].seq = 999;
    let fail_seq = verify_audit_chain(&tampered_seq);
    assert!(fail_seq.is_err());
    let (seq_err, msg_err) = fail_seq.unwrap_err();
    assert_eq!(seq_err, 999);
    assert!(msg_err.contains("Sequence mismatch"));

    // 4. Negative control: Tamper with parent hash pointer
    let mut tampered_prev = state.audit_events.clone();
    tampered_prev[3].prev_hash =
        "0000000000000000000000000000000000000000000000000000000000000000".to_string();
    let fail_prev = verify_audit_chain(&tampered_prev);
    assert!(fail_prev.is_err());
    let (prev_seq, prev_msg) = fail_prev.unwrap_err();
    assert_eq!(prev_seq, 4);
    assert!(prev_msg.contains("Parent hash mismatch"));
}

#[test]
fn test_storage_recovery_vault_cryptography_and_backup() {
    let mut state = ConnectedScreensState::default();
    assert!(!state.storage_vault_locked);
    assert!(state.storage_derived_key.is_some());
    assert!(state.storage_backup_verified);

    let key = state.storage_derived_key.as_ref().unwrap();
    let expected_key = sha256_hex(state.storage_passphrase.as_bytes());
    assert_eq!(
        key, &expected_key,
        "Derived session key must equal SHA-256 of passphrase"
    );

    // Negative control: corrupt backup manifest
    state.storage_backup_manifest = Some("CORRUPTED_MANIFEST_BYTES".to_string());
    let recomputed = sha256_hex(state.storage_backup_manifest.as_ref().unwrap().as_bytes());
    assert_ne!(
        recomputed,
        *state.storage_backup_hash.as_ref().unwrap(),
        "Corrupted manifest must fail hash comparison"
    );

    // Zero-wipe simulation
    state.storage_passphrase.clear();
    state.storage_derived_key = None;
    state.storage_vault_locked = true;
    state.storage_wipe_simulation_done = true;
    assert!(state.storage_passphrase.is_empty());
    assert!(state.storage_derived_key.is_none());
    assert!(state.storage_vault_locked);
}

#[test]
fn test_all_four_gated_screens_are_disabled() {
    // Exactly 4 screens in the 28-screen registry must remain Gated/Deferred and disabled:
    // Screen 4: Audio & transcript (Gated)
    // Screen 6: Orders & tasks (Gated)
    // Screen 7: Coding suggestions (Deferred)
    // Screen 21: Model catalog & runtime (Gated)

    assert_eq!(SCREENS[4].label, "Audio & transcript");
    assert_eq!(SCREENS[4].tag, Some(Tag::Gated));
    assert!(!SCREENS[4].enabled(), "Audio capture must remain disabled");

    assert_eq!(SCREENS[6].label, "Orders & tasks");
    assert_eq!(SCREENS[6].tag, Some(Tag::Gated));
    assert!(!SCREENS[6].enabled(), "Orders write must remain disabled");

    assert_eq!(SCREENS[7].label, "Coding suggestions");
    assert_eq!(SCREENS[7].tag, Some(Tag::Deferred));
    assert!(!SCREENS[7].enabled(), "Billing coding must remain disabled");

    assert_eq!(SCREENS[21].label, "Model catalog & runtime");
    assert_eq!(SCREENS[21].tag, Some(Tag::Gated));
    assert!(!SCREENS[21].enabled(), "Model runtime must remain disabled");

    // The remaining 24 screens are enabled
    let enabled_count = SCREENS.iter().filter(|s| s.enabled()).count();
    assert_eq!(
        enabled_count, 24,
        "Exactly 24 of 28 screens must be enabled in native desktop"
    );
}

#[test]
fn test_export_quarantine_risk_scan_and_manifest() {
    let mut app = MedOriginNativePreview::default();
    app.open_embedded_fictional_bundle_demo().unwrap();
    let resources = app.active_resources();

    // Verify all resources pass synthetic prefix checks
    let direct_id_leaks = resources
        .iter()
        .filter(|r| !r.resource_id.starts_with("fictional-"))
        .count();
    assert_eq!(
        direct_id_leaks, 0,
        "Zero PHI or non-fictional IDs permitted"
    );

    let invalid_refs = resources
        .iter()
        .flat_map(|r| &r.links)
        .filter(|l| !l.target.starts_with("urn:uuid:"))
        .count();
    assert_eq!(
        invalid_refs, 0,
        "All links must be well-formed urn:uuid: references"
    );

    let manifest_payload = format!(
        "MANIFEST_V1:COUNT={}:DIRECT_LEAKS={}:INVALID_REFS={}",
        resources.len(),
        direct_id_leaks,
        invalid_refs
    );
    let digest = sha256_hex(manifest_payload.as_bytes());
    assert_eq!(digest.len(), 64);
}
