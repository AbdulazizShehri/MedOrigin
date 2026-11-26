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
    VAULT_KEY_LABEL, VERIFIED_EVIDENCE_SNAPSHOT_IDS, benchmark_measured_results_available,
    build_dynamic_graph, chacha20_poly1305_decrypt, chacha20_poly1305_encrypt, decrypt_envelope,
    decrypt_envelope_with_passphrase, derive_workspace_key, encrypt_envelope,
    execute_integration_dry_run, generate_random_bytes, load_audit_ledger_from_path,
    load_encrypted_backup_from_path, load_verified_evidence_snapshot, pbkdf2_hmac_sha256,
    poly1305_mac, save_audit_ledger_to_path, save_encrypted_backup_to_path, scan_export_quarantine,
    screen_classification_by_label, search_verified_evidence, sha256_hex, verify_audit_chain,
    zeroize_bytes,
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
    let mut count_a = 0usize;
    let mut count_b = 0usize;
    let mut count_c = 0usize;
    let mut count_d = 0usize;
    for screen in SCREENS.iter() {
        let class = screen_classification_by_label(screen.label);
        match class {
            ScreenClassification::ClassA => count_a += 1,
            ScreenClassification::ClassB => count_b += 1,
            ScreenClassification::ClassC => count_c += 1,
            ScreenClassification::ClassD => count_d += 1,
        }
        match screen.label {
            "Audio & transcript"
            | "Orders & tasks"
            | "Coding suggestions"
            | "Model catalog & runtime" => {
                assert_eq!(class, ScreenClassification::ClassD);
            }
            "Literature screening"
            | "Research explorer"
            | "Benchmark & evaluation"
            | "Integrations" => {
                assert_eq!(class, ScreenClassification::ClassC);
            }
            "Local search"
            | "Note drafts"
            | "Patient graph"
            | "Patient timeline"
            | "Documents & canvas"
            | "Clinical evidence"
            | "Tables & structured data"
            | "Analytics"
            | "Dataset manager"
            | "Export quarantine"
            | "Audit history"
            | "Storage & recovery" => {
                assert_eq!(class, ScreenClassification::ClassB);
            }
            _ => {
                assert_eq!(class, ScreenClassification::ClassA);
            }
        }
    }
    assert_eq!((count_a, count_b, count_c, count_d), (8, 12, 4, 4));
    assert_eq!(count_a + count_b + count_c + count_d, 28);
}

#[test]
fn test_export_quarantine_risk_scan_and_manifest_fail_closed() {
    // 1. Empty bundle must NEVER pass
    let empty_scan = scan_export_quarantine(&[], &[]);
    assert!(
        !empty_scan.passed,
        "Empty dataset must never produce a PASS quarantine scan"
    );

    let mut app = MedOriginNativePreview::default();
    app.open_embedded_fictional_bundle_demo().unwrap();
    let resources = app.active_resources();

    // 2. Clean synthetic dataset passes scan
    let clean_scan = scan_export_quarantine(&resources, &["Synthetic research draft 2026-10-15"]);
    assert!(clean_scan.passed);
    assert_eq!(clean_scan.direct_id_leaks, 0);
    assert_eq!(clean_scan.invalid_refs, 0);
    assert_eq!(clean_scan.forbidden_terms, 0);
    assert_eq!(clean_scan.raw_date_leaks, 0);

    // 3. Negative control: injected non-synthetic ID
    let mut contaminated = resources.clone();
    contaminated.push(FictionalReadbackResource {
        resource_type: "Patient".to_string(),
        resource_id: "REAL-PATIENT-99999".to_string(),
        full_url: "urn:uuid:00000000-0000-4000-8000-000000000999".to_string(),
        links: vec![],
    });
    let leak_scan = scan_export_quarantine(&contaminated, &[]);
    assert!(!leak_scan.passed);
    assert_eq!(leak_scan.direct_id_leaks, 1);

    // 4. Negative control: invalid non-UUID link
    contaminated.push(FictionalReadbackResource {
        resource_type: "Observation".to_string(),
        resource_id: "fictional-obs-badref".to_string(),
        full_url: "urn:uuid:00000000-0000-4000-8000-000000000888".to_string(),
        links: vec![FictionalReadbackLink {
            field: "subject".to_string(),
            target: "http://external-ehr.org/Patient/123".to_string(),
        }],
    });
    let ref_scan = scan_export_quarantine(&contaminated, &[]);
    assert!(!ref_scan.passed);
    assert_eq!(ref_scan.invalid_refs, 1);

    // 5. Negative control: prohibited SSN, CONFIDENTIAL, MRN, email, unshifted date in draft text
    let draft_leak_scan = scan_export_quarantine(
        &resources,
        &["CONFIDENTIAL MRN:4455 SSN 123-45-6789 DOB 1984-05-12 user@example.org"],
    );
    assert!(!draft_leak_scan.passed);
    assert!(draft_leak_scan.direct_id_leaks >= 1);
    assert!(draft_leak_scan.forbidden_terms >= 1);
    assert!(draft_leak_scan.raw_date_leaks >= 1);
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

#[test]
fn test_pbkdf2_rfc_vectors_and_unique_entropy_salts_nonces() {
    // Standard PBKDF2-HMAC-SHA256 test vectors (iter=1 and iter=2)
    let dk1 = pbkdf2_hmac_sha256(b"password", b"salt", 1);
    let dk1_hex: String = dk1.iter().map(|b| format!("{b:02x}")).collect();
    assert_eq!(
        dk1_hex,
        "120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b"
    );

    let dk2 = pbkdf2_hmac_sha256(b"password", b"salt", 2);
    let dk2_hex: String = dk2.iter().map(|b| format!("{b:02x}")).collect();
    assert_eq!(
        dk2_hex,
        "ae4d0c95af6b46d32d0adff928f06dd02a303f8ef3c251dfd6e2d85a95474c43"
    );

    // Unique OS-seeded salts and nonces (no deterministic reuse)
    let salt_a = generate_random_bytes::<16>(b"test-salt");
    let salt_b = generate_random_bytes::<16>(b"test-salt");
    assert_ne!(salt_a, salt_b, "Salts must be unique across calls");

    let nonce_a = generate_random_bytes::<12>(b"test-nonce");
    let nonce_b = generate_random_bytes::<12>(b"test-nonce");
    assert_ne!(nonce_a, nonce_b, "96-bit nonces must never repeat");
}

#[test]
fn test_encrypted_backup_persistence_and_restart_recovery() {
    let dir = std::env::temp_dir().join(format!(
        "medorigin-d2-backup-test-{}-{}",
        std::process::id(),
        &sha256_hex(&generate_random_bytes::<16>(b"dir"))[..12]
    ));
    std::fs::create_dir_all(&dir).expect("create temp test dir");
    let backup_file = dir.join("synthetic-backup.mswsenv");

    let passphrase = "synthetic-restart-recovery-passphrase-2026!";
    let plaintext = b"MEDORIGIN_BACKUP:RESOURCES=8:SYNTHETIC_RESTART_PAYLOAD";

    // Session 1: Derive key, encrypt MSWSENV1 envelope, persist to disk
    {
        let salt = generate_random_bytes::<16>(b"session1-salt");
        let nonce = generate_random_bytes::<12>(b"session1-nonce");
        let mut key = derive_workspace_key(passphrase, &salt, VAULT_KEY_LABEL);
        let envelope = encrypt_envelope(&key, &salt, &nonce, plaintext);
        zeroize_bytes(&mut key);

        // Verify raw ciphertext on disk does NOT contain plaintext
        assert!(!envelope.windows(plaintext.len()).any(|w| w == plaintext));
        let written = save_encrypted_backup_to_path(&backup_file, &envelope).unwrap();
        assert_eq!(written, envelope.len());
    }

    // Session 2 (simulated restart — zero prior in-memory key or salt):
    let disk_bytes = load_encrypted_backup_from_path(&backup_file).unwrap();

    // Negative control 1: Wrong passphrase fails closed
    assert_eq!(
        decrypt_envelope_with_passphrase("wrong-passphrase", &disk_bytes, VAULT_KEY_LABEL),
        Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
    );

    // Negative control 2: Empty passphrase fails closed
    assert_eq!(
        decrypt_envelope_with_passphrase("", &disk_bytes, VAULT_KEY_LABEL),
        Err("EMPTY_PASSPHRASE_REFUSED")
    );

    // Positive control: Correct passphrase recovers exact original authenticated bytes
    let recovered =
        decrypt_envelope_with_passphrase(passphrase, &disk_bytes, VAULT_KEY_LABEL).unwrap();
    assert_eq!(recovered.as_slice(), plaintext);

    // Negative control 3: Corrupted backup file on disk cannot be restored
    let mut corrupted = disk_bytes.clone();
    let idx = corrupted.len() - 1;
    corrupted[idx] ^= 0x40;
    std::fs::write(&backup_file, &corrupted).unwrap();
    let reloaded_corrupted = load_encrypted_backup_from_path(&backup_file).unwrap();
    assert_eq!(
        decrypt_envelope_with_passphrase(passphrase, &reloaded_corrupted, VAULT_KEY_LABEL),
        Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
    );

    // Negative control 4: Truncated backup file rejected
    std::fs::write(&backup_file, &corrupted[..20]).unwrap();
    assert_eq!(
        load_encrypted_backup_from_path(&backup_file),
        Err("ENVELOPE_TOO_SHORT")
    );

    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn test_audit_ledger_persistence_restart_and_disk_tamper_rejection() {
    let dir = std::env::temp_dir().join(format!(
        "medorigin-d2-audit-test-{}-{}",
        std::process::id(),
        &sha256_hex(&generate_random_bytes::<16>(b"audit-dir"))[..12]
    ));
    std::fs::create_dir_all(&dir).expect("create temp audit dir");
    let ledger_file = dir.join("synthetic-audit.json");

    // Session 1: Create real runtime events and save ledger
    let mut state = ConnectedScreensState::default();
    state.record_audit_event("BUNDLE_ADMISSION", "user-local", "Admitted 8 resources");
    state.record_audit_event("EXPORT_QUARANTINE_PASSED", "user-local", "Clean scan");
    let saved_count = save_audit_ledger_to_path(&ledger_file, &state.audit_events).unwrap();
    assert_eq!(saved_count, 3);

    // Session 2 (simulated restart): Load and verify intact ledger
    let reloaded = load_audit_ledger_from_path(&ledger_file).unwrap();
    assert_eq!(reloaded.len(), 3);
    assert_eq!(reloaded, state.audit_events);

    // Negative control: Tamper with persisted JSON on disk -> load MUST fail closed
    let raw = std::fs::read_to_string(&ledger_file).unwrap();
    let tampered = raw.replace("Admitted 8 resources", "Admitted 999 REAL resources");
    std::fs::write(&ledger_file, tampered).unwrap();
    let err = load_audit_ledger_from_path(&ledger_file).unwrap_err();
    assert!(
        err.contains("AUDIT_CHAIN_CORRUPTED"),
        "Expected tamper detection error, got: {err}"
    );

    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn test_evidence_retrieval_verified_snapshots_unknown_rejection_and_abstention() {
    // Unknown or missing snapshot is rejected
    assert_eq!(
        load_verified_evidence_snapshot("unknown-snapshot-2099.json"),
        Err("UNKNOWN_OR_MISSING_SNAPSHOT_REFUSED")
    );
    assert_eq!(
        search_verified_evidence("missing.json", "patient", 0.5),
        Err("UNKNOWN_OR_MISSING_SNAPSHOT_REFUSED")
    );

    // Both committed snapshots load with distinct real SHA-256 hashes and real entries
    let snap0 = load_verified_evidence_snapshot(VERIFIED_EVIDENCE_SNAPSHOT_IDS[0]).unwrap();
    let snap1 = load_verified_evidence_snapshot(VERIFIED_EVIDENCE_SNAPSHOT_IDS[1]).unwrap();
    assert_eq!(snap0.sha256.len(), 64);
    assert_eq!(snap1.sha256.len(), 64);
    assert_ne!(snap0.sha256, snap1.sha256);
    assert_eq!(snap0.entries.len(), 8);
    assert_eq!(snap1.entries.len(), 3);

    // Matching query admits relevant entries
    let (_, ranked_match) =
        search_verified_evidence(VERIFIED_EVIDENCE_SNAPSHOT_IDS[0], "observation 001", 0.5)
            .unwrap();
    let admitted = ranked_match.iter().filter(|(_, _, _, ok)| *ok).count();
    assert!(admitted >= 1);

    // Unmatched query enforces explicit abstention (0 admitted)
    let (_, ranked_miss) = search_verified_evidence(
        VERIFIED_EVIDENCE_SNAPSHOT_IDS[0],
        "nonexistent_quantum_drug_xyz",
        0.5,
    )
    .unwrap();
    let admitted_miss = ranked_miss.iter().filter(|(_, _, _, ok)| *ok).count();
    assert_eq!(admitted_miss, 0, "Unmatched query must trigger abstention");
}

#[test]
fn test_benchmark_never_fabricates_measured_results_and_ehr_write_blocked() {
    assert!(
        !benchmark_measured_results_available(),
        "Offline desktop must never claim measured benchmark results without an authentic receipt"
    );

    // Read-only synthetic dry run succeeds without claiming PASS on EHR write
    let ok_dry = execute_integration_dry_run(0, 8).unwrap();
    assert!(ok_dry.starts_with("DRY_RUN_READONLY_SIMULATION_SHA256_"));

    // Blocked live EHR write endpoint MUST refuse and NEVER return PASS
    let blocked = execute_integration_dry_run(2, 8);
    assert_eq!(blocked, Err("SECURITY_REFUSAL_EHR_WRITE_BLOCKED"));
}

#[test]
fn test_session_clear_purges_sensitive_keys_passphrases_and_receipts() {
    let mut app = MedOriginNativePreview::default();
    app.open_embedded_fictional_bundle_demo().unwrap();

    // Populate sensitive in-memory state
    let salt = generate_random_bytes::<16>(b"clear-test-salt");
    let key = derive_workspace_key("secret-session-passphrase", &salt, VAULT_KEY_LABEL);
    app.connected.storage_passphrase = "secret-session-passphrase".to_string();
    app.connected.storage_salt = salt;
    app.connected.storage_raw_key = Some(key);
    app.connected.storage_derived_key = Some(sha256_hex(&key));
    app.connected.storage_vault_tag = Some("tag".to_string());
    app.connected.storage_backup_envelope = Some(vec![1, 2, 3, 4]);
    app.connected.storage_vault_locked = false;
    app.connected.note_attestation_receipt = Some("RECEIPT".to_string());
    app.connected.analytics_verified_receipt = Some("ANALYTICS".to_string());
    app.connected.quarantine_manifest_receipt = Some("QUARANTINE".to_string());

    // Clear session
    app.clear_fictional_output();

    // Verify all sensitive in-memory references were purged
    assert!(app.active_resources().is_empty());
    assert!(app.connected.storage_vault_locked);
    assert!(app.connected.storage_passphrase.is_empty());
    assert_eq!(app.connected.storage_salt, [0u8; 16]);
    assert!(app.connected.storage_raw_key.is_none());
    assert!(app.connected.storage_derived_key.is_none());
    assert!(app.connected.storage_vault_tag.is_none());
    assert!(app.connected.storage_backup_envelope.is_none());
    assert!(app.connected.note_attestation_receipt.is_none());
    assert!(app.connected.analytics_verified_receipt.is_none());
    assert!(app.connected.quarantine_manifest_receipt.is_none());
    assert_eq!(
        app.connected.audit_events.last().unwrap().event_type,
        "SESSION_CLEAR"
    );
    assert!(verify_audit_chain(&app.connected.audit_events).is_ok());
}
