//! Comprehensive functional, cryptographic, persistence, and negative-control
//! execution tests for the MedOrigin Desktop D2 connected screens.

use std::fs;
use std::thread;

use medorigin_desktop_d2_native_egui::app::MedOriginNativePreview;
use medorigin_desktop_d2_native_egui::encrypted_readback::{
    FictionalReadbackLink, FictionalReadbackResource,
};
use medorigin_desktop_d2_native_egui::screens::{SCREENS, Tag};
use medorigin_desktop_d2_native_egui::screens_connected::{
    Argon2Params, ConnectedScreensState, ENVELOPE_MAGIC, ENVELOPE_V2_HEADER_LEN,
    ENVELOPE_VERSION_V1_LEGACY, ENVELOPE_VERSION_V2_ARGON2ID, MAX_ARGON2_MEMORY_KIB,
    MAX_ARGON2_PARALLELISM, MAX_ARGON2_TIME_COST, MAX_PERSISTED_FILE_BYTES, MIN_ARGON2_MEMORY_KIB,
    ScreenClassification, ScreeningStage, TAG_LEN, VAULT_KEY_LABEL_V1_LEGACY, VAULT_KEY_LABEL_V2,
    VERIFIED_EVIDENCE_SNAPSHOT_IDS, advance_screening_stage, atomic_write_local_file,
    authenticate_audit_events_with_key, benchmark_measured_results_available, build_dynamic_graph,
    bytes_to_hex, chacha20_poly1305_decrypt, chacha20_poly1305_encrypt, compute_audit_hash,
    compute_prisma_counts, decrypt_envelope_with_passphrase, deduplicate_literature_records,
    derive_audit_mac_key, derive_workspace_key_argon2id, derive_workspace_key_v1_legacy,
    encrypt_envelope_v1_raw, encrypt_envelope_v2, execute_integration_dry_run,
    execute_offline_fhir_interop_check, export_literature_screening_json,
    export_research_manifest_json, filter_research_artifacts, generate_os_random_bytes,
    import_literature_records_json, key_fingerprint_hex, load_audit_ledger_from_path,
    load_authenticated_audit_ledger_from_path, load_committed_research_artifacts,
    load_encrypted_backup_from_path, load_literature_records_from_path,
    load_local_research_artifact_file, load_verified_evidence_snapshot, migrate_v1_envelope_to_v2,
    pbkdf2_hmac_sha256, run_local_structural_benchmark, save_audit_ledger_to_path,
    save_authenticated_audit_ledger_to_path, save_encrypted_backup_to_path, scan_export_quarantine,
    screen_classification_by_label, search_verified_evidence, sha256_hex,
    validate_local_regular_path, verify_audit_chain, verify_authenticated_audit_ledger,
    verify_external_benchmark_receipt_json, zeroize_bytes,
};

fn fast_test_argon2_params() -> Argon2Params {
    Argon2Params {
        m_cost_kib: MIN_ARGON2_MEMORY_KIB,
        t_cost: 1,
        p_cost: 1,
    }
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

fn temp_test_dir(prefix: &str) -> std::path::PathBuf {
    let suffix = bytes_to_hex(&generate_os_random_bytes::<8>().unwrap());
    let dir = std::env::temp_dir().join(format!(
        "medorigin-d2-{prefix}-{}-{suffix}",
        std::process::id()
    ));
    fs::create_dir_all(&dir).expect("create temp test dir");
    dir
}

#[test]
fn test_empty_bundle_clean_empty_states() {
    let app = MedOriginNativePreview::default();
    let resources = app.active_resources();
    assert_eq!(resources.len(), 0);

    let (nodes, has_cycle, graph_sha) = build_dynamic_graph(&resources);
    assert_eq!(nodes.len(), 0);
    assert!(!has_cycle);
    assert_eq!(
        graph_sha,
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    );
}

#[test]
fn test_bundle_admission_dynamic_computations() {
    let mut app = MedOriginNativePreview::default();
    app.open_embedded_fictional_bundle_demo().unwrap();
    let resources = app.active_resources();
    assert_eq!(resources.len(), 8);

    let (nodes, has_cycle, graph_sha) = build_dynamic_graph(&resources);
    assert_eq!(nodes.len(), 8);
    assert!(!has_cycle);
    assert_eq!(graph_sha.len(), 64);

    assert_eq!(
        resources
            .iter()
            .filter(|r| r.resource_type == "Patient")
            .count(),
        2
    );
    assert_eq!(
        resources
            .iter()
            .filter(|r| r.resource_type == "Encounter")
            .count(),
        2
    );
    assert_eq!(
        resources
            .iter()
            .filter(|r| r.resource_type == "Observation")
            .count(),
        4
    );
    let total_links: usize = resources.iter().map(|r| r.links.len()).sum();
    assert_eq!(total_links, 10);
}

#[test]
fn test_changing_bundle_updates_analytics_and_graph() {
    let mut app_bundle = MedOriginNativePreview::default();
    app_bundle.open_embedded_fictional_bundle_demo().unwrap();

    const READBACK_RAW: &[u8] =
        include_bytes!("../fixtures/core/encrypted-readback-projection.json");
    let app_readback =
        MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(READBACK_RAW)
            .unwrap();

    let (nodes1, _, hash1) = build_dynamic_graph(&app_bundle.active_resources());
    let (nodes2, _, hash2) = build_dynamic_graph(&app_readback.active_resources());

    assert_eq!(nodes1.len(), 8);
    assert_eq!(nodes2.len(), 3);
    assert_ne!(hash1, hash2);
}

#[test]
fn test_rfc8439_and_pbkdf2_known_answer_vectors_via_audited_crates() {
    // RFC 8439 Section 2.8.2 AEAD test vector via audited chacha20poly1305
    let key_aead = hex_to_32("808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f");
    let nonce = hex_to_12("070000004041424344454647");
    let aad = hex_to_vec("50515253c0c1c2c3c4c5c6c7");
    let pt = b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, sunscreen would be it.";

    let (ct, tag_aead) = chacha20_poly1305_encrypt(&key_aead, &nonce, &aad, pt).unwrap();
    assert_eq!(bytes_to_hex(&tag_aead), "1ae10b594f09e26a7e902ecbd0600691");

    let decrypted = chacha20_poly1305_decrypt(&key_aead, &nonce, &aad, &ct, &tag_aead).unwrap();
    assert_eq!(decrypted.as_slice(), pt);

    // Negative controls: tag, ciphertext, and AAD bit flips rejected before release
    let mut bad_tag = tag_aead;
    bad_tag[0] ^= 0x01;
    assert_eq!(
        chacha20_poly1305_decrypt(&key_aead, &nonce, &aad, &ct, &bad_tag),
        Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
    );
    let mut bad_ct = ct.clone();
    bad_ct[0] ^= 0x01;
    assert_eq!(
        chacha20_poly1305_decrypt(&key_aead, &nonce, &aad, &bad_ct, &tag_aead),
        Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
    );
    let mut bad_aad = aad.clone();
    bad_aad[0] ^= 0x01;
    assert_eq!(
        chacha20_poly1305_decrypt(&key_aead, &nonce, &bad_aad, &ct, &tag_aead),
        Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
    );

    // Standard PBKDF2-HMAC-SHA256 known-answer vectors via audited pbkdf2
    let dk1 = pbkdf2_hmac_sha256(b"password", b"salt", 1).unwrap();
    assert_eq!(
        bytes_to_hex(dk1.as_ref()),
        "120fb6cffcf8b32c43e7225256c4f837a86548c92ccc35480805987cb70be17b"
    );
    let dk2 = pbkdf2_hmac_sha256(b"password", b"salt", 2).unwrap();
    assert_eq!(
        bytes_to_hex(dk2.as_ref()),
        "ae4d0c95af6b46d32d0adff928f06dd02a303f8ef3c251dfd6e2d85a95474c43"
    );
    assert_eq!(
        pbkdf2_hmac_sha256(b"password", b"salt", 0),
        Err("PBKDF2_ITERATIONS_OUT_OF_BOUNDS")
    );
    assert_eq!(
        pbkdf2_hmac_sha256(b"password", b"salt", 999_999),
        Err("PBKDF2_ITERATIONS_OUT_OF_BOUNDS")
    );

    // OS CSPRNG produces distinct salts and nonces via getrandom
    let salt_a = generate_os_random_bytes::<16>().unwrap();
    let salt_b = generate_os_random_bytes::<16>().unwrap();
    assert_ne!(salt_a, salt_b);
    let nonce_a = generate_os_random_bytes::<12>().unwrap();
    let nonce_b = generate_os_random_bytes::<12>().unwrap();
    assert_ne!(nonce_a, nonce_b);
}

#[test]
fn test_argon2id_bounds_dos_defense_key_separation_and_v1_migration() {
    let passphrase = "founder-authorized-strong-passphrase-2026!";
    let plaintext = b"Synthetic clinical backup snapshot 2026-11-27";
    let params = fast_test_argon2_params();

    // Reject malicious/out-of-bounds KDF parameters BEFORE allocation
    for bad in [
        Argon2Params {
            m_cost_kib: MIN_ARGON2_MEMORY_KIB - 1,
            t_cost: 1,
            p_cost: 1,
        },
        Argon2Params {
            m_cost_kib: MAX_ARGON2_MEMORY_KIB + 1,
            t_cost: 1,
            p_cost: 1,
        },
        Argon2Params {
            m_cost_kib: MIN_ARGON2_MEMORY_KIB,
            t_cost: 0,
            p_cost: 1,
        },
        Argon2Params {
            m_cost_kib: MIN_ARGON2_MEMORY_KIB,
            t_cost: MAX_ARGON2_TIME_COST + 1,
            p_cost: 1,
        },
        Argon2Params {
            m_cost_kib: MIN_ARGON2_MEMORY_KIB,
            t_cost: 1,
            p_cost: MAX_ARGON2_PARALLELISM + 1,
        },
    ] {
        assert_eq!(
            encrypt_envelope_v2(passphrase, bad, plaintext),
            Err("ARGON2_KDF_PARAMS_OUT_OF_BOUNDS")
        );
    }

    // Valid v2 encryption & decryption
    let env = encrypt_envelope_v2(passphrase, params, plaintext).unwrap();
    assert!(env.starts_with(ENVELOPE_MAGIC));
    assert_eq!(env[8], ENVELOPE_VERSION_V2_ARGON2ID);
    assert_eq!(
        env.len(),
        ENVELOPE_V2_HEADER_LEN + TAG_LEN + plaintext.len()
    );

    // Malicious header KDF params injected into envelope rejected before Argon2id runs
    let mut dos_env = env.clone();
    dos_env[13..17].copy_from_slice(&(MAX_ARGON2_MEMORY_KIB + 1024).to_be_bytes());
    assert_eq!(
        decrypt_envelope_with_passphrase(passphrase, &dos_env),
        Err("ARGON2_KDF_PARAMS_OUT_OF_BOUNDS")
    );

    // In-bounds header KDF param tamper rejected by AEAD AAD authentication
    let mut aad_tampered = env.clone();
    aad_tampered[17..21].copy_from_slice(&2u32.to_be_bytes());
    assert_eq!(
        decrypt_envelope_with_passphrase(passphrase, &aad_tampered),
        Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
    );

    // Oversized envelope rejected
    let oversized = vec![0u8; MAX_PERSISTED_FILE_BYTES + 1];
    assert_eq!(
        decrypt_envelope_with_passphrase(passphrase, &oversized),
        Err("ENVELOPE_TOO_LARGE")
    );

    // Key separation: vault encryption key != derived audit MAC key != key fingerprint
    let salt = generate_os_random_bytes::<16>().unwrap();
    let vault_key =
        derive_workspace_key_argon2id(passphrase, &salt, params, VAULT_KEY_LABEL_V2).unwrap();
    let audit_key = derive_audit_mac_key(&vault_key, &salt).unwrap();
    assert_ne!(vault_key.as_ref(), audit_key.as_ref());
    let fp = key_fingerprint_hex(&vault_key);
    assert_ne!(fp, bytes_to_hex(vault_key.as_ref()));

    // Legacy v1 -> v2 migration compatibility
    let v1_salt = generate_os_random_bytes::<16>().unwrap();
    let v1_nonce = generate_os_random_bytes::<12>().unwrap();
    let v1_key =
        derive_workspace_key_v1_legacy(passphrase, &v1_salt, VAULT_KEY_LABEL_V1_LEGACY).unwrap();
    let v1_env = encrypt_envelope_v1_raw(&v1_key, &v1_salt, &v1_nonce, plaintext).unwrap();
    let (v1_ver, v1_pt) = decrypt_envelope_with_passphrase(passphrase, &v1_env).unwrap();
    assert_eq!(v1_ver, ENVELOPE_VERSION_V1_LEGACY);
    assert_eq!(v1_pt.as_slice(), plaintext);

    let v2_env = migrate_v1_envelope_to_v2(passphrase, &v1_env, params).unwrap();
    let (v2_ver, v2_pt) = decrypt_envelope_with_passphrase(passphrase, &v2_env).unwrap();
    assert_eq!(v2_ver, ENVELOPE_VERSION_V2_ARGON2ID);
    assert_eq!(v2_pt.as_slice(), plaintext);
}

#[test]
fn test_persistence_atomic_writes_overwrite_refusal_concurrency_and_restart_recovery() {
    let dir = temp_test_dir("persist");
    let backup_file = dir.join("synthetic-backup.mswsenv");
    let passphrase = "synthetic-restart-recovery-passphrase-2026!";
    let params = fast_test_argon2_params();
    let plaintext = b"MEDORIGIN_BACKUP_V2:RESOURCES=8:SYNTHETIC_RESTART_PAYLOAD";

    // 1. Encrypt & atomic write to new path
    let env = encrypt_envelope_v2(passphrase, params, plaintext).unwrap();
    assert!(!env.windows(plaintext.len()).any(|w| w == plaintext));
    let written = save_encrypted_backup_to_path(&backup_file, &env, false).unwrap();
    assert_eq!(written, env.len());

    // 2. Existing-file overwrite protection fails closed by default
    assert_eq!(
        save_encrypted_backup_to_path(&backup_file, &env, false),
        Err("FILE_ALREADY_EXISTS_REFUSED")
    );

    // 3. Explicit overwrite succeeds atomically and leaves no leftover .tmp files
    let env2 = encrypt_envelope_v2(passphrase, params, b"UPDATED_V2_PAYLOAD").unwrap();
    save_encrypted_backup_to_path(&backup_file, &env2, true).unwrap();
    let tmp_leftovers: Vec<_> = fs::read_dir(&dir)
        .unwrap()
        .filter_map(Result::ok)
        .filter(|e| e.file_name().to_string_lossy().contains(".medorigin.tmp."))
        .collect();
    assert!(
        tmp_leftovers.is_empty(),
        "Atomic write must not leave stray temporary files"
    );

    // 4. Clean workspace restart recovery
    let disk_bytes = load_encrypted_backup_from_path(&backup_file).unwrap();
    assert_eq!(
        decrypt_envelope_with_passphrase("wrong-passphrase", &disk_bytes),
        Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
    );
    let (ver, recovered) = decrypt_envelope_with_passphrase(passphrase, &disk_bytes).unwrap();
    assert_eq!(ver, ENVELOPE_VERSION_V2_ARGON2ID);
    assert_eq!(recovered.as_slice(), b"UPDATED_V2_PAYLOAD");

    // 5. Unwritable / nonexistent parent directory fails cleanly without panic
    let missing_parent = dir.join("no-such-dir").join("backup.mswsenv");
    assert_eq!(
        save_encrypted_backup_to_path(&missing_parent, &env2, false),
        Err("PARENT_DIRECTORY_NOT_FOUND")
    );

    // 6. Concurrent access across threads never corrupts or panics
    let mut handles = Vec::new();
    for i in 0..4u32 {
        let p = dir.join(format!("concurrent-{i}.mswsenv"));
        let e = env.clone();
        handles.push(thread::spawn(move || {
            save_encrypted_backup_to_path(&p, &e, false).unwrap();
            let loaded = load_encrypted_backup_from_path(&p).unwrap();
            assert_eq!(loaded, e);
        }));
    }
    for h in handles {
        h.join().unwrap();
    }

    // 7. Corrupted and truncated disk files rejected
    let mut corrupted = disk_bytes.clone();
    let last = corrupted.len() - 1;
    corrupted[last] ^= 0x40;
    atomic_write_local_file(&backup_file, &corrupted, true).unwrap();
    let reloaded = load_encrypted_backup_from_path(&backup_file).unwrap();
    assert_eq!(
        decrypt_envelope_with_passphrase(passphrase, &reloaded),
        Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
    );
    atomic_write_local_file(&backup_file, &corrupted[..20], true).unwrap();
    assert_eq!(
        load_encrypted_backup_from_path(&backup_file),
        Err("ENVELOPE_TOO_SHORT")
    );

    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn test_authenticated_audit_ledger_adversarial_matrix() {
    let dir = temp_test_dir("audit-hmac");
    let ledger_file = dir.join("ledger.json");
    let checkpoint_file = dir.join("checkpoint.json");
    let old_ledger_file = dir.join("old-ledger.json");

    let salt = generate_os_random_bytes::<16>().unwrap();
    let vault_key = derive_workspace_key_argon2id(
        "audit-passphrase-2026!",
        &salt,
        fast_test_argon2_params(),
        VAULT_KEY_LABEL_V2,
    )
    .unwrap();
    let audit_key = derive_audit_mac_key(&vault_key, &salt).unwrap();

    // Build authenticated 4-event ledger
    let mut state = ConnectedScreensState::default();
    authenticate_audit_events_with_key(&mut state.audit_events, &audit_key);
    state.audit_mac_key = Some(audit_key.clone());
    state.record_audit_event("BUNDLE_ADMISSION", "user-local", "Admitted 8 resources");
    state.record_audit_event("NOTE_ATTESTATION", "user-local", "Signed synthetic note");
    // Save an earlier valid 3-event snapshot to test rollback detection later
    save_audit_ledger_to_path(&old_ledger_file, &state.audit_events, false).unwrap();

    state.record_audit_event("EXPORT_QUARANTINE_PASSED", "user-local", "Clean scan");
    assert_eq!(state.audit_events.len(), 4);

    let cp = save_authenticated_audit_ledger_to_path(
        &ledger_file,
        &checkpoint_file,
        &state.audit_events,
        &audit_key,
        false,
    )
    .unwrap();
    assert_eq!(cp.head_seq, 4);

    // Clean reload & verification succeeds
    let (reloaded, reloaded_cp) =
        load_authenticated_audit_ledger_from_path(&ledger_file, &checkpoint_file, &audit_key)
            .unwrap();
    assert_eq!(reloaded.len(), 4);
    assert_eq!(reloaded_cp, cp);

    // Adversarial 1: Complete SHA-256 chain reconstruction WITHOUT HMAC key (attacker rewrites all hashes)
    let mut forged = reloaded.clone();
    forged[1].payload = "FORGED_RECONSTRUCTED_EVENT".to_string();
    let mut prev = "0000000000000000000000000000000000000000000000000000000000000000".to_string();
    for ev in &mut forged {
        ev.prev_hash = prev.clone();
        ev.hash = compute_audit_hash(ev.seq, &ev.event_type, &ev.actor, &ev.payload, &prev);
        prev = ev.hash.clone();
    }
    // Unkeyed SHA-256 check ALONE would pass on full reconstruction...
    assert_eq!(verify_audit_chain(&forged), Ok(4));
    // ...but keyed HMAC verification IMMEDIATELY defeats full-chain reconstruction!
    let err_recon = verify_authenticated_audit_ledger(&forged, &audit_key, Some(&cp)).unwrap_err();
    assert!(err_recon.1.contains("AUDIT_HMAC_VERIFICATION_FAILED"));

    // Adversarial 2: Deletion of middle event
    let mut deleted = reloaded.clone();
    deleted.remove(1);
    assert!(verify_authenticated_audit_ledger(&deleted, &audit_key, Some(&cp)).is_err());

    // Adversarial 3: Reordering two events
    let mut reordered = reloaded.clone();
    reordered.swap(1, 2);
    assert!(verify_authenticated_audit_ledger(&reordered, &audit_key, Some(&cp)).is_err());

    // Adversarial 4: Insertion of extra forged event
    let mut inserted = reloaded.clone();
    let dup = inserted[1].clone();
    inserted.insert(2, dup);
    assert!(verify_authenticated_audit_ledger(&inserted, &audit_key, Some(&cp)).is_err());

    // Adversarial 5: Truncation (tail event removed) caught by protected checkpoint
    let truncated = reloaded[..3].to_vec();
    let err_trunc =
        verify_authenticated_audit_ledger(&truncated, &audit_key, Some(&cp)).unwrap_err();
    assert!(
        err_trunc
            .1
            .contains("AUDIT_ROLLBACK_OR_TRUNCATION_DETECTED")
    );

    // Adversarial 6: Rollback (replacing current ledger file with earlier valid 3-event file)
    let err_rollback =
        load_authenticated_audit_ledger_from_path(&old_ledger_file, &checkpoint_file, &audit_key)
            .unwrap_err();
    assert!(err_rollback.contains("AUDIT_ROLLBACK_OR_TRUNCATION_DETECTED"));

    // Adversarial 7: Partial/truncated JSON write on disk rejected cleanly
    let partial_file = dir.join("partial.json");
    atomic_write_local_file(&partial_file, b"{\"schema\":\"medorigin-d2-local", false).unwrap();
    let err_partial = load_audit_ledger_from_path(&partial_file).unwrap_err();
    assert!(err_partial.contains("AUDIT_LEDGER_JSON_INVALID"));

    // Adversarial 8: Wrong audit key fails HMAC verification
    let wrong_key = [0x99u8; 32];
    assert!(verify_authenticated_audit_ledger(&reloaded, &wrong_key, Some(&cp)).is_err());

    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn test_all_four_gated_screens_are_disabled() {
    assert_eq!(SCREENS[4].label, "Audio & transcript");
    assert_eq!(SCREENS[4].tag, Some(Tag::Gated));
    assert!(!SCREENS[4].enabled());

    assert_eq!(SCREENS[6].label, "Orders & tasks");
    assert_eq!(SCREENS[6].tag, Some(Tag::Gated));
    assert!(!SCREENS[6].enabled());

    assert_eq!(SCREENS[7].label, "Coding suggestions");
    assert_eq!(SCREENS[7].tag, Some(Tag::Deferred));
    assert!(!SCREENS[7].enabled());

    assert_eq!(SCREENS[21].label, "Model catalog & runtime");
    assert_eq!(SCREENS[21].tag, Some(Tag::Gated));
    assert!(!SCREENS[21].enabled());

    assert_eq!(SCREENS.iter().filter(|s| s.enabled()).count(), 24);
}

#[test]
fn test_screen_classification_all_28_screens() {
    let mut counts = (0usize, 0usize, 0usize, 0usize);
    for screen in SCREENS.iter() {
        match screen_classification_by_label(screen.label) {
            ScreenClassification::ClassA => counts.0 += 1,
            ScreenClassification::ClassB => counts.1 += 1,
            ScreenClassification::ClassC => counts.2 += 1,
            ScreenClassification::ClassD => counts.3 += 1,
        }
    }
    assert_eq!(counts, (8, 16, 0, 4));
}

#[test]
fn test_export_quarantine_risk_scan_and_manifest_fail_closed() {
    assert!(!scan_export_quarantine(&[], &[]).passed);

    let mut app = MedOriginNativePreview::default();
    app.open_embedded_fictional_bundle_demo().unwrap();
    let resources = app.active_resources();

    let clean = scan_export_quarantine(&resources, &["Synthetic research draft 2026-10-15"]);
    assert!(clean.passed);

    let mut contaminated = resources.clone();
    contaminated.push(FictionalReadbackResource {
        resource_type: "Patient".to_string(),
        resource_id: "REAL-PATIENT-99999".to_string(),
        full_url: "urn:uuid:00000000-0000-4000-8000-000000000999".to_string(),
        links: vec![],
    });
    assert!(!scan_export_quarantine(&contaminated, &[]).passed);

    contaminated.push(FictionalReadbackResource {
        resource_type: "Observation".to_string(),
        resource_id: "fictional-obs-badref".to_string(),
        full_url: "urn:uuid:00000000-0000-4000-8000-000000000888".to_string(),
        links: vec![FictionalReadbackLink {
            field: "subject".to_string(),
            target: "http://external-ehr.org/Patient/123".to_string(),
        }],
    });
    assert_eq!(scan_export_quarantine(&contaminated, &[]).invalid_refs, 1);

    let draft_leak = scan_export_quarantine(
        &resources,
        &["CONFIDENTIAL MRN:4455 SSN 123-45-6789 DOB 1984-05-12 user@example.org"],
    );
    assert!(!draft_leak.passed);
    assert!(draft_leak.direct_id_leaks >= 1);
    assert!(draft_leak.forbidden_terms >= 1);
    assert!(draft_leak.raw_date_leaks >= 1);
}

#[test]
fn test_evidence_retrieval_verified_snapshots_unknown_rejection_and_abstention() {
    assert_eq!(
        load_verified_evidence_snapshot("unknown-snapshot-2099.json"),
        Err("UNKNOWN_OR_MISSING_SNAPSHOT_REFUSED")
    );
    let snap0 = load_verified_evidence_snapshot(VERIFIED_EVIDENCE_SNAPSHOT_IDS[0]).unwrap();
    let snap1 = load_verified_evidence_snapshot(VERIFIED_EVIDENCE_SNAPSHOT_IDS[1]).unwrap();
    assert_ne!(snap0.sha256, snap1.sha256);

    let (_, ranked_match) =
        search_verified_evidence(VERIFIED_EVIDENCE_SNAPSHOT_IDS[0], "observation 001", 0.5)
            .unwrap();
    assert!(ranked_match.iter().any(|(_, _, _, ok)| *ok));

    let (_, ranked_miss) = search_verified_evidence(
        VERIFIED_EVIDENCE_SNAPSHOT_IDS[0],
        "nonexistent_quantum_drug_xyz",
        0.5,
    )
    .unwrap();
    assert_eq!(ranked_miss.iter().filter(|(_, _, _, ok)| *ok).count(), 0);
}

#[test]
fn test_benchmark_never_fabricates_measured_results_and_ehr_write_blocked() {
    assert!(!benchmark_measured_results_available());
    assert!(
        execute_integration_dry_run(0, 8)
            .unwrap()
            .starts_with("DRY_RUN_READONLY_SIMULATION_SHA256_")
    );
    assert_eq!(
        execute_integration_dry_run(2, 8),
        Err("SECURITY_REFUSAL_EHR_WRITE_BLOCKED")
    );
}

#[test]
fn test_session_clear_purges_sensitive_keys_passphrases_and_receipts() {
    let mut app = MedOriginNativePreview::default();
    app.open_embedded_fictional_bundle_demo().unwrap();

    let salt = generate_os_random_bytes::<16>().unwrap();
    let key = derive_workspace_key_argon2id(
        "secret-session-passphrase",
        &salt,
        fast_test_argon2_params(),
        VAULT_KEY_LABEL_V2,
    )
    .unwrap();
    let audit_key = derive_audit_mac_key(&key, &salt).unwrap();
    let mut test_buf = [0xAAu8; 32];
    zeroize_bytes(&mut test_buf);
    assert_eq!(test_buf, [0u8; 32]);

    app.connected.storage_passphrase = "secret-session-passphrase".to_string();
    app.connected.storage_salt = salt;
    app.connected.storage_key_fingerprint = Some(key_fingerprint_hex(&key));
    app.connected.storage_raw_key = Some(key);
    app.connected.audit_mac_key = Some(audit_key);
    app.connected.storage_vault_tag = Some("tag".to_string());
    app.connected.storage_backup_envelope = Some(vec![1, 2, 3, 4]);
    app.connected.storage_vault_locked = false;
    app.connected.note_attestation_receipt = Some("RECEIPT".to_string());
    app.connected.analytics_verified_receipt = Some("ANALYTICS".to_string());
    app.connected.quarantine_manifest_receipt = Some("QUARANTINE".to_string());

    app.clear_fictional_output();

    assert!(app.active_resources().is_empty());
    assert!(app.connected.storage_vault_locked);
    assert!(app.connected.storage_passphrase.is_empty());
    assert_eq!(app.connected.storage_salt, [0u8; 16]);
    assert!(app.connected.storage_raw_key.is_none());
    assert!(app.connected.audit_mac_key.is_none());
    assert!(app.connected.storage_key_fingerprint.is_none());
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

#[test]
fn test_literature_screening_import_dedupe_prisma_and_export() {
    let dir = temp_test_dir("lit-screen");
    let lit_file = dir.join("synthetic-lit.json");
    let export_file = dir.join("screening-export.json");

    // Negative controls on import
    assert_eq!(
        import_literature_records_json("not-json"),
        Err("LITERATURE_JSON_INVALID")
    );
    assert_eq!(
        import_literature_records_json("[]"),
        Err("LITERATURE_IMPORT_EMPTY_REFUSED")
    );
    assert_eq!(
        import_literature_records_json(r#"[{"source":"PubMed"}]"#),
        Err("LITERATURE_RECORD_MISSING_TITLE")
    );
    assert_eq!(
        import_literature_records_json(r#"[{"title":"Study A"}]"#),
        Err("LITERATURE_RECORD_MISSING_SOURCE")
    );
    assert_eq!(
        import_literature_records_json(r#"[{"title":"CONFIDENTIAL MRN:99","source":"local"}]"#),
        Err("LITERATURE_RECORD_PROHIBITED_MARKER_REFUSED")
    );

    // Valid local JSON file import with DOI duplicate, PMID duplicate, title duplicate, and unique records
    let sample = r#"{
        "records": [
            {"id":"lit-1","title":"Evidence Provenance in Synthetic FHIR Graphs","doi":"10.1000/SYN.001","pmid":"100001","year":2026,"source":"PubMed","license":"CC-BY-4.0"},
            {"id":"lit-2","title":"Duplicate by DOI with different case","doi":"10.1000/syn.001","year":2026,"source":"EuropePMC","license":"CC-BY-4.0"},
            {"id":"lit-3","title":"Deterministic PRISMA Screening Workflows","pmid":"200002","year":2025,"source":"PubMed","license":"CC0-1.0"},
            {"id":"lit-4","title":"Duplicate by PMID","pmid":"200002","year":2025,"source":"Crossref","license":"CC0-1.0"},
            {"id":"lit-5","title":"Deterministic PRISMA Screening Workflows!","year":2025,"source":"Manual","license":"CC-BY-4.0"},
            {"id":"lit-6","title":"Fail-Closed Abstention Benchmarks","doi":"10.1000/syn.003","year":2026,"source":"PubMed","license":"CC-BY-4.0"}
        ]
    }"#;
    atomic_write_local_file(&lit_file, sample.as_bytes(), false).unwrap();

    let mut records = load_literature_records_from_path(&lit_file).unwrap();
    assert_eq!(records.len(), 6);

    let removed = deduplicate_literature_records(&mut records);
    assert_eq!(removed, 3);
    assert_eq!(records[1].duplicate_of.as_deref(), Some("lit-1"));
    assert_eq!(records[1].stage, ScreeningStage::Excluded);
    assert_eq!(records[3].duplicate_of.as_deref(), Some("lit-3"));
    assert_eq!(records[4].duplicate_of.as_deref(), Some("lit-3"));

    // PRISMA state machine legal and illegal transitions + mandatory exclusion reason
    assert_eq!(
        advance_screening_stage(ScreeningStage::Deduped, ScreeningStage::Included, None),
        Err("ILLEGAL_PRISMA_STAGE_TRANSITION")
    );
    assert_eq!(
        advance_screening_stage(
            ScreeningStage::Deduped,
            ScreeningStage::Excluded,
            Some("   ")
        ),
        Err("EXCLUSION_REQUIRES_MANDATORY_REASON")
    );
    assert_eq!(
        advance_screening_stage(
            ScreeningStage::Deduped,
            ScreeningStage::Screened,
            Some("not allowed on non-excluded")
        ),
        Err("REASON_ONLY_PERMITTED_ON_EXCLUDED")
    );

    // Advance lit-1 -> Screened -> Eligibility -> Included
    for next in [
        ScreeningStage::Screened,
        ScreeningStage::Eligibility,
        ScreeningStage::Included,
    ] {
        let (st, reason) = advance_screening_stage(records[0].stage, next, None).unwrap();
        records[0].stage = st;
        records[0].exclusion_reason = reason;
    }
    // Exclude lit-6 with mandatory reason
    let (st, reason) = advance_screening_stage(
        records[5].stage,
        ScreeningStage::Excluded,
        Some("OUT_OF_SCOPE_NON_MEDICAL"),
    )
    .unwrap();
    records[5].stage = st;
    records[5].exclusion_reason = reason;
    // Excluded is terminal
    assert_eq!(
        advance_screening_stage(ScreeningStage::Excluded, ScreeningStage::Included, None),
        Err("ILLEGAL_PRISMA_STAGE_TRANSITION")
    );

    let counts = compute_prisma_counts(&records);
    assert_eq!(counts.identified, 6);
    assert_eq!(counts.duplicates_removed, 3);
    assert_eq!(counts.screened, 3);
    assert_eq!(counts.included, 1);
    assert_eq!(counts.excluded, 4);
    assert_eq!(counts.pending, 1);

    // Reproducible deterministic export + atomic disk write
    assert_eq!(
        export_literature_screening_json(&[]),
        Err("CANNOT_EXPORT_EMPTY_SCREENING_SET")
    );
    let export1 = export_literature_screening_json(&records).unwrap();
    let export2 = export_literature_screening_json(&records).unwrap();
    assert_eq!(export1, export2);
    assert!(export1.contains("medorigin-d2-literature-screening-export/v1"));
    assert!(export1.contains("OUT_OF_SCOPE_NON_MEDICAL"));
    atomic_write_local_file(&export_file, export1.as_bytes(), false).unwrap();
    assert_eq!(fs::read_to_string(&export_file).unwrap(), export1);

    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn test_research_explorer_committed_and_local_artifacts_filter_and_export() {
    let dir = temp_test_dir("research-exp");
    let local_ok = dir.join("local-cohort.json");
    let local_bad = dir.join("corrupt.json");
    let manifest_out = dir.join("research-manifest.json");

    let mut artifacts = load_committed_research_artifacts();
    assert_eq!(artifacts.len(), 6);
    assert!(
        artifacts
            .iter()
            .all(|a| a.sha256.len() == 64 && a.byte_len > 0)
    );

    // Load a local JSON artifact
    atomic_write_local_file(
        &local_ok,
        br#"{"schema":"synthetic-local-cohort/v1","resources":[{"id":"fictional-1"},{"id":"fictional-2"}]}"#,
        false,
    )
    .unwrap();
    let loaded = load_local_research_artifact_file(&local_ok).unwrap();
    assert_eq!(loaded.schema_or_type, "synthetic-local-cohort/v1");
    assert_eq!(loaded.item_count, 2);
    assert_eq!(loaded.origin, "local-file");
    artifacts.push(loaded);

    // Reject malformed local JSON
    atomic_write_local_file(&local_bad, b"{bad json", false).unwrap();
    assert_eq!(
        load_local_research_artifact_file(&local_bad),
        Err("RESEARCH_ARTIFACT_JSON_INVALID")
    );

    // Filter by schema / id / sha256
    assert_eq!(filter_research_artifacts(&artifacts, "").len(), 7);
    assert_eq!(
        filter_research_artifacts(&artifacts, "synthetic-local-cohort/v1").len(),
        1
    );
    assert_eq!(filter_research_artifacts(&artifacts, "bundle-48").len(), 1);
    assert_eq!(
        filter_research_artifacts(&artifacts, "does-not-exist").len(),
        0
    );

    // Export deterministic manifest
    assert_eq!(
        export_research_manifest_json(&[]),
        Err("CANNOT_EXPORT_EMPTY_RESEARCH_MANIFEST")
    );
    let manifest = export_research_manifest_json(&artifacts).unwrap();
    assert!(manifest.contains("medorigin-d2-research-manifest/v1"));
    assert!(manifest.contains("SCIENTIFIC_NOT_QUALIFIED"));
    atomic_write_local_file(&manifest_out, manifest.as_bytes(), false).unwrap();
    assert_eq!(fs::read_to_string(&manifest_out).unwrap(), manifest);

    let _ = fs::remove_dir_all(&dir);
}

#[test]
fn test_executable_local_benchmark_and_external_receipt_verifier() {
    // 1. Real executable local deterministic structural benchmark
    let run = run_local_structural_benchmark();
    assert_eq!(run.numerator, 5);
    assert_eq!(run.denominator, 5);
    assert_eq!(run.cases.len(), 5);
    assert!(run.cases.iter().all(|c| c.passed));
    assert_eq!(run.dataset_sha256.len(), 64);
    assert_eq!(run.receipt_sha256.len(), 64);
    assert_eq!(run.scientific_qualification, "SCIENTIFIC_NOT_QUALIFIED");
    assert!(!run.platform.is_empty());
    assert!(!run.execution_command.is_empty());
    assert!(!run.limitations.is_empty());

    // 2. External benchmark receipt verifier (valid receipt)
    let ds_sha = "a".repeat(64);
    let expected_receipt_sha = sha256_hex(
        format!(
            "synthetic-medqa-mini|{ds_sha}|qwen-0.5b-local|t4-16gb|uv run pytest tests/eval|42/50"
        )
        .as_bytes(),
    );
    let valid_json = format!(
        r#"{{
            "schema": "medorigin-bench-result-receipt/v1",
            "scientific_qualified": false,
            "dataset_id": "synthetic-medqa-mini",
            "dataset_sha256": "{ds_sha}",
            "model_id": "qwen-0.5b-local",
            "hardware": "t4-16gb",
            "command": "uv run pytest tests/eval",
            "numerator": 42,
            "denominator": 50,
            "receipt_sha256": "{expected_receipt_sha}"
        }}"#
    );
    let verified = verify_external_benchmark_receipt_json(&valid_json).unwrap();
    assert_eq!(verified.numerator, 42);
    assert_eq!(verified.denominator, 50);

    // 3. Negative controls: forged scientific_qualified: true, zero denominator, numerator > denominator, digest mismatch
    let forged_qualified = valid_json.replace(
        r#""scientific_qualified": false"#,
        r#""scientific_qualified": true"#,
    );
    assert_eq!(
        verify_external_benchmark_receipt_json(&forged_qualified),
        Err("UNAUTHORIZED_SCIENTIFIC_QUALIFICATION_CLAIM_REFUSED")
    );

    let zero_denom = valid_json.replace(r#""denominator": 50"#, r#""denominator": 0"#);
    assert_eq!(
        verify_external_benchmark_receipt_json(&zero_denom),
        Err("BENCHMARK_RECEIPT_INVALID_DENOMINATOR")
    );

    let bad_ratio = valid_json.replace(r#""numerator": 42"#, r#""numerator": 51"#);
    assert_eq!(
        verify_external_benchmark_receipt_json(&bad_ratio),
        Err("BENCHMARK_RECEIPT_NUMERATOR_EXCEEDS_DENOMINATOR")
    );

    let bad_digest = valid_json.replace(&expected_receipt_sha, &"0".repeat(64));
    assert_eq!(
        verify_external_benchmark_receipt_json(&bad_digest),
        Err("BENCHMARK_RECEIPT_DIGEST_MISMATCH")
    );
}

#[test]
fn test_offline_fhir_interop_validator_and_negative_controls() {
    let mut app = MedOriginNativePreview::default();

    // Endpoint 0 refuses empty bundle
    assert_eq!(
        execute_offline_fhir_interop_check(0, &app.active_resources(), ""),
        Err("INTEROP_NO_SYNTHETIC_BUNDLE_ADMITTED")
    );

    // Endpoint 0 passes on valid 8-resource synthetic bundle
    app.open_embedded_fictional_bundle_demo().unwrap();
    let ep0 = execute_offline_fhir_interop_check(0, &app.active_resources(), "").unwrap();
    assert_eq!(ep0.endpoint_id, "local-synthetic-fhir-validator");
    assert_eq!(ep0.resources_checked, 8);
    assert_eq!(ep0.outcome_sha256.len(), 64);

    // Endpoint 1 validates valid offline read-only FHIR Patient JSON
    let ok_payload = r#"{"resourceType":"Patient","id":"fictional-pat-interop-1","method":"GET"}"#;
    let ep1 = execute_offline_fhir_interop_check(1, &app.active_resources(), ok_payload).unwrap();
    assert_eq!(ep1.status, "OPERATION_OUTCOME_READONLY_ADMITTED");
    assert_eq!(ep1.resources_checked, 1);

    // Endpoint 1 negative controls
    assert_eq!(
        execute_offline_fhir_interop_check(1, &app.active_resources(), "   "),
        Err("INTEROP_EMPTY_PAYLOAD_REFUSED")
    );
    assert_eq!(
        execute_offline_fhir_interop_check(1, &app.active_resources(), "{malformed"),
        Err("INTEROP_MALFORMED_JSON_REFUSED")
    );
    assert_eq!(
        execute_offline_fhir_interop_check(
            1,
            &app.active_resources(),
            r#"{"resourceType":"Patient","method":"POST"}"#
        ),
        Err("INTEROP_WRITE_VERB_REFUSED")
    );
    assert_eq!(
        execute_offline_fhir_interop_check(
            1,
            &app.active_resources(),
            r#"{"resourceType":"Patient","url":"https://ehr.hospital.example/fhir"}"#
        ),
        Err("INTEROP_EXTERNAL_URL_EGRESS_REFUSED")
    );
    assert_eq!(
        execute_offline_fhir_interop_check(
            1,
            &app.active_resources(),
            r#"{"resourceType":"MedicationRequest"}"#
        ),
        Err("INTEROP_UNSUPPORTED_RESOURCE_TYPE")
    );

    // Endpoint 2 permanently blocks live EHR writes
    assert_eq!(
        execute_offline_fhir_interop_check(2, &app.active_resources(), ok_payload),
        Err("SECURITY_REFUSAL_EHR_WRITE_BLOCKED")
    );

    // Unknown endpoint refused
    assert_eq!(
        execute_offline_fhir_interop_check(99, &app.active_resources(), ok_payload),
        Err("INTEROP_UNSUPPORTED_ENDPOINT_REFUSED")
    );
}

#[test]
fn test_symlink_and_junction_paths_refused_fail_closed() {
    let dir = temp_test_dir("reparse-guard");
    let real_target_dir = dir.join("real-target");
    fs::create_dir_all(&real_target_dir).unwrap();
    let link_dir = dir.join("linked-dir");

    #[cfg(windows)]
    {
        let status = std::process::Command::new("cmd")
            .args([
                "/C",
                "mklink",
                "/J",
                &link_dir.to_string_lossy(),
                &real_target_dir.to_string_lossy(),
            ])
            .status()
            .expect("invoke mklink /J for directory junction test");
        assert!(
            status.success(),
            "mklink /J must succeed on local NTFS temp dir"
        );
    }

    #[cfg(unix)]
    {
        std::os::unix::fs::symlink(&real_target_dir, &link_dir)
            .expect("create unix symlink for guard test");
    }

    // Both the junction/symlink itself and any file beneath it must be refused fail-closed
    let valid_env = encrypt_envelope_v2(
        "junction-guard-test-passphrase-2026!",
        fast_test_argon2_params(),
        b"synthetic-junction-guard-payload",
    )
    .unwrap();
    let real_existing = real_target_dir.join("existing.mswsenv");
    save_encrypted_backup_to_path(&real_existing, &valid_env, false).unwrap();
    let nested_file = link_dir.join("vault-backup.mswsenv");
    let nested_existing = link_dir.join("existing.mswsenv");
    assert_eq!(
        validate_local_regular_path(&link_dir, false),
        Err("SYMLINK_OR_NON_FILE_REFUSED")
    );
    assert_eq!(
        validate_local_regular_path(&nested_file, false),
        Err("SYMLINK_OR_REPARSE_ANCESTOR_REFUSED")
    );
    assert_eq!(
        save_encrypted_backup_to_path(&nested_file, &valid_env, false),
        Err("SYMLINK_OR_REPARSE_ANCESTOR_REFUSED")
    );
    assert_eq!(
        load_encrypted_backup_from_path(&nested_existing),
        Err("SYMLINK_OR_REPARSE_ANCESTOR_REFUSED")
    );

    // Cleanup junction cleanly before removing temp dir
    #[cfg(windows)]
    {
        let _ = fs::remove_dir(&link_dir);
    }
    #[cfg(unix)]
    {
        let _ = fs::remove_file(&link_dir);
    }
    let _ = fs::remove_dir_all(&dir);
}
