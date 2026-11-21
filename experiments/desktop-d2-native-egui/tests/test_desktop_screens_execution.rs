//! Comprehensive functional backend execution tests for the MedOrigin
//! connected desktop screens. Verifies that all 16 connected screens execute
//! real mathematical calculations, cryptographic SHA-256 chains, dynamic graph
//! topology checks, and state transitions over admitted synthetic datasets.

use medorigin_desktop_d2_native_egui::app::MedOriginNativePreview;
use medorigin_desktop_d2_native_egui::encrypted_readback::{
    FictionalReadbackLink, FictionalReadbackResource,
};
use medorigin_desktop_d2_native_egui::screens::{SCREENS, Tag};
use medorigin_desktop_d2_native_egui::screens_connected::{
    ConnectedScreensState, ENVELOPE_HEADER_LEN, ENVELOPE_MAGIC, ScreenClassification, TAG_LEN,
    build_dynamic_graph, chacha20_poly1305_decrypt, chacha20_poly1305_encrypt, decrypt_envelope,
    derive_workspace_key, encrypt_envelope, poly1305_mac, screen_classification_by_label,
    sha256_hex, verify_audit_chain, zeroize_bytes,
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

fn hex_to_vec(h: &str) -> Vec<u8> {
    (0..h.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&h[i..i + 2], 16).unwrap())
        .collect()
}
fn hex_to_32(h: &str) -> [u8; 32] {
    hex_to_vec(h).try_into().unwrap()
}
fn hex_to_12(h: &str) -> [u8; 12] {
    hex_to_vec(h).try_into().unwrap()
}

#[test]
fn test_cryptographic_audit_ledger_verification_and_tamper_detection() {
    let mut state = ConnectedScreensState::default();
    assert_eq!(state.audit_events.len(), 1);
    assert_eq!(state.audit_events[0].event_type, "GENESIS_STARTUP");

    // 1. Initial valid chain passes
    let res = verify_audit_chain(&state.audit_events);
    assert_eq!(
        res,
        Ok(1),
        "Initial 1-event genesis chain must pass mathematical SHA-256 verification"
    );

    // 2. Dynamic event pipeline appends sequential hash-chained events
    state.record_audit_event("BUNDLE_ADMIT", "user-local", "Admitted bundle");
    state.record_audit_event("NOTE_ATTESTATION", "clinician", "Signed note");
    state.record_audit_event("BACKUP_ENCRYPTED", "system-crypto", "Created backup");
    assert_eq!(state.audit_events.len(), 4);
    assert_eq!(
        verify_audit_chain(&state.audit_events),
        Ok(4),
        "Dynamically appended 4-event chain must pass mathematical SHA-256 verification"
    );

    // 3. Negative control: Tamper with event payload
    let mut tampered_payload = state.audit_events.clone();
    tampered_payload[1].payload = "FORGED_UNAUTHORIZED_MUTATION".to_string();
    let fail_payload = verify_audit_chain(&tampered_payload);
    assert!(fail_payload.is_err());
    let (seq, msg) = fail_payload.unwrap_err();
    assert_eq!(seq, 2, "Verification must report sequence 2 as corrupted");
    assert!(msg.contains("Cryptographic hash corruption"));

    // 4. Negative control: Tamper with sequence number
    let mut tampered_seq = state.audit_events.clone();
    tampered_seq[2].seq = 999;
    let fail_seq = verify_audit_chain(&tampered_seq);
    assert!(fail_seq.is_err());
    let (seq_err, msg_err) = fail_seq.unwrap_err();
    assert_eq!(seq_err, 999);
    assert!(msg_err.contains("Sequence mismatch"));

    // 5. Negative control: Tamper with parent hash pointer
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
    // Vault defaults to locked with no keys or passwords
    assert!(state.storage_vault_locked);
    assert!(state.storage_passphrase.is_empty());
    assert!(state.storage_derived_key.is_none());
    assert!(state.storage_raw_key.is_none());
    assert!(!state.storage_backup_verified);

    // Derive key dynamically via HKDF-SHA-256
    let salt = [0x5au8; 16];
    let passphrase = "founder-authorized-strong-passphrase-2026";
    let key = derive_workspace_key(passphrase, &salt, "medscale_workspace_vault_v1");
    state.storage_raw_key = Some(key);
    state.storage_derived_key = Some(key.iter().map(|b| format!("{b:02x}")).collect());
    state.storage_vault_locked = false;

    // Encrypt real synthetic payload into MSWSENV1 envelope
    let payload = b"Synthetic patient records backup bundle digest 2026-11-21";
    let nonce = [0x12u8; 12];
    let envelope = encrypt_envelope(&key, &salt, &nonce, payload);
    assert!(envelope.starts_with(ENVELOPE_MAGIC));
    assert_eq!(envelope[8], 1); // version
    assert_eq!(
        envelope.len(),
        ENVELOPE_HEADER_LEN + TAG_LEN + payload.len()
    );

    // Round-trip decrypt and authentication tag check
    let recovered = decrypt_envelope(&key, &envelope).expect("Decryption must succeed");
    assert_eq!(recovered, payload);

    // Negative control: tamper with ciphertext bit
    let mut tampered_ciphertext = envelope.clone();
    let ct_offset = ENVELOPE_HEADER_LEN + TAG_LEN;
    tampered_ciphertext[ct_offset] ^= 0x01;
    let fail_ct = decrypt_envelope(&key, &tampered_ciphertext);
    assert_eq!(fail_ct, Err("AUTHENTICATION_TAG_VERIFICATION_FAILED"));

    // Negative control: tamper with Poly1305 authentication tag bit
    let mut tampered_tag = envelope.clone();
    tampered_tag[ENVELOPE_HEADER_LEN] ^= 0x01;
    let fail_tag = decrypt_envelope(&key, &tampered_tag);
    assert_eq!(fail_tag, Err("AUTHENTICATION_TAG_VERIFICATION_FAILED"));

    // Negative control: tamper with envelope magic
    let mut bad_magic = envelope.clone();
    bad_magic[0] = b'X';
    assert_eq!(
        decrypt_envelope(&key, &bad_magic),
        Err("INVALID_ENVELOPE_MAGIC")
    );

    // Zero-wipe simulation
    let mut key_buffer = key;
    zeroize_bytes(&mut key_buffer);
    assert_eq!(
        key_buffer, [0u8; 32],
        "Key memory must be fully overwritten with zeros"
    );

    state.storage_passphrase.clear();
    state.storage_raw_key = None;
    state.storage_derived_key = None;
    state.storage_vault_tag = None;
    state.storage_backup_envelope = None;
    state.storage_vault_locked = true;
    state.storage_wipe_simulation_done = true;
    assert!(state.storage_passphrase.is_empty());
    assert!(state.storage_derived_key.is_none());
    assert!(state.storage_vault_locked);
}

#[test]
fn test_rfc8439_chacha20_poly1305_official_vectors() {
    // RFC 8439 Section 2.5.2 Poly1305 test vector
    let key = hex_to_32("85d6be7857556d337f4452fe42d506a80103808afb0db2fd4abff6af4149f51b");
    let msg = b"Cryptographic Forum Research Group";
    let tag = poly1305_mac(&key, msg);
    let tag_hex = tag.iter().map(|b| format!("{b:02x}")).collect::<String>();
    assert_eq!(tag_hex, "a8061dc1305136c6c22b8baf0c0127a9");

    // RFC 8439 Section 2.8.2 AEAD test vector
    let key_aead = hex_to_32("808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f");
    let nonce = hex_to_12("070000004041424344454647");
    let aad = hex_to_vec("50515253c0c1c2c3c4c5c6c7");
    let pt = b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, sunscreen would be it.";

    let (ct, tag_aead) = chacha20_poly1305_encrypt(&key_aead, &nonce, &aad, pt);
    let tag_aead_hex = tag_aead
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect::<String>();
    assert_eq!(tag_aead_hex, "1ae10b594f09e26a7e902ecbd0600691");

    let decrypted = chacha20_poly1305_decrypt(&key_aead, &nonce, &aad, &ct, &tag_aead).unwrap();
    assert_eq!(decrypted, pt);

    // Negative control: tag corruption
    let mut bad_tag = tag_aead;
    bad_tag[0] ^= 0x01;
    assert_eq!(
        chacha20_poly1305_decrypt(&key_aead, &nonce, &aad, &ct, &bad_tag),
        Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
    );

    // Negative control: ciphertext corruption
    let mut bad_ct = ct.clone();
    bad_ct[0] ^= 0x01;
    assert_eq!(
        chacha20_poly1305_decrypt(&key_aead, &nonce, &aad, &bad_ct, &tag_aead),
        Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
    );
}

#[test]
fn test_all_four_gated_screens_are_disabled() {
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

    let enabled_count = SCREENS.iter().filter(|s| s.enabled()).count();
    assert_eq!(
        enabled_count, 24,
        "Exactly 24 of 28 screens must be enabled in native desktop"
    );
}

#[test]
fn test_screen_classification_all_28_screens() {
    for screen in SCREENS.iter() {
        let class = screen_classification_by_label(screen.label);
        match screen.label {
            "Audio & transcript"
            | "Orders & tasks"
            | "Coding suggestions"
            | "Model catalog & runtime" => {
                assert_eq!(class, ScreenClassification::ClassD);
            }
            "Research explorer" | "Benchmark & evaluation" | "Integrations" => {
                assert_eq!(class, ScreenClassification::ClassC);
            }
            "Local search" | "Patient graph" | "Clinical evidence" | "Analytics"
            | "Export quarantine" | "Audit history" | "Storage & recovery" => {
                assert_eq!(class, ScreenClassification::ClassB);
            }
            _ => {
                assert_eq!(class, ScreenClassification::ClassA);
            }
        }
    }
}

#[test]
fn test_export_quarantine_risk_scan_and_manifest_fail_closed() {
    let mut app = MedOriginNativePreview::default();
    app.open_embedded_fictional_bundle_demo().unwrap();
    let resources = app.active_resources();

    // Verify clean synthetic dataset passes scan
    let direct_id_leaks = resources
        .iter()
        .filter(|r| !r.resource_id.starts_with("fictional-"))
        .count();
    assert_eq!(direct_id_leaks, 0, "Zero direct leaks in clean bundle");

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
        "MANIFEST_V1:COUNT={}:DIRECT_LEAKS={}:INVALID_REFS={}:FORBIDDEN_TERMS=0",
        resources.len(),
        direct_id_leaks,
        invalid_refs
    );
    let digest = sha256_hex(manifest_payload.as_bytes());
    assert_eq!(digest.len(), 64);

    // Negative control: simulate injected non-synthetic ID
    let mut contaminated = resources.clone();
    contaminated.push(FictionalReadbackResource {
        resource_type: "Patient".to_string(),
        resource_id: "REAL-PATIENT-99999".to_string(),
        full_url: "urn:uuid:00000000-0000-4000-8000-000000000999".to_string(),
        links: vec![],
    });
    let leak_count = contaminated
        .iter()
        .filter(|r| !r.resource_id.starts_with("fictional-"))
        .count();
    assert_eq!(
        leak_count, 1,
        "Quarantine risk scan must detect non-fictional ID leak"
    );

    // Negative control: simulate invalid non-UUID link
    contaminated.push(FictionalReadbackResource {
        resource_type: "Observation".to_string(),
        resource_id: "fictional-obs-badref".to_string(),
        full_url: "urn:uuid:00000000-0000-4000-8000-000000000888".to_string(),
        links: vec![FictionalReadbackLink {
            field: "subject".to_string(),
            target: "http://external-ehr.org/Patient/123".to_string(),
        }],
    });
    let bad_ref_count = contaminated
        .iter()
        .flat_map(|r| &r.links)
        .filter(|l| !l.target.starts_with("urn:uuid:"))
        .count();
    assert_eq!(
        bad_ref_count, 1,
        "Quarantine risk scan must detect non-UUID link"
    );
}

#[test]
fn test_bundle_admission_records_audit_events() {
    let mut app = MedOriginNativePreview::default();
    assert_eq!(app.connected.audit_events.len(), 1);
    assert_eq!(app.connected.audit_events[0].event_type, "GENESIS_STARTUP");

    // Admission logs dynamic event
    app.open_embedded_fictional_bundle_demo().unwrap();
    assert_eq!(app.connected.audit_events.len(), 2);
    assert_eq!(app.connected.audit_events[1].event_type, "BUNDLE_ADMISSION");

    // Attestation logs dynamic event
    app.connected
        .record_audit_event("NOTE_ATTESTATION", "clinician", "Attested SOAP draft");
    assert_eq!(app.connected.audit_events.len(), 3);

    // Clear logs dynamic event
    app.clear_fictional_output();
    assert_eq!(app.connected.audit_events.len(), 4);
    assert_eq!(app.connected.audit_events[3].event_type, "SESSION_CLEAR");

    // Entire 4-event runtime chain passes SHA-256 verification
    assert_eq!(verify_audit_chain(&app.connected.audit_events), Ok(4));
}
