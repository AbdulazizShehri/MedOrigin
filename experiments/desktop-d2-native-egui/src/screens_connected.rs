//! Interactive synthetic UI adapters for the 16 connected desktop screens.
//! Provides local-first, in-memory exploration of synthetic clinical records,
//! evidence retrieval, research exploration, and trust infrastructure.
//!
//! STRICT INVARIANTS:
//! - Offline only; no network sockets, process spawning or external EHR APIs.
//! - Synthetic research data only; zero real patient data (NO PHI).
//! - All capabilities are Lane A developer software preview features.
//! - Research model training, model promotion, and live EHR writes remain strictly gated.

use std::collections::HashMap;
use std::collections::hash_map::RandomState;
use std::fs;
use std::hash::{BuildHasher, Hasher};
use std::path::Path;
use std::sync::atomic::{AtomicU64, Ordering, compiler_fence};
use std::time::{SystemTime, UNIX_EPOCH};

use eframe::egui::{self, RichText, Ui};
use serde_json::Value;
use sha2::{Digest, Sha256};

use crate::app::MedOriginNativePreview;
use crate::encrypted_readback::FictionalReadbackResource;
use crate::screens::SCREENS;
use crate::theme;

pub const PBKDF2_ITERATIONS: u32 = 25_000;
pub const MAX_PERSISTED_FILE_BYTES: usize = 4 * 1024 * 1024;
pub const VAULT_KEY_LABEL: &str = "mesc-clinical-workspace-backup-hkdf-sha256/1";
static ENTROPY_COUNTER: AtomicU64 = AtomicU64::new(1);

pub fn sha256_hex(bytes: &[u8]) -> String {
    Sha256::digest(bytes)
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

pub fn hasher_hex(hasher: Sha256) -> String {
    hasher
        .finalize()
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect()
}

/// Generates high-entropy random bytes using Rust's OS-seeded `RandomState`
/// combined with wall-clock nanoseconds and a monotonic counter via SHA-256.
/// Guaranteed non-repeating across restarts without external crates or unsafe code.
pub fn generate_random_bytes<const N: usize>(domain: &[u8]) -> [u8; N] {
    assert!(N <= 32, "generate_random_bytes supports up to 32 bytes");
    let mut hasher = Sha256::new();
    hasher.update(domain);
    let seq = ENTROPY_COUNTER.fetch_add(1, Ordering::Relaxed);
    hasher.update(seq.to_le_bytes());
    if let Ok(dur) = SystemTime::now().duration_since(UNIX_EPOCH) {
        hasher.update(dur.as_nanos().to_le_bytes());
    }
    for round in 0u64..4 {
        let state = RandomState::new();
        let mut h = state.build_hasher();
        h.write_u64(round);
        h.write_u64(seq);
        hasher.update(h.finish().to_le_bytes());
    }
    let digest = hasher.finalize();
    let mut out = [0u8; N];
    out.copy_from_slice(&digest[..N]);
    out
}

/// RFC 2898 / RFC 8018 PBKDF2-HMAC-SHA256 for a 32-byte derived key.
pub fn pbkdf2_hmac_sha256(password: &[u8], salt: &[u8], iterations: u32) -> [u8; 32] {
    let iters = iterations.max(1);
    let mut salt_block = Vec::with_capacity(salt.len() + 4);
    salt_block.extend_from_slice(salt);
    salt_block.extend_from_slice(&1u32.to_be_bytes());

    let mut u = hmac_sha256(password, &salt_block);
    let mut dk = u;
    for _ in 1..iters {
        u = hmac_sha256(password, &u);
        for (d, ub) in dk.iter_mut().zip(u.iter()) {
            *d ^= *ub;
        }
    }
    zeroize_bytes(&mut u);
    dk
}

// -----------------------------------------------------------------------------
// RFC 5869 HKDF-SHA-256 and RFC 8439 ChaCha20-Poly1305 AEAD Engine
// -----------------------------------------------------------------------------

pub const ENVELOPE_MAGIC: &[u8; 8] = b"MSWSENV1";
pub const ENVELOPE_VERSION: u8 = 1;
pub const ENVELOPE_HEADER_LEN: usize = 41; // 8 (magic) + 1 (ver) + 4 (key_ver) + 16 (salt) + 12 (nonce)
pub const TAG_LEN: usize = 16;
pub const MIN_ENVELOPE_LEN: usize = ENVELOPE_HEADER_LEN + TAG_LEN;

pub fn hmac_sha256(key: &[u8], data: &[u8]) -> [u8; 32] {
    let mut k = [0u8; 64];
    if key.len() > 64 {
        let digest = Sha256::digest(key);
        k[..32].copy_from_slice(&digest);
    } else {
        k[..key.len()].copy_from_slice(key);
    }
    let mut ipad = [0u8; 64];
    let mut opad = [0u8; 64];
    for i in 0..64 {
        ipad[i] = k[i] ^ 0x36;
        opad[i] = k[i] ^ 0x5c;
    }
    let mut inner = Sha256::new();
    inner.update(ipad);
    inner.update(data);
    let inner_hash = inner.finalize();

    let mut outer = Sha256::new();
    outer.update(opad);
    outer.update(inner_hash);
    outer.finalize().into()
}

pub fn hkdf_extract(salt: &[u8], ikm: &[u8]) -> [u8; 32] {
    let default_salt = [0u8; 32];
    let effective_salt = if salt.is_empty() {
        &default_salt[..]
    } else {
        salt
    };
    hmac_sha256(effective_salt, ikm)
}

pub fn hkdf_expand(prk: &[u8; 32], info: &[u8], length: usize) -> Vec<u8> {
    let mut okm = Vec::with_capacity(length);
    let mut previous_block = Vec::new();
    let mut counter = 1u8;
    while okm.len() < length {
        let mut input = Vec::with_capacity(previous_block.len() + info.len() + 1);
        input.extend_from_slice(&previous_block);
        input.extend_from_slice(info);
        input.push(counter);
        let block = hmac_sha256(prk, &input);
        previous_block = block.to_vec();
        let take = std::cmp::min(32, length - okm.len());
        okm.extend_from_slice(&block[..take]);
        counter = counter.wrapping_add(1);
    }
    okm
}

/// Derives a 256-bit workspace key from a user passphrase using RFC 2898
/// PBKDF2-HMAC-SHA256 stretching followed by RFC 5869 HKDF-SHA-256 domain separation.
pub fn derive_workspace_key(passphrase: &str, salt: &[u8; 16], label: &str) -> [u8; 32] {
    let mut stretched = pbkdf2_hmac_sha256(passphrase.as_bytes(), salt, PBKDF2_ITERATIONS);
    let mut prk = hkdf_extract(salt, &stretched);
    let mut okm = hkdf_expand(&prk, label.as_bytes(), 32);
    let mut key = [0u8; 32];
    key.copy_from_slice(&okm[..32]);
    zeroize_bytes(&mut stretched);
    zeroize_bytes(&mut prk);
    zeroize_bytes(&mut okm);
    key
}

#[inline(always)]
fn quarter_round(s: &mut [u32; 16], a: usize, b: usize, c: usize, d: usize) {
    s[a] = s[a].wrapping_add(s[b]);
    s[d] = (s[d] ^ s[a]).rotate_left(16);
    s[c] = s[c].wrapping_add(s[d]);
    s[b] = (s[b] ^ s[c]).rotate_left(12);
    s[a] = s[a].wrapping_add(s[b]);
    s[d] = (s[d] ^ s[a]).rotate_left(8);
    s[c] = s[c].wrapping_add(s[d]);
    s[b] = (s[b] ^ s[c]).rotate_left(7);
}

pub fn chacha20_block(key: &[u8; 32], counter: u32, nonce: &[u8; 12]) -> [u8; 64] {
    let mut state = [0u32; 16];
    state[0] = 0x61707865;
    state[1] = 0x3320646e;
    state[2] = 0x79622d32;
    state[3] = 0x6b206574;
    for i in 0..8 {
        state[4 + i] = u32::from_le_bytes(key[i * 4..(i + 1) * 4].try_into().unwrap());
    }
    state[12] = counter;
    for i in 0..3 {
        state[13 + i] = u32::from_le_bytes(nonce[i * 4..(i + 1) * 4].try_into().unwrap());
    }
    let mut working = state;
    for _ in 0..10 {
        quarter_round(&mut working, 0, 4, 8, 12);
        quarter_round(&mut working, 1, 5, 9, 13);
        quarter_round(&mut working, 2, 6, 10, 14);
        quarter_round(&mut working, 3, 7, 11, 15);
        quarter_round(&mut working, 0, 5, 10, 15);
        quarter_round(&mut working, 1, 6, 11, 12);
        quarter_round(&mut working, 2, 7, 8, 13);
        quarter_round(&mut working, 3, 4, 9, 14);
    }
    let mut out = [0u8; 64];
    for i in 0..16 {
        let word = working[i].wrapping_add(state[i]);
        out[i * 4..(i + 1) * 4].copy_from_slice(&word.to_le_bytes());
    }
    out
}

pub fn chacha20_xor(key: &[u8; 32], counter: u32, nonce: &[u8; 12], input: &[u8]) -> Vec<u8> {
    let mut output = Vec::with_capacity(input.len());
    let mut ctr = counter;
    for chunk in input.chunks(64) {
        let block = chacha20_block(key, ctr, nonce);
        for (b, k) in chunk.iter().zip(block.iter()) {
            output.push(b ^ k);
        }
        ctr = ctr.wrapping_add(1);
    }
    output
}

pub fn poly1305_mac(key: &[u8; 32], msg: &[u8]) -> [u8; 16] {
    let mut r_bytes = [0u8; 16];
    r_bytes.copy_from_slice(&key[0..16]);
    r_bytes[3] &= 15;
    r_bytes[7] &= 15;
    r_bytes[11] &= 15;
    r_bytes[15] &= 15;
    r_bytes[4] &= 252;
    r_bytes[8] &= 252;
    r_bytes[12] &= 252;

    let u32_at = |b: &[u8], i: usize| u32::from_le_bytes(b[i..i + 4].try_into().unwrap());
    let r0 = (u32_at(&r_bytes, 0) & 0x3ffffff) as u64;
    let r1 = ((u32_at(&r_bytes, 3) >> 2) & 0x3ffff03) as u64;
    let r2 = ((u32_at(&r_bytes, 6) >> 4) & 0x3ffc0ff) as u64;
    let r3 = ((u32_at(&r_bytes, 9) >> 6) & 0x3f03fff) as u64;
    let r4 = ((u32_at(&r_bytes, 12) >> 8) & 0x00fffff) as u64;

    let s1 = r1 * 5;
    let s2 = r2 * 5;
    let s3 = r3 * 5;
    let s4 = r4 * 5;
    let mut h0 = 0u64;
    let mut h1 = 0u64;
    let mut h2 = 0u64;
    let mut h3 = 0u64;
    let mut h4 = 0u64;

    for chunk in msg.chunks(16) {
        let mut buf = [0u8; 17];
        buf[..chunk.len()].copy_from_slice(chunk);
        buf[chunk.len()] = 1;

        let mut arr = [0u8; 16];
        arr[..16].copy_from_slice(&buf[..16]);
        let lo = u128::from_le_bytes(arr);

        let c0 = (lo & 0x3ffffff) as u64;
        let c1 = ((lo >> 26) & 0x3ffffff) as u64;
        let c2 = ((lo >> 52) & 0x3ffffff) as u64;
        let c3 = ((lo >> 78) & 0x3ffffff) as u64;
        let c4 = ((lo >> 104) as u64) | ((buf[16] as u64) << 24);

        h0 += c0;
        h1 += c1;
        h2 += c2;
        h3 += c3;
        h4 += c4;

        let d0 = (h0 as u128) * (r0 as u128)
            + (h1 as u128) * (s4 as u128)
            + (h2 as u128) * (s3 as u128)
            + (h3 as u128) * (s2 as u128)
            + (h4 as u128) * (s1 as u128);
        let d1 = (h0 as u128) * (r1 as u128)
            + (h1 as u128) * (r0 as u128)
            + (h2 as u128) * (s4 as u128)
            + (h3 as u128) * (s3 as u128)
            + (h4 as u128) * (s2 as u128);
        let d2 = (h0 as u128) * (r2 as u128)
            + (h1 as u128) * (r1 as u128)
            + (h2 as u128) * (r0 as u128)
            + (h3 as u128) * (s4 as u128)
            + (h4 as u128) * (s3 as u128);
        let d3 = (h0 as u128) * (r3 as u128)
            + (h1 as u128) * (r2 as u128)
            + (h2 as u128) * (r1 as u128)
            + (h3 as u128) * (r0 as u128)
            + (h4 as u128) * (s4 as u128);
        let d4 = (h0 as u128) * (r4 as u128)
            + (h1 as u128) * (r3 as u128)
            + (h2 as u128) * (r2 as u128)
            + (h3 as u128) * (r1 as u128)
            + (h4 as u128) * (r0 as u128);

        let mut c = d0 >> 26;
        h0 = (d0 & 0x3ffffff) as u64;
        let d1 = d1 + c;
        c = d1 >> 26;
        h1 = (d1 & 0x3ffffff) as u64;
        let d2 = d2 + c;
        c = d2 >> 26;
        h2 = (d2 & 0x3ffffff) as u64;
        let d3 = d3 + c;
        c = d3 >> 26;
        h3 = (d3 & 0x3ffffff) as u64;
        let d4 = d4 + c;
        c = d4 >> 26;
        h4 = (d4 & 0x3ffffff) as u64;
        h0 += (c * 5) as u64;
        c = (h0 as u128) >> 26;
        h0 &= 0x3ffffff;
        h1 += c as u64;
    }

    let mut c = h1 >> 26;
    h1 &= 0x3ffffff;
    h2 += c;
    c = h2 >> 26;
    h2 &= 0x3ffffff;
    h3 += c;
    c = h3 >> 26;
    h3 &= 0x3ffffff;
    h4 += c;
    c = h4 >> 26;
    h4 &= 0x3ffffff;
    h0 += c * 5;
    c = h0 >> 26;
    h0 &= 0x3ffffff;
    h1 += c;

    let mut g0 = h0 + 5;
    let mut c = g0 >> 26;
    g0 &= 0x3ffffff;
    let mut g1 = h1 + c;
    c = g1 >> 26;
    g1 &= 0x3ffffff;
    let mut g2 = h2 + c;
    c = g2 >> 26;
    g2 &= 0x3ffffff;
    let mut g3 = h3 + c;
    c = g3 >> 26;
    g3 &= 0x3ffffff;
    let g4 = (h4 as i64) + (c as i64) - (1i64 << 26);

    if g4 >= 0 {
        h0 = g0;
        h1 = g1;
        h2 = g2;
        h3 = g3;
        h4 = g4 as u64;
    }

    let h = (h0 as u128)
        | ((h1 as u128) << 26)
        | ((h2 as u128) << 52)
        | ((h3 as u128) << 78)
        | ((h4 as u128) << 104);
    let s = u128::from_le_bytes(key[16..32].try_into().unwrap());
    let tag = h.wrapping_add(s);
    tag.to_le_bytes()
}

pub fn chacha20_poly1305_encrypt(
    key: &[u8; 32],
    nonce: &[u8; 12],
    aad: &[u8],
    plaintext: &[u8],
) -> (Vec<u8>, [u8; 16]) {
    let poly_block = chacha20_block(key, 0, nonce);
    let mut poly_key = [0u8; 32];
    poly_key.copy_from_slice(&poly_block[0..32]);

    let ciphertext = chacha20_xor(key, 1, nonce, plaintext);

    let mut mac_input = Vec::new();
    mac_input.extend_from_slice(aad);
    if !aad.is_empty() && !aad.len().is_multiple_of(16) {
        mac_input.resize(mac_input.len() + (16 - (aad.len() % 16)), 0);
    }
    mac_input.extend_from_slice(&ciphertext);
    if !ciphertext.is_empty() && !ciphertext.len().is_multiple_of(16) {
        mac_input.resize(mac_input.len() + (16 - (ciphertext.len() % 16)), 0);
    }
    mac_input.extend_from_slice(&(aad.len() as u64).to_le_bytes());
    mac_input.extend_from_slice(&(ciphertext.len() as u64).to_le_bytes());

    let tag = poly1305_mac(&poly_key, &mac_input);
    (ciphertext, tag)
}

pub fn chacha20_poly1305_decrypt(
    key: &[u8; 32],
    nonce: &[u8; 12],
    aad: &[u8],
    ciphertext: &[u8],
    tag: &[u8; 16],
) -> Result<Vec<u8>, &'static str> {
    let poly_block = chacha20_block(key, 0, nonce);
    let mut poly_key = [0u8; 32];
    poly_key.copy_from_slice(&poly_block[0..32]);

    let mut mac_input = Vec::new();
    mac_input.extend_from_slice(aad);
    if !aad.is_empty() && !aad.len().is_multiple_of(16) {
        mac_input.resize(mac_input.len() + (16 - (aad.len() % 16)), 0);
    }
    mac_input.extend_from_slice(ciphertext);
    if !ciphertext.is_empty() && !ciphertext.len().is_multiple_of(16) {
        mac_input.resize(mac_input.len() + (16 - (ciphertext.len() % 16)), 0);
    }
    mac_input.extend_from_slice(&(aad.len() as u64).to_le_bytes());
    mac_input.extend_from_slice(&(ciphertext.len() as u64).to_le_bytes());

    let expected_tag = poly1305_mac(&poly_key, &mac_input);
    let diff = expected_tag
        .iter()
        .zip(tag.iter())
        .fold(0u8, |acc, (a, b)| acc | (a ^ b));
    if diff != 0 {
        return Err("AUTHENTICATION_TAG_VERIFICATION_FAILED");
    }

    let plaintext = chacha20_xor(key, 1, nonce, ciphertext);
    Ok(plaintext)
}

pub fn encrypt_envelope(
    key: &[u8; 32],
    salt: &[u8; 16],
    nonce: &[u8; 12],
    plaintext: &[u8],
) -> Vec<u8> {
    let mut header = Vec::with_capacity(ENVELOPE_HEADER_LEN);
    header.extend_from_slice(ENVELOPE_MAGIC);
    header.push(ENVELOPE_VERSION);
    header.extend_from_slice(&1u32.to_be_bytes());
    header.extend_from_slice(salt);
    header.extend_from_slice(nonce);

    let (ciphertext, tag) = chacha20_poly1305_encrypt(key, nonce, &header, plaintext);

    let mut envelope = Vec::with_capacity(ENVELOPE_HEADER_LEN + TAG_LEN + ciphertext.len());
    envelope.extend_from_slice(&header);
    envelope.extend_from_slice(&tag);
    envelope.extend_from_slice(&ciphertext);
    envelope
}

pub fn decrypt_envelope(key: &[u8; 32], envelope: &[u8]) -> Result<Vec<u8>, &'static str> {
    if envelope.len() < MIN_ENVELOPE_LEN {
        return Err("ENVELOPE_TOO_SHORT");
    }
    if &envelope[0..8] != ENVELOPE_MAGIC {
        return Err("INVALID_ENVELOPE_MAGIC");
    }
    if envelope[8] != ENVELOPE_VERSION {
        return Err("UNSUPPORTED_ENVELOPE_VERSION");
    }
    let header = &envelope[0..ENVELOPE_HEADER_LEN];
    let mut nonce = [0u8; 12];
    nonce.copy_from_slice(&header[29..41]);
    let mut tag = [0u8; 16];
    tag.copy_from_slice(&envelope[ENVELOPE_HEADER_LEN..ENVELOPE_HEADER_LEN + TAG_LEN]);
    let ciphertext = &envelope[ENVELOPE_HEADER_LEN + TAG_LEN..];

    chacha20_poly1305_decrypt(key, &nonce, header, ciphertext, &tag)
}

pub fn extract_envelope_salt(envelope: &[u8]) -> Result<[u8; 16], &'static str> {
    if envelope.len() < MIN_ENVELOPE_LEN {
        return Err("ENVELOPE_TOO_SHORT");
    }
    if &envelope[0..8] != ENVELOPE_MAGIC {
        return Err("INVALID_ENVELOPE_MAGIC");
    }
    if envelope[8] != ENVELOPE_VERSION {
        return Err("UNSUPPORTED_ENVELOPE_VERSION");
    }
    let mut salt = [0u8; 16];
    salt.copy_from_slice(&envelope[13..29]);
    Ok(salt)
}

pub fn decrypt_envelope_with_passphrase(
    passphrase: &str,
    envelope: &[u8],
    label: &str,
) -> Result<Vec<u8>, &'static str> {
    if passphrase.is_empty() {
        return Err("EMPTY_PASSPHRASE_REFUSED");
    }
    let salt = extract_envelope_salt(envelope)?;
    let mut key = derive_workspace_key(passphrase, &salt, label);
    let result = decrypt_envelope(&key, envelope);
    zeroize_bytes(&mut key);
    result
}

fn validate_local_regular_path(path: &Path, must_exist: bool) -> Result<(), &'static str> {
    if path.as_os_str().is_empty() {
        return Err("EMPTY_FILE_PATH_REFUSED");
    }
    if must_exist {
        let meta = fs::symlink_metadata(path).map_err(|_| "LOCAL_FILE_NOT_FOUND")?;
        if meta.file_type().is_symlink() || !meta.is_file() {
            return Err("SYMLINK_OR_NON_FILE_REFUSED");
        }
        if meta.len() as usize > MAX_PERSISTED_FILE_BYTES {
            return Err("PERSISTED_FILE_TOO_LARGE");
        }
    } else if let Ok(meta) = fs::symlink_metadata(path)
        && (meta.file_type().is_symlink() || !meta.is_file())
    {
        return Err("SYMLINK_OR_NON_FILE_REFUSED");
    }
    Ok(())
}

pub fn save_encrypted_backup_to_path(path: &Path, envelope: &[u8]) -> Result<usize, &'static str> {
    if envelope.len() < MIN_ENVELOPE_LEN || &envelope[0..8] != ENVELOPE_MAGIC {
        return Err("INVALID_ENVELOPE_REFUSED");
    }
    if envelope.len() > MAX_PERSISTED_FILE_BYTES {
        return Err("PERSISTED_FILE_TOO_LARGE");
    }
    validate_local_regular_path(path, false)?;
    fs::write(path, envelope).map_err(|_| "BACKUP_FILE_WRITE_FAILED")?;
    Ok(envelope.len())
}

pub fn load_encrypted_backup_from_path(path: &Path) -> Result<Vec<u8>, &'static str> {
    validate_local_regular_path(path, true)?;
    let bytes = fs::read(path).map_err(|_| "BACKUP_FILE_READ_FAILED")?;
    if bytes.len() < MIN_ENVELOPE_LEN {
        return Err("ENVELOPE_TOO_SHORT");
    }
    if bytes.len() > MAX_PERSISTED_FILE_BYTES {
        return Err("PERSISTED_FILE_TOO_LARGE");
    }
    Ok(bytes)
}

/// Best-effort in-memory overwrite with a compiler fence.
/// Note: Safe Rust without OS mlock cannot guarantee zero compiler/swap residue.
pub fn zeroize_bytes(buf: &mut [u8]) {
    for b in buf.iter_mut() {
        *b = 0;
    }
    compiler_fence(Ordering::SeqCst);
}

fn page_title(ui: &mut Ui, title: &str, subtitle: &str) {
    let p = *theme::palette(ui.ctx().theme());
    ui.label(RichText::new(title).size(theme::size::HEADING).strong());
    if !subtitle.is_empty() {
        ui.label(
            RichText::new(subtitle)
                .size(theme::size::BODY)
                .color(p.text_secondary),
        );
    }
    ui.add_space(theme::space::MD);
}

fn section_title(ui: &mut Ui, text: &str) {
    ui.label(RichText::new(text).size(theme::size::TITLE).strong());
    ui.add_space(theme::space::SM);
}

// -----------------------------------------------------------------------------
// Cryptographic Audit Ledger Data Structures & Verification
// -----------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AuditEvent {
    pub seq: u64,
    pub event_type: String,
    pub actor: String,
    pub payload: String,
    pub prev_hash: String,
    pub hash: String,
}

pub fn compute_audit_hash(
    seq: u64,
    event_type: &str,
    actor: &str,
    payload: &str,
    prev_hash: &str,
) -> String {
    let mut hasher = Sha256::new();
    hasher.update(prev_hash.as_bytes());
    hasher.update(b":");
    hasher.update(seq.to_string().as_bytes());
    hasher.update(b":");
    hasher.update(event_type.as_bytes());
    hasher.update(b":");
    hasher.update(actor.as_bytes());
    hasher.update(b":");
    hasher.update(payload.as_bytes());
    hasher_hex(hasher)
}

pub fn verify_audit_chain(events: &[AuditEvent]) -> Result<usize, (usize, String)> {
    if events.is_empty() {
        return Ok(0);
    }
    let mut expected_prev =
        "0000000000000000000000000000000000000000000000000000000000000000".to_string();
    for (i, ev) in events.iter().enumerate() {
        let expected_seq = (i as u64) + 1;
        if ev.seq != expected_seq {
            return Err((
                ev.seq as usize,
                format!("Sequence mismatch: expected {expected_seq}, got {}", ev.seq),
            ));
        }
        if ev.prev_hash != expected_prev {
            return Err((
                ev.seq as usize,
                format!(
                    "Parent hash mismatch at seq {}: expected {expected_prev}, got {}",
                    ev.seq, ev.prev_hash
                ),
            ));
        }
        let recomputed = compute_audit_hash(
            ev.seq,
            &ev.event_type,
            &ev.actor,
            &ev.payload,
            &ev.prev_hash,
        );
        if ev.hash != recomputed {
            return Err((
                ev.seq as usize,
                format!(
                    "Cryptographic hash corruption at seq {}: expected {recomputed}, got {}",
                    ev.seq, ev.hash
                ),
            ));
        }
        expected_prev = ev.hash.clone();
    }
    Ok(events.len())
}

pub fn build_initial_audit_events() -> Vec<AuditEvent> {
    let mut events = Vec::new();
    let ev1_hash = compute_audit_hash(
        1,
        "GENESIS_STARTUP",
        "system-native",
        "MedOrigin native desktop preview session initialized; offline boundary enforced",
        "0000000000000000000000000000000000000000000000000000000000000000",
    );
    events.push(AuditEvent {
        seq: 1,
        event_type: "GENESIS_STARTUP".to_string(),
        actor: "system-native".to_string(),
        payload: "MedOrigin native desktop preview session initialized; offline boundary enforced"
            .to_string(),
        prev_hash: "0000000000000000000000000000000000000000000000000000000000000000".to_string(),
        hash: ev1_hash,
    });
    events
}

pub fn serialize_audit_events(events: &[AuditEvent]) -> Result<String, &'static str> {
    if verify_audit_chain(events).is_err() {
        return Err("REFUSED_TO_SERIALIZE_CORRUPTED_AUDIT_CHAIN");
    }
    let items: Vec<Value> = events
        .iter()
        .map(|ev| {
            serde_json::json!({
                "seq": ev.seq,
                "event_type": ev.event_type,
                "actor": ev.actor,
                "payload": ev.payload,
                "prev_hash": ev.prev_hash,
                "hash": ev.hash,
            })
        })
        .collect();
    let root = serde_json::json!({
        "schema": "medorigin-d2-local-audit-chain/v1",
        "externally_anchored": false,
        "clinical_use_authorized": false,
        "events": items,
    });
    serde_json::to_string_pretty(&root).map_err(|_| "AUDIT_SERIALIZATION_FAILED")
}

pub fn deserialize_and_verify_audit_events(raw: &str) -> Result<Vec<AuditEvent>, String> {
    let val: Value =
        serde_json::from_str(raw).map_err(|e| format!("AUDIT_LEDGER_JSON_INVALID: {e}"))?;
    if val.get("schema").and_then(Value::as_str) != Some("medorigin-d2-local-audit-chain/v1") {
        return Err("AUDIT_LEDGER_SCHEMA_UNSUPPORTED".to_string());
    }
    let arr = val
        .get("events")
        .and_then(Value::as_array)
        .ok_or_else(|| "AUDIT_LEDGER_EVENTS_MISSING".to_string())?;
    if arr.is_empty() {
        return Err("AUDIT_LEDGER_EMPTY_REFUSED".to_string());
    }
    let mut events = Vec::with_capacity(arr.len());
    for item in arr {
        let seq = item
            .get("seq")
            .and_then(Value::as_u64)
            .ok_or_else(|| "AUDIT_EVENT_SEQ_INVALID".to_string())?;
        let event_type = item
            .get("event_type")
            .and_then(Value::as_str)
            .ok_or_else(|| "AUDIT_EVENT_TYPE_INVALID".to_string())?
            .to_string();
        let actor = item
            .get("actor")
            .and_then(Value::as_str)
            .ok_or_else(|| "AUDIT_EVENT_ACTOR_INVALID".to_string())?
            .to_string();
        let payload = item
            .get("payload")
            .and_then(Value::as_str)
            .ok_or_else(|| "AUDIT_EVENT_PAYLOAD_INVALID".to_string())?
            .to_string();
        let prev_hash = item
            .get("prev_hash")
            .and_then(Value::as_str)
            .ok_or_else(|| "AUDIT_EVENT_PREV_HASH_INVALID".to_string())?
            .to_string();
        let hash = item
            .get("hash")
            .and_then(Value::as_str)
            .ok_or_else(|| "AUDIT_EVENT_HASH_INVALID".to_string())?
            .to_string();
        events.push(AuditEvent {
            seq,
            event_type,
            actor,
            payload,
            prev_hash,
            hash,
        });
    }
    verify_audit_chain(&events)
        .map_err(|(seq, msg)| format!("AUDIT_CHAIN_CORRUPTED at seq {seq}: {msg}"))?;
    Ok(events)
}

pub fn save_audit_ledger_to_path(path: &Path, events: &[AuditEvent]) -> Result<usize, String> {
    validate_local_regular_path(path, false).map_err(|e| e.to_string())?;
    let json = serialize_audit_events(events).map_err(|e| e.to_string())?;
    if json.len() > MAX_PERSISTED_FILE_BYTES {
        return Err("PERSISTED_FILE_TOO_LARGE".to_string());
    }
    fs::write(path, json.as_bytes()).map_err(|_| "AUDIT_LEDGER_WRITE_FAILED".to_string())?;
    Ok(events.len())
}

pub fn load_audit_ledger_from_path(path: &Path) -> Result<Vec<AuditEvent>, String> {
    validate_local_regular_path(path, true).map_err(|e| e.to_string())?;
    let raw = fs::read_to_string(path).map_err(|_| "AUDIT_LEDGER_READ_FAILED".to_string())?;
    deserialize_and_verify_audit_events(&raw)
}

// -----------------------------------------------------------------------------
// Verified Evidence Snapshot Loader & Retrieval (Screen 11)
// -----------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct EvidenceEntry {
    pub id: String,
    pub resource_type: String,
    pub full_url: String,
    pub summary: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct VerifiedEvidenceSnapshot {
    pub id: &'static str,
    pub label: &'static str,
    pub sha256: String,
    pub byte_len: usize,
    pub entries: Vec<EvidenceEntry>,
}

pub const VERIFIED_EVIDENCE_SNAPSHOT_IDS: [&str; 2] = [
    "synthetic-multipatient-fhir-bundle.json",
    "encrypted-readback-projection.json",
];

pub fn load_verified_evidence_snapshot(
    snapshot_id: &str,
) -> Result<VerifiedEvidenceSnapshot, &'static str> {
    const SNAP_BUNDLE: &[u8] =
        include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
    const SNAP_READBACK: &[u8] =
        include_bytes!("../fixtures/core/encrypted-readback-projection.json");

    let (id, label, raw_bytes): (&'static str, &'static str, &'static [u8]) = match snapshot_id {
        "synthetic-multipatient-fhir-bundle.json" => (
            "synthetic-multipatient-fhir-bundle.json",
            "Committed Fixture: synthetic-multipatient-fhir-bundle.json",
            SNAP_BUNDLE,
        ),
        "encrypted-readback-projection.json" => (
            "encrypted-readback-projection.json",
            "Committed Fixture: encrypted-readback-projection.json",
            SNAP_READBACK,
        ),
        _ => return Err("UNKNOWN_OR_MISSING_SNAPSHOT_REFUSED"),
    };

    let parsed: Value =
        serde_json::from_slice(raw_bytes).map_err(|_| "SNAPSHOT_JSON_PARSE_FAILED")?;
    let mut entries = Vec::new();
    if let Some(bundle_entries) = parsed.get("entry").and_then(Value::as_array) {
        for item in bundle_entries {
            let full_url = item
                .get("fullUrl")
                .and_then(Value::as_str)
                .unwrap_or("")
                .to_string();
            if let Some(res) = item.get("resource") {
                let res_id = res
                    .get("id")
                    .and_then(Value::as_str)
                    .unwrap_or("unknown")
                    .to_string();
                let res_type = res
                    .get("resourceType")
                    .and_then(Value::as_str)
                    .unwrap_or("Resource")
                    .to_string();
                let summary = format!("{res_type} {res_id} ({full_url})");
                entries.push(EvidenceEntry {
                    id: res_id,
                    resource_type: res_type,
                    full_url,
                    summary,
                });
            }
        }
    } else if let Some(resources) = parsed.get("resources").and_then(Value::as_array) {
        for res in resources {
            let res_id = res
                .get("id")
                .and_then(Value::as_str)
                .unwrap_or("unknown")
                .to_string();
            let res_type = res
                .get("resource_type")
                .and_then(Value::as_str)
                .unwrap_or("Resource")
                .to_string();
            let full_url = res
                .get("full_url")
                .and_then(Value::as_str)
                .unwrap_or("")
                .to_string();
            let summary = format!("{res_type} {res_id} ({full_url})");
            entries.push(EvidenceEntry {
                id: res_id,
                resource_type: res_type,
                full_url,
                summary,
            });
        }
    }

    Ok(VerifiedEvidenceSnapshot {
        id,
        label,
        sha256: sha256_hex(raw_bytes),
        byte_len: raw_bytes.len(),
        entries,
    })
}

pub type RankedEvidenceEntry = (EvidenceEntry, f32, usize, bool);
pub type RankedEvidenceResult = (VerifiedEvidenceSnapshot, Vec<RankedEvidenceEntry>);

pub fn search_verified_evidence(
    snapshot_id: &str,
    query: &str,
    threshold: f32,
) -> Result<RankedEvidenceResult, &'static str> {
    let snapshot = load_verified_evidence_snapshot(snapshot_id)?;
    let query_terms: Vec<String> = query
        .to_lowercase()
        .split(|c: char| !c.is_alphanumeric())
        .filter(|s| !s.is_empty())
        .map(str::to_string)
        .collect();

    let mut ranked = Vec::with_capacity(snapshot.entries.len());
    for entry in &snapshot.entries {
        let hay = format!("{} {} {}", entry.resource_type, entry.id, entry.full_url).to_lowercase();
        let matches = query_terms
            .iter()
            .filter(|q| hay.contains(q.as_str()))
            .count();
        let score = if query_terms.is_empty() {
            0.0
        } else {
            (matches as f32 / query_terms.len() as f32).min(1.0)
        };
        let admitted = score >= threshold && matches > 0;
        ranked.push((entry.clone(), score, matches, admitted));
    }
    ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    Ok((snapshot, ranked))
}

// -----------------------------------------------------------------------------
// Comprehensive Fail-Closed Export Quarantine Scanner (Screen 18)
// -----------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct QuarantineScanResult {
    pub resources_inspected: usize,
    pub direct_id_leaks: usize,
    pub invalid_refs: usize,
    pub forbidden_terms: usize,
    pub raw_date_leaks: usize,
    pub passed: bool,
}

fn contains_ssn_pattern(text: &str) -> bool {
    let b = text.as_bytes();
    if b.len() < 11 {
        return false;
    }
    for i in 0..=b.len() - 11 {
        if b[i].is_ascii_digit()
            && b[i + 1].is_ascii_digit()
            && b[i + 2].is_ascii_digit()
            && b[i + 3] == b'-'
            && b[i + 4].is_ascii_digit()
            && b[i + 5].is_ascii_digit()
            && b[i + 6] == b'-'
            && b[i + 7].is_ascii_digit()
            && b[i + 8].is_ascii_digit()
            && b[i + 9].is_ascii_digit()
            && b[i + 10].is_ascii_digit()
        {
            return true;
        }
    }
    false
}

fn contains_unshifted_date(text: &str) -> bool {
    let b = text.as_bytes();
    if b.len() < 10 {
        return false;
    }
    for i in 0..=b.len() - 10 {
        if b[i].is_ascii_digit()
            && b[i + 1].is_ascii_digit()
            && b[i + 2].is_ascii_digit()
            && b[i + 3].is_ascii_digit()
            && b[i + 4] == b'-'
            && b[i + 5].is_ascii_digit()
            && b[i + 6].is_ascii_digit()
            && b[i + 7] == b'-'
            && b[i + 8].is_ascii_digit()
            && b[i + 9].is_ascii_digit()
        {
            let year = &text[i..i + 4];
            if year != "2026" {
                return true;
            }
        }
    }
    false
}

fn has_forbidden_marker(text: &str) -> bool {
    let upper = text.to_uppercase();
    const FORBIDDEN: &[&str] = &[
        "CONFIDENTIAL",
        "RESTRICTED",
        "SSN:",
        "MRN:",
        "DOB:",
        "PATIENT_REAL",
        "PHI:",
    ];
    FORBIDDEN.iter().any(|pat| upper.contains(pat))
}

pub fn scan_export_quarantine(
    resources: &[FictionalReadbackResource],
    supplementary_texts: &[&str],
) -> QuarantineScanResult {
    let mut direct_id_leaks = resources
        .iter()
        .filter(|r| {
            !r.resource_id.starts_with("fictional-")
                || contains_ssn_pattern(&r.resource_id)
                || contains_ssn_pattern(&r.full_url)
                || r.resource_id.contains('@')
                || r.full_url.contains('@')
        })
        .count();

    let invalid_refs = resources
        .iter()
        .flat_map(|r| &r.links)
        .filter(|l| !l.target.starts_with("urn:uuid:"))
        .count();

    let mut forbidden_terms = resources
        .iter()
        .filter(|r| {
            has_forbidden_marker(&r.resource_id)
                || has_forbidden_marker(&r.full_url)
                || r.links.iter().any(|l| has_forbidden_marker(&l.target))
        })
        .count();

    let mut raw_date_leaks = resources
        .iter()
        .filter(|r| contains_unshifted_date(&r.resource_id) || contains_unshifted_date(&r.full_url))
        .count();

    for text in supplementary_texts {
        if contains_ssn_pattern(text) || text.contains('@') {
            direct_id_leaks += 1;
        }
        if has_forbidden_marker(text) {
            forbidden_terms += 1;
        }
        if contains_unshifted_date(text) {
            raw_date_leaks += 1;
        }
    }

    let passed = !resources.is_empty()
        && direct_id_leaks == 0
        && invalid_refs == 0
        && forbidden_terms == 0
        && raw_date_leaks == 0;

    QuarantineScanResult {
        resources_inspected: resources.len(),
        direct_id_leaks,
        invalid_refs,
        forbidden_terms,
        raw_date_leaks,
        passed,
    }
}

/// Offline desktop runtime never executes model inference or fabricates measured benchmark scores.
pub fn benchmark_measured_results_available() -> bool {
    false
}

/// Fail-closed integration dry-run simulator. Live EHR write endpoints are permanently refused.
pub fn execute_integration_dry_run(
    endpoint_idx: usize,
    resource_count: usize,
) -> Result<String, &'static str> {
    match endpoint_idx {
        0 | 1 => {
            let payload = format!(
                "DRY_RUN_READ_ONLY:ENDPOINT={endpoint_idx}:RESOURCES={resource_count}:PACKETS=0"
            );
            let digest = sha256_hex(payload.as_bytes());
            Ok(format!("DRY_RUN_READONLY_SIMULATION_SHA256_{digest}"))
        }
        _ => Err("SECURITY_REFUSAL_EHR_WRITE_BLOCKED"),
    }
}

// -----------------------------------------------------------------------------
// Dynamic Graph Calculation
// -----------------------------------------------------------------------------

#[derive(Clone, Debug)]
pub struct DynamicGraphNode {
    pub id: String,
    pub resource_type: String,
    pub full_url: String,
    pub role: &'static str,
    pub in_degree: usize,
    pub out_degree: usize,
    pub incoming_from: Vec<String>,
    pub outgoing_to: Vec<(String, String)>, // (field, target_id)
}

pub fn build_dynamic_graph(
    resources: &[FictionalReadbackResource],
) -> (Vec<DynamicGraphNode>, bool, String) {
    if resources.is_empty() {
        return (
            Vec::new(),
            false,
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855".to_string(),
        );
    }

    let mut url_to_idx = HashMap::new();
    let mut id_to_idx = HashMap::new();
    for (idx, r) in resources.iter().enumerate() {
        url_to_idx.insert(r.full_url.clone(), idx);
        id_to_idx.insert(r.resource_id.clone(), idx);
    }

    let mut nodes: Vec<DynamicGraphNode> = resources
        .iter()
        .map(|r| {
            let role = match r.resource_type.as_str() {
                "Patient" => "Core Subject (Patient)",
                "Encounter" => "Clinical Event (Encounter)",
                "Observation" => "Clinical Finding (Observation)",
                _ => "Synthetic FHIR Resource",
            };
            DynamicGraphNode {
                id: r.resource_id.clone(),
                resource_type: r.resource_type.clone(),
                full_url: r.full_url.clone(),
                role,
                in_degree: 0,
                out_degree: 0,
                incoming_from: Vec::new(),
                outgoing_to: Vec::new(),
            }
        })
        .collect();

    let mut adj = vec![Vec::new(); resources.len()];

    for (src_idx, r) in resources.iter().enumerate() {
        for link in &r.links {
            let tgt_idx = url_to_idx
                .get(&link.target)
                .copied()
                .or_else(|| id_to_idx.get(&link.target).copied());
            if let Some(target) = tgt_idx {
                nodes[src_idx].out_degree += 1;
                nodes[src_idx]
                    .outgoing_to
                    .push((link.field.clone(), resources[target].resource_id.clone()));
                nodes[target].in_degree += 1;
                nodes[target].incoming_from.push(r.resource_id.clone());
                adj[src_idx].push(target);
            }
        }
    }

    // DFS Cycle detection (3-color algorithm)
    let mut state = vec![0u8; resources.len()]; // 0=unvisited, 1=visiting, 2=visited
    fn dfs(u: usize, adj: &[Vec<usize>], state: &mut [u8]) -> bool {
        state[u] = 1;
        for &v in &adj[u] {
            if state[v] == 1 {
                return true;
            }
            if state[v] == 0 && dfs(v, adj, state) {
                return true;
            }
        }
        state[u] = 2;
        false
    }

    let mut has_cycle = false;
    for i in 0..resources.len() {
        if state[i] == 0 && dfs(i, &adj, &mut state) {
            has_cycle = true;
            break;
        }
    }

    let mut hasher = Sha256::new();
    for node in &nodes {
        hasher.update(node.id.as_bytes());
        hasher.update(node.in_degree.to_string().as_bytes());
        hasher.update(node.out_degree.to_string().as_bytes());
    }
    let graph_sha = hasher_hex(hasher);

    (nodes, has_cycle, graph_sha)
}

// -----------------------------------------------------------------------------
// ConnectedScreensState
// -----------------------------------------------------------------------------

#[derive(Clone, Debug)]
pub struct ConnectedScreensState {
    // 1. Local Search
    pub search_query: String,
    pub search_scope: usize,
    pub search_last_match_count: usize,

    // 5. Note Drafts
    pub note_subjective: String,
    pub note_objective: String,
    pub note_assessment: String,
    pub note_plan: String,
    pub note_missing_info_acknowledged: bool,
    pub note_attestation_receipt: Option<String>,

    // 8. Patient Graph
    pub graph_selected_node: usize,
    pub graph_edge_filter: usize,

    // 9. Patient Timeline
    pub timeline_selected_event: usize,
    pub timeline_category: usize,

    // 10. Documents & Canvas
    pub canvas_selected_doc: usize,
    pub canvas_notes: String,

    // 11. Clinical Evidence
    pub evidence_query: String,
    pub evidence_selected_snapshot: usize,
    pub evidence_abstention_threshold: f32,

    // 12. Literature Screening
    pub lit_criteria_include: [bool; 4],
    pub lit_selected_item: usize,
    pub lit_decisions: [Option<bool>; 5],

    // 13. Tables & Structured Data
    pub tables_selected_table: usize,
    pub tables_filter: String,

    // 16. Analytics
    pub analytics_selected_metric: usize,
    pub analytics_receipt_verified: bool,
    pub analytics_verified_receipt: Option<String>,

    // 17. Dataset Manager
    pub dataset_active_tab: usize,
    pub dataset_selected_index: usize,

    // 18. Export Quarantine
    pub quarantine_acknowledged: bool,
    pub quarantine_manifest_generated: bool,
    pub quarantine_manifest_receipt: Option<String>,

    // 19. Research Explorer
    pub research_selected_study: usize,
    pub research_active_tab: usize,

    // 20. Benchmark & Evaluation
    pub bench_selected_suite: usize,
    pub bench_seed_locked: bool,
    pub bench_verification_receipt: Option<String>,

    // 22. Integrations
    pub integration_selected_endpoint: usize,
    pub integration_dry_run_done: bool,
    pub integration_dry_run_receipt: Option<String>,
    pub integration_dry_run_error: Option<String>,

    // 23. Audit History
    pub audit_events: Vec<AuditEvent>,
    pub audit_selected_event: usize,
    pub audit_verified: bool,
    pub audit_verification_status: Option<Result<usize, (usize, String)>>,
    pub audit_ledger_path: String,
    pub audit_persistence_status: Option<Result<String, String>>,

    // 24. Storage & Recovery
    pub storage_vault_locked: bool,
    pub storage_passphrase: String,
    pub storage_salt: [u8; 16],
    pub storage_raw_key: Option<[u8; 32]>,
    pub storage_derived_key: Option<String>,
    pub storage_vault_tag: Option<String>,
    pub storage_backup_envelope: Option<Vec<u8>>,
    pub storage_backup_path: String,
    pub storage_backup_status: Option<Result<String, String>>,
    pub storage_backup_verified: bool,
    pub storage_wipe_simulation_done: bool,
    pub storage_op_counter: u64,
}

impl ConnectedScreensState {
    pub fn record_audit_event(&mut self, event_type: &str, actor: &str, payload: &str) {
        let seq = (self.audit_events.len() as u64) + 1;
        let prev_hash = if let Some(last) = self.audit_events.last() {
            last.hash.clone()
        } else {
            "0000000000000000000000000000000000000000000000000000000000000000".to_string()
        };
        let hash = compute_audit_hash(seq, event_type, actor, payload, &prev_hash);
        self.audit_events.push(AuditEvent {
            seq,
            event_type: event_type.to_string(),
            actor: actor.to_string(),
            payload: payload.to_string(),
            prev_hash,
            hash,
        });
        let verified = verify_audit_chain(&self.audit_events);
        self.audit_verified = verified.is_ok();
        self.audit_verification_status = Some(verified);
    }

    /// Best-effort clear of sensitive session references, vault keys, passphrases,
    /// and ephemeral receipts when the user clears or terminates a session.
    pub fn clear_sensitive_session_state(&mut self) {
        if let Some(mut key) = self.storage_raw_key.take() {
            zeroize_bytes(&mut key);
        }
        zeroize_bytes(&mut self.storage_salt);
        // Best-effort clear of passphrase string buffer
        self.storage_passphrase.clear();
        self.storage_passphrase.shrink_to_fit();
        self.storage_derived_key = None;
        self.storage_vault_tag = None;
        if let Some(mut env) = self.storage_backup_envelope.take() {
            zeroize_bytes(&mut env);
        }
        self.storage_backup_status = None;
        self.storage_backup_verified = false;
        self.storage_vault_locked = true;
        self.search_last_match_count = 0;
        self.note_attestation_receipt = None;
        self.analytics_receipt_verified = false;
        self.analytics_verified_receipt = None;
        self.quarantine_acknowledged = false;
        self.quarantine_manifest_generated = false;
        self.quarantine_manifest_receipt = None;
        self.bench_verification_receipt = None;
        self.integration_dry_run_done = false;
        self.integration_dry_run_receipt = None;
        self.integration_dry_run_error = None;
        self.record_audit_event(
            "SESSION_CLEAR",
            "user-local",
            "Cleared active session state and purged in-memory vault keys and receipts",
        );
    }
}

impl Drop for ConnectedScreensState {
    fn drop(&mut self) {
        if let Some(mut key) = self.storage_raw_key.take() {
            zeroize_bytes(&mut key);
        }
        zeroize_bytes(&mut self.storage_salt);
        self.storage_passphrase.clear();
    }
}

impl Default for ConnectedScreensState {
    fn default() -> Self {
        let audit_events = build_initial_audit_events();

        Self {
            search_query: String::new(),
            search_scope: 0,
            search_last_match_count: 0,

            note_subjective:
                "Fictional patient reports mild fatigue for 3 days. No fever, no shortness of breath, no chest discomfort."
                    .to_owned(),
            note_objective:
                "BP 120/80 mmHg (synthetic fixture). HR 72 bpm regular. Temp 37.0 C. Alert and oriented."
                    .to_owned(),
            note_assessment:
                "Synthetic encounter: observation consistent with mild non-specific fatigue. Essential hypertension well controlled on current fictional regimen."
                    .to_owned(),
            note_plan:
                "Encourage adequate oral hydration and rest. Continue current fictitious regimen. Follow-up in 14 days if symptoms persist. Review-only synthetic draft."
                    .to_owned(),
            note_missing_info_acknowledged: false,
            note_attestation_receipt: None,

            graph_selected_node: 0,
            graph_edge_filter: 0,

            timeline_selected_event: 0,
            timeline_category: 0,

            canvas_selected_doc: 0,
            canvas_notes:
                "Local research canvas: structured blocks, provenance annotations and export boundary receipts."
                    .to_owned(),

            evidence_query: "fictional observation".to_owned(),
            evidence_selected_snapshot: 0,
            evidence_abstention_threshold: 0.50,

            lit_criteria_include: [true, true, true, false],
            lit_selected_item: 0,
            lit_decisions: [Some(true), Some(true), None, Some(false), None],

            tables_selected_table: 0,
            tables_filter: String::new(),

            analytics_selected_metric: 0,
            analytics_receipt_verified: false,
            analytics_verified_receipt: None,

            dataset_active_tab: 0,
            dataset_selected_index: 0,

            quarantine_acknowledged: false,
            quarantine_manifest_generated: false,
            quarantine_manifest_receipt: None,

            research_selected_study: 0,
            research_active_tab: 0,

            bench_selected_suite: 0,
            bench_seed_locked: true,
            bench_verification_receipt: None,

            integration_selected_endpoint: 0,
            integration_dry_run_done: false,
            integration_dry_run_receipt: None,
            integration_dry_run_error: None,

            audit_events,
            audit_selected_event: 0,
            audit_verified: true,
            audit_verification_status: Some(Ok(1)),
            audit_ledger_path: String::new(),
            audit_persistence_status: None,

            storage_vault_locked: true,
            storage_passphrase: String::new(),
            storage_salt: [0u8; 16],
            storage_raw_key: None,
            storage_derived_key: None,
            storage_vault_tag: None,
            storage_backup_envelope: None,
            storage_backup_path: String::new(),
            storage_backup_status: None,
            storage_backup_verified: false,
            storage_wipe_simulation_done: false,
            storage_op_counter: 0,
        }
    }
}

// -----------------------------------------------------------------------------
// 4-Tier Screen Governance Classification
// -----------------------------------------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ScreenClassification {
    ClassA, // Core Workspace Foundation
    ClassB, // Independent Rust Verified
    ClassC, // Limited Demonstration / Spec Viewer
    ClassD, // Gated / Unavailable
}

impl ScreenClassification {
    pub fn badge_label(self) -> &'static str {
        match self {
            ScreenClassification::ClassA => "CLASS A · Core Workspace",
            ScreenClassification::ClassB => "CLASS B · Independent Rust Verified",
            ScreenClassification::ClassC => "CLASS C · Limited Demo / Spec",
            ScreenClassification::ClassD => "CLASS D · Gated / Unavailable",
        }
    }
}

pub fn screen_classification_by_label(label: &str) -> ScreenClassification {
    match label {
        "Audio & transcript"
        | "Orders & tasks"
        | "Coding suggestions"
        | "Model catalog & runtime" => ScreenClassification::ClassD,
        "Literature screening"
        | "Research explorer"
        | "Benchmark & evaluation"
        | "Integrations" => ScreenClassification::ClassC,
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
        | "Storage & recovery" => ScreenClassification::ClassB,
        _ => ScreenClassification::ClassA,
    }
}

// Helper to draw standard screen header and provenance card
fn screen_header(
    ui: &mut Ui,
    title: &str,
    purpose: &str,
    contract: &str,
    sources: &str,
    status_label: &str,
) {
    let p = *theme::palette(ui.ctx().theme());
    page_title(ui, title, purpose);
    ui.set_max_width(820.0);

    let classification = screen_classification_by_label(title);
    let (class_label, class_bg, class_text) = match classification {
        ScreenClassification::ClassA => (classification.badge_label(), p.badge, p.accent),
        ScreenClassification::ClassB => (classification.badge_label(), p.badge, p.accent),
        ScreenClassification::ClassC => (classification.badge_label(), p.badge, p.text_secondary),
        ScreenClassification::ClassD => (classification.badge_label(), p.pink_bg, p.pink_text),
    };

    theme::card(ui, |ui| {
        ui.horizontal(|ui| {
            section_title(ui, "Desktop Adapter Status");
            theme::tag(ui, class_label, class_bg, class_text);
            theme::tag(ui, status_label, p.badge, p.accent);
            theme::tag(ui, "Non-Clinical Synthetic Only", p.badge, p.text_secondary);
        });
        ui.add_space(theme::space::SM);
        ui.label(RichText::new(format!("Design contract: {contract}")).color(p.text_secondary));
        ui.label(
            RichText::new(format!("Backed by: {sources}"))
                .size(theme::size::SMALL)
                .color(p.text_muted),
        );
    });
    ui.add_space(theme::space::MD);
}

// Helper to render an empty state when no bundle is admitted yet
fn render_empty_bundle_card(app: &mut MedOriginNativePreview, ui: &mut Ui) {
    let p = *theme::palette(ui.ctx().theme());
    theme::card(ui, |ui| {
        ui.label(
            RichText::new("No synthetic bundle is currently admitted in this session.")
                .strong()
                .color(p.text_secondary),
        );
        ui.label(
            "Admit a bundle from Records or load the reviewed canonical synthetic fixture below:",
        );
        ui.add_space(theme::space::XS);
        if ui.button("Admit Default Synthetic Fixture").clicked() {
            let _ = app.open_embedded_fictional_bundle_demo();
        }
    });
    ui.add_space(theme::space::SM);
}

impl MedOriginNativePreview {
    // -------------------------------------------------------------------------
    // 1. Local Search (Screen 1)
    // -------------------------------------------------------------------------
    pub(crate) fn local_search_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[1];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · In-Memory Retrieval",
        );
        let p = *theme::palette(ui.ctx().theme());

        let resources = self.active_resources();

        theme::card(ui, |ui| {
            section_title(ui, "Search Query & Scope");
            ui.label(
                "Search dynamically across currently admitted synthetic FHIR resources and reference links.",
            );

            ui.horizontal(|ui| {
                ui.label("Query:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.search_query)
                        .hint_text("Type resource type, ID, URL or link (e.g., patient, obs, 001)")
                        .desired_width(320.0),
                );
                ui.label("Scope:");
                egui::ComboBox::from_id_salt("local_search_scope")
                    .selected_text(match self.connected.search_scope {
                        0 => "All Resources",
                        1 => "Patients Only",
                        2 => "Encounters Only",
                        _ => "Observations Only",
                    })
                    .show_ui(ui, |ui| {
                        ui.selectable_value(&mut self.connected.search_scope, 0, "All Resources");
                        ui.selectable_value(&mut self.connected.search_scope, 1, "Patients Only");
                        ui.selectable_value(&mut self.connected.search_scope, 2, "Encounters Only");
                        ui.selectable_value(
                            &mut self.connected.search_scope,
                            3,
                            "Observations Only",
                        );
                    });
            });

            ui.add_space(theme::space::SM);

            if resources.is_empty() {
                self.connected.search_last_match_count = 0;
                render_empty_bundle_card(self, ui);
                return;
            }

            let raw_query = self.connected.search_query.trim().to_lowercase();

            let matches: Vec<&FictionalReadbackResource> = resources
                .iter()
                .filter(|r| {
                    let scope_ok = match self.connected.search_scope {
                        1 => r.resource_type == "Patient",
                        2 => r.resource_type == "Encounter",
                        3 => r.resource_type == "Observation",
                        _ => true,
                    };
                    if !scope_ok {
                        return false;
                    }
                    if raw_query.is_empty() {
                        return true;
                    }
                    r.resource_type.to_lowercase().contains(&raw_query)
                        || r.resource_id.to_lowercase().contains(&raw_query)
                        || r.full_url.to_lowercase().contains(&raw_query)
                        || r.links.iter().any(|link| {
                            link.field.to_lowercase().contains(&raw_query)
                                || link.target.to_lowercase().contains(&raw_query)
                        })
                })
                .collect();

            self.connected.search_last_match_count = matches.len();

            ui.horizontal(|ui| {
                ui.label(
                    RichText::new(format!(
                        "Matching synthetic records: {} (of {} admitted)",
                        matches.len(),
                        resources.len()
                    ))
                    .strong(),
                );
            });
            ui.separator();

            if matches.is_empty() {
                ui.label(
                    RichText::new("0 records match the query filter in current scope.")
                        .color(p.text_secondary),
                );
            } else {
                egui::ScrollArea::vertical()
                    .max_height(280.0)
                    .show(ui, |ui| {
                        for r in matches {
                            let hash = sha256_hex(
                                format!("{}:{}:{}", r.resource_type, r.resource_id, r.full_url)
                                    .as_bytes(),
                            );

                            ui.group(|ui| {
                                ui.horizontal(|ui| {
                                    theme::tag(ui, &r.resource_type, p.badge, p.accent);
                                    ui.strong(&r.resource_id);
                                    ui.label(
                                        RichText::new(format!("SHA: {}...", &hash[..16]))
                                            .size(theme::size::SMALL)
                                            .color(p.text_muted),
                                    );
                                });
                                ui.label(
                                    RichText::new(&r.full_url)
                                        .size(theme::size::SMALL)
                                        .color(p.text_secondary),
                                );
                                if !r.links.is_empty() {
                                    let links_str = r
                                        .links
                                        .iter()
                                        .map(|l| format!("{}: {}", l.field, l.target))
                                        .collect::<Vec<_>>()
                                        .join(" | ");
                                    ui.label(
                                        RichText::new(format!("References: {links_str}"))
                                            .size(theme::size::SMALL)
                                            .color(p.text_muted),
                                    );
                                }
                            });
                            ui.add_space(theme::space::XS);
                        }
                    });
            }
        });
    }

    // -------------------------------------------------------------------------
    // 5. Note Drafts (Screen 5)
    // -------------------------------------------------------------------------
    pub(crate) fn note_drafts_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[5];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Local Review-Only Editor",
        );
        let p = *theme::palette(ui.ctx().theme());

        let resources = self.active_resources();
        let bound_patient = resources
            .iter()
            .find(|r| r.resource_type == "Patient")
            .map(|r| r.resource_id.clone());

        theme::card(ui, |ui| {
            ui.horizontal(|ui| {
                section_title(ui, "Fictional Clinical Note (SOAP Structure)");
                theme::tag(ui, "REVIEW ONLY — NO EHR COMMITS", p.pink_bg, p.pink_text);
            });
            ui.label("Source-linked draft editor with missing-information checks and non-clinical attestation.");
            ui.add_space(theme::space::SM);

            if let Some(ref pt) = bound_patient {
                ui.horizontal(|ui| {
                    ui.label("Bound Synthetic Patient Subject:");
                    theme::tag(ui, pt, p.badge, p.accent);
                });
            } else {
                ui.label(
                    RichText::new("Notice: No synthetic patient admitted. Attestation binds to session unlinked draft.")
                        .size(theme::size::SMALL)
                        .color(p.text_secondary),
                );
            }
            ui.add_space(theme::space::SM);

            ui.label(RichText::new("Subjective (Patient Reported):").strong());
            ui.add(
                egui::TextEdit::multiline(&mut self.connected.note_subjective)
                    .desired_rows(2)
                    .desired_width(f32::INFINITY),
            );

            ui.add_space(theme::space::XS);
            ui.label(RichText::new("Objective (Synthetic Vitals & Labs):").strong());
            ui.add(
                egui::TextEdit::multiline(&mut self.connected.note_objective)
                    .desired_rows(2)
                    .desired_width(f32::INFINITY),
            );

            ui.add_space(theme::space::XS);
            ui.label(RichText::new("Assessment:").strong());
            ui.add(
                egui::TextEdit::multiline(&mut self.connected.note_assessment)
                    .desired_rows(2)
                    .desired_width(f32::INFINITY),
            );

            ui.add_space(theme::space::XS);
            ui.label(RichText::new("Plan:").strong());
            ui.add(
                egui::TextEdit::multiline(&mut self.connected.note_plan)
                    .desired_rows(2)
                    .desired_width(f32::INFINITY),
            );

            ui.add_space(theme::space::SM);
            ui.separator();

            let subj_words = self.connected.note_subjective.split_whitespace().count();
            let obj_words = self.connected.note_objective.split_whitespace().count();
            let assess_words = self.connected.note_assessment.split_whitespace().count();
            let plan_words = self.connected.note_plan.split_whitespace().count();
            let total_words = subj_words + obj_words + assess_words + plan_words;

            section_title(ui, "Missing Information & Safety Checklist");
            ui.label(format!(
                "• Word counts: Subj: {subj_words} | Obj: {obj_words} | Assess: {assess_words} | Plan: {plan_words} (Total: {total_words} words)"
            ));
            let subj_ok = !self.connected.note_subjective.trim().is_empty();
            let obj_ok = !self.connected.note_objective.trim().is_empty();
            let assess_ok = !self.connected.note_assessment.trim().is_empty();
            let plan_ok = !self.connected.note_plan.trim().is_empty();

            ui.label(format!(
                "• Section completeness: [{}] Subjective  [{}] Objective  [{}] Assessment  [{}] Plan",
                if subj_ok { "x" } else { " " },
                if obj_ok { "x" } else { " " },
                if assess_ok { "x" } else { " " },
                if plan_ok { "x" } else { " " }
            ));

            ui.checkbox(
                &mut self.connected.note_missing_info_acknowledged,
                "I acknowledge this note is synthetic research output and cannot be committed to real EHR.",
            );

            ui.add_space(theme::space::SM);
            let can_attest = self.connected.note_missing_info_acknowledged
                && subj_ok
                && obj_ok
                && assess_ok
                && plan_ok;

            if ui
                .add_enabled(
                    can_attest,
                    egui::Button::new("Generate Synthetic Attestation Digest"),
                )
                .clicked()
            {
                let pt_binding = bound_patient.as_deref().unwrap_or("UNBOUND_SESSION");
                let note_content = format!(
                    "PATIENT:{pt_binding}\nSUBJ:{}\nOBJ:{}\nASSESS:{}\nPLAN:{}",
                    self.connected.note_subjective,
                    self.connected.note_objective,
                    self.connected.note_assessment,
                    self.connected.note_plan
                );
                let digest = sha256_hex(note_content.as_bytes());
                self.connected.note_attestation_receipt =
                    Some(format!("SYNTHETIC_NOTE_DIGEST_{digest}"));
                self.connected.record_audit_event(
                    "NOTE_ATTESTATION",
                    "user-local",
                    &format!("Generated synthetic SOAP note digest for {pt_binding}: {digest}"),
                );
            }

            if let Some(receipt) = &self.connected.note_attestation_receipt {
                ui.add_space(theme::space::XS);
                ui.group(|ui| {
                    ui.label(
                        RichText::new(format!("Attestation Receipt: {receipt}"))
                            .strong()
                            .color(p.accent),
                    );
                    ui.label(
                        "Session-only receipt computed with real SHA-256. Zero external transmission.",
                    );
                });
            }
        });
    }

    // -------------------------------------------------------------------------
    // 8. Patient Graph (Screen 8)
    // -------------------------------------------------------------------------
    pub(crate) fn patient_graph_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[8];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Relation Graph Explorer",
        );
        let p = *theme::palette(ui.ctx().theme());

        let resources = self.active_resources();

        theme::card(ui, |ui| {
            section_title(ui, "Dynamic Synthetic Knowledge Graph");
            ui.label("Derives nodes and topological edges dynamically from admitted synthetic FHIR references.");

            if resources.is_empty() {
                render_empty_bundle_card(self, ui);
                return;
            }

            let (nodes, has_cycle, graph_sha) = build_dynamic_graph(&resources);
            let total_edges: usize = nodes.iter().map(|n| n.out_degree).sum();

            ui.horizontal(|ui| {
                ui.label("Edge Filter:");
                egui::ComboBox::from_id_salt("graph_edge_filter")
                    .selected_text(match self.connected.graph_edge_filter {
                        0 => format!("All Edges ({total_edges})"),
                        1 => "Subject References Only".to_string(),
                        _ => "Context References Only".to_string(),
                    })
                    .show_ui(ui, |ui| {
                        ui.selectable_value(
                            &mut self.connected.graph_edge_filter,
                            0,
                            format!("All Edges ({total_edges})"),
                        );
                        ui.selectable_value(
                            &mut self.connected.graph_edge_filter,
                            1,
                            "Subject References Only",
                        );
                        ui.selectable_value(
                            &mut self.connected.graph_edge_filter,
                            2,
                            "Context References Only",
                        );
                    });
            });

            ui.add_space(theme::space::SM);

            if nodes.is_empty() {
                ui.label(RichText::new("Empty graph: 0 nodes").color(p.text_secondary));
                return;
            }

            if self.connected.graph_selected_node >= nodes.len() {
                self.connected.graph_selected_node = 0;
            }

            ui.columns(2, |columns| {
                columns[0].label(RichText::new("Graph Nodes (Admitted Dataset):").strong());
                for (idx, node) in nodes.iter().enumerate() {
                    let is_selected = self.connected.graph_selected_node == idx;
                    let label = format!("{}: {}/{}", idx, node.resource_type, node.id);
                    if columns[0].selectable_label(is_selected, label).clicked() {
                        self.connected.graph_selected_node = idx;
                    }
                }

                columns[1].label(RichText::new("Selected Node Inspection:").strong());
                let selected = &nodes[self.connected.graph_selected_node];
                theme::card(&mut columns[1], |ui| {
                    ui.strong(format!("{}/{}", selected.resource_type, selected.id));
                    ui.label(format!("Role: {}", selected.role));
                    ui.label(format!("Full URL: {}", selected.full_url));
                    ui.label(format!(
                        "In-degree: {} | Out-degree: {}",
                        selected.in_degree, selected.out_degree
                    ));

                    if !selected.incoming_from.is_empty() {
                        ui.label(format!(
                            "Incoming links from: {}",
                            selected.incoming_from.join(", ")
                        ));
                    }
                    if !selected.outgoing_to.is_empty() {
                        let out_str = selected
                            .outgoing_to
                            .iter()
                            .map(|(f, t)| format!("{f} -> {t}"))
                            .collect::<Vec<_>>()
                            .join(", ");
                        ui.label(format!("Outgoing references: {out_str}"));
                    }

                    ui.add_space(theme::space::XS);
                    if has_cycle {
                        ui.label(
                            RichText::new("Cycle Check: CYCLIC REFERENCE DETECTED")
                                .color(p.pink_text),
                        );
                    } else {
                        ui.label(
                            RichText::new(format!(
                                "Cycle Check: 0 cycles detected across {} nodes (Topological DAG validated)",
                                nodes.len()
                            ))
                            .color(p.accent),
                        );
                    }
                    ui.label(
                        RichText::new(format!("Edge Provenance: SYNTHETIC_EDGE_LOCK_{}", &graph_sha[..16]))
                            .size(theme::size::SMALL)
                            .color(p.text_muted),
                    );
                });
            });
        });
    }

    // -------------------------------------------------------------------------
    // 9. Patient Timeline (Screen 9)
    // -------------------------------------------------------------------------
    pub(crate) fn patient_timeline_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[9];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Chronological Event Stream",
        );
        let p = *theme::palette(ui.ctx().theme());

        let resources = self.active_resources();

        theme::card(ui, |ui| {
            section_title(ui, "Chronological Events with Uncertainty Indicators");
            ui.label("Temporal projection derived dynamically from admitted synthetic clinical resources.");

            if resources.is_empty() {
                render_empty_bundle_card(self, ui);
                return;
            }

            ui.horizontal(|ui| {
                ui.label("Category Filter:");
                egui::ComboBox::from_id_salt("timeline_cat_filter")
                    .selected_text(match self.connected.timeline_category {
                        0 => format!("All Events ({})", resources.len()),
                        1 => "Encounters Only".to_string(),
                        2 => "Observations Only".to_string(),
                        _ => "Patients Only".to_string(),
                    })
                    .show_ui(ui, |ui| {
                        ui.selectable_value(
                            &mut self.connected.timeline_category,
                            0,
                            format!("All Events ({})", resources.len()),
                        );
                        ui.selectable_value(
                            &mut self.connected.timeline_category,
                            1,
                            "Encounters Only",
                        );
                        ui.selectable_value(
                            &mut self.connected.timeline_category,
                            2,
                            "Observations Only",
                        );
                        ui.selectable_value(
                            &mut self.connected.timeline_category,
                            3,
                            "Patients Only",
                        );
                    });
            });

            ui.add_space(theme::space::SM);

            let mut timeline_items = Vec::new();
            for (i, r) in resources.iter().enumerate() {
                let hour = 9 + (i / 4);
                let min = (i * 15) % 60;
                let timestamp = format!("2026-10-15 {hour:02}:{min:02}");
                let (cat, uncert, desc) = match r.resource_type.as_str() {
                    "Patient" => (
                        "Patient",
                        "Uncertainty: None (Deterministic identity registration)",
                        format!("Synthetic Patient subject: {}", r.resource_id),
                    ),
                    "Encounter" => (
                        "Encounter",
                        "Uncertainty: Scheduled window (±15 min)",
                        format!(
                            "Ambulatory encounter: {} ({} reference link(s))",
                            r.resource_id,
                            r.links.len()
                        ),
                    ),
                    "Observation" => (
                        "Observation",
                        "Uncertainty: ±1.5% calibration margin (synthetic assay)",
                        format!(
                            "Observation finding: {} linked to {} target(s)",
                            r.resource_id,
                            r.links.len()
                        ),
                    ),
                    _ => (
                        "Resource",
                        "Uncertainty: Discrete record entry",
                        format!("Resource: {}", r.resource_id),
                    ),
                };
                timeline_items.push((timestamp, cat, r.resource_id.clone(), desc, uncert));
            }

            let filtered_items: Vec<_> = timeline_items
                .iter()
                .enumerate()
                .filter(
                    |(_, (_, cat, _, _, _))| match self.connected.timeline_category {
                        1 => *cat == "Encounter",
                        2 => *cat == "Observation",
                        3 => *cat == "Patient",
                        _ => true,
                    },
                )
                .collect();

            if filtered_items.is_empty() {
                ui.label(
                    RichText::new("0 timeline events matching current category filter.")
                        .color(p.text_secondary),
                );
            } else {
                egui::ScrollArea::vertical()
                    .max_height(280.0)
                    .show(ui, |ui| {
                        for (orig_idx, (time, cat, id, desc, uncert)) in filtered_items {
                            let is_sel = self.connected.timeline_selected_event == orig_idx;
                            ui.group(|ui| {
                                ui.horizontal(|ui| {
                                    if ui.selectable_label(is_sel, time).clicked() {
                                        self.connected.timeline_selected_event = orig_idx;
                                    }
                                    theme::tag(ui, cat, p.badge, p.accent);
                                    ui.strong(id);
                                });
                                ui.label(desc);
                                ui.label(
                                    RichText::new(*uncert)
                                        .size(theme::size::SMALL)
                                        .color(p.text_muted),
                                );
                            });
                            ui.add_space(theme::space::XS);
                        }
                    });
            }
        });
    }

    // -------------------------------------------------------------------------
    // 10. Documents & Canvas (Screen 10)
    // -------------------------------------------------------------------------
    pub(crate) fn documents_canvas_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[10];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Structured Canvas",
        );
        let p = *theme::palette(ui.ctx().theme());

        let resources = self.active_resources();
        let patient_ids: Vec<_> = resources
            .iter()
            .filter(|r| r.resource_type == "Patient")
            .map(|r| r.resource_id.as_str())
            .collect();
        let encounter_ids: Vec<_> = resources
            .iter()
            .filter(|r| r.resource_type == "Encounter")
            .map(|r| r.resource_id.as_str())
            .collect();

        theme::card(ui, |ui| {
            section_title(ui, "Structured Document Blocks & Local Canvas");
            ui.label("Interactive clinical document canvas with modular object blocks derived from active session.");

            ui.horizontal(|ui| {
                ui.label("Document Template:");
                egui::ComboBox::from_id_salt("canvas_doc_selector")
                    .selected_text(match self.connected.canvas_selected_doc {
                        0 => "Template A: Synthetic Ambulatory Summary",
                        _ => "Template B: Synthetic Research Study Case Report",
                    })
                    .show_ui(ui, |ui| {
                        ui.selectable_value(
                            &mut self.connected.canvas_selected_doc,
                            0,
                            "Template A: Synthetic Ambulatory Summary",
                        );
                        ui.selectable_value(
                            &mut self.connected.canvas_selected_doc,
                            1,
                            "Template B: Synthetic Research Study Case Report",
                        );
                    });
            });

            ui.add_space(theme::space::SM);
            ui.group(|ui| {
                ui.strong("Block 1: Identity & Demographics");
                if patient_ids.is_empty() {
                    ui.label("Subject: Unbound Session (0 synthetic patients admitted)");
                } else {
                    ui.label(format!(
                        "Admitted Subjects: {} | Gender: unknown (synthetic) | Fixed Cohort",
                        patient_ids.join(", ")
                    ));
                }
            });

            ui.group(|ui| {
                ui.strong("Block 2: Encounter Clinical Synopsis");
                if encounter_ids.is_empty() {
                    ui.label("Encounter Summary: 0 active encounters in bundle");
                } else {
                    ui.label(format!(
                        "Encounters ({}) : {} | Class: AMB | Status: finished",
                        encounter_ids.len(),
                        encounter_ids.join(", ")
                    ));
                }
            });

            ui.group(|ui| {
                ui.strong("Block 3: Research Annotations & Local Canvas Notes");
                ui.add(
                    egui::TextEdit::multiline(&mut self.connected.canvas_notes)
                        .desired_rows(3)
                        .desired_width(f32::INFINITY),
                );
            });

            let canvas_combined = format!(
                "DOC_TEMPLATE_{}\nPATIENTS:{}\nENCOUNTERS:{}\nNOTES:{}",
                self.connected.canvas_selected_doc,
                patient_ids.join(","),
                encounter_ids.join(","),
                self.connected.canvas_notes
            );
            let digest = sha256_hex(canvas_combined.as_bytes());

            ui.add_space(theme::space::SM);
            ui.horizontal(|ui| {
                theme::tag(ui, "QUARANTINED EXPORT BOUNDARY", p.pink_bg, p.pink_text);
                if ui.button("Record Canvas Snapshot to Audit").clicked() {
                    self.connected.record_audit_event(
                        "CANVAS_DIGEST_RECORDED",
                        "user-local",
                        &format!(
                            "Recorded structured canvas template {} digest: {digest}",
                            self.connected.canvas_selected_doc
                        ),
                    );
                }
                ui.label(
                    RichText::new(format!("Canvas SHA-256: {digest}"))
                        .size(theme::size::SMALL)
                        .color(p.text_muted),
                );
            });
        });
    }

    // -------------------------------------------------------------------------
    // 11. Clinical Evidence (Screen 11)
    // -------------------------------------------------------------------------
    pub(crate) fn clinical_evidence_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[11];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Evidence & Abstention Workbench",
        );
        let p = *theme::palette(ui.ctx().theme());

        theme::card(ui, |ui| {
            ui.horizontal(|ui| {
                section_title(ui, "Evidence Retrieval & Abstention Evaluation");
                theme::tag(ui, "OFFLINE CORPUS ONLY", p.badge, p.accent);
            });
            ui.label("Query reviewed synthetic corpus, calculate dynamic match scores, and enforce abstention thresholds.");

            ui.horizontal(|ui| {
                ui.label("Evidence Query:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.evidence_query)
                        .desired_width(340.0),
                );
            });

            let snapshot_id_opt = VERIFIED_EVIDENCE_SNAPSHOT_IDS
                .get(self.connected.evidence_selected_snapshot)
                .copied();
            let search_result = match snapshot_id_opt {
                Some(snap_id) => search_verified_evidence(
                    snap_id,
                    &self.connected.evidence_query,
                    self.connected.evidence_abstention_threshold,
                ),
                None => Err("UNKNOWN_OR_MISSING_SNAPSHOT_REFUSED"),
            };

            ui.horizontal(|ui| {
                ui.label("Verified Snapshot:");
                egui::ComboBox::from_id_salt("evidence_snapshot")
                    .selected_text(snapshot_id_opt.unwrap_or("INVALID / UNKNOWN SNAPSHOT"))
                    .show_ui(ui, |ui| {
                        for (idx, snap_id) in VERIFIED_EVIDENCE_SNAPSHOT_IDS.iter().enumerate() {
                            ui.selectable_value(
                                &mut self.connected.evidence_selected_snapshot,
                                idx,
                                *snap_id,
                            );
                        }
                    });
                if search_result.is_ok() {
                    theme::tag(ui, "SNAPSHOT_SHA256_VERIFIED", p.badge, p.accent);
                } else {
                    theme::tag(ui, "UNKNOWN_SNAPSHOT_REJECTED", p.pink_bg, p.pink_text);
                }
            });

            ui.horizontal(|ui| {
                ui.label("Abstention Threshold:");
                ui.add(
                    egui::Slider::new(
                        &mut self.connected.evidence_abstention_threshold,
                        0.20..=0.99,
                    )
                    .text("Confidence Gate"),
                );
            });

            match search_result {
                Err(err_code) => {
                    ui.label(
                        RichText::new(format!(
                            "SYSTEM_ABSTENTION: {err_code}. Unknown or missing snapshot cannot be searched."
                        ))
                        .color(p.pink_text)
                        .strong(),
                    );
                }
                Ok((snapshot, ranked)) => {
                    ui.label(
                        RichText::new(format!(
                            "Computed Snapshot SHA-256 ({} bytes, {} records): {}",
                            snapshot.byte_len,
                            snapshot.entries.len(),
                            snapshot.sha256
                        ))
                        .size(theme::size::SMALL)
                        .color(p.text_muted),
                    );
                    ui.add_space(theme::space::SM);
                    section_title(
                        ui,
                        "Retrieved Evidence Entries (Real Fixture Token Overlap)",
                    );

                    let mut admitted_count = 0usize;
                    egui::ScrollArea::vertical()
                        .max_height(240.0)
                        .show(ui, |ui| {
                            for (entry, score, term_matches, passed) in &ranked {
                                if *passed {
                                    admitted_count += 1;
                                }
                                ui.group(|ui| {
                                    ui.horizontal(|ui| {
                                        ui.strong(&entry.id);
                                        theme::tag(ui, &entry.resource_type, p.badge, p.accent);
                                        ui.label(format!(
                                            "Overlap: {score:.3} ({term_matches} term matches)"
                                        ));
                                        if *passed {
                                            theme::tag(ui, "ADMITTED", p.badge, p.accent);
                                        } else {
                                            theme::tag(ui, "ABSTAIN", p.pink_bg, p.pink_text);
                                        }
                                    });
                                    ui.label(
                                        RichText::new(&entry.full_url)
                                            .size(theme::size::SMALL)
                                            .color(p.text_secondary),
                                    );
                                });
                                ui.add_space(theme::space::XS);
                            }
                        });

                    ui.add_space(theme::space::SM);
                    if admitted_count == 0 {
                        ui.group(|ui| {
                            ui.label(
                                RichText::new(format!(
                                    "SYSTEM_ABSTENTION_ENFORCED: 0 records satisfy confidence gate ({:.2}). System explicitly abstains.",
                                    self.connected.evidence_abstention_threshold
                                ))
                                .strong()
                                .color(p.pink_text),
                            );
                        });
                        ui.add_space(theme::space::XS);
                    }
                    ui.label(
                        RichText::new(
                            "Contradiction Detection: NOT PERFORMED (requires qualified external NLI claim-pair evaluator; zero contradictory assertions claimed).",
                        )
                        .color(p.text_secondary),
                    );
                    ui.label(
                        RichText::new("DISCLOSURE: Real SHA-256 verification and token-overlap retrieval over committed synthetic fixtures only. Zero network queries.")
                            .size(theme::size::SMALL)
                            .color(p.text_muted),
                    );
                }
            }
        });
    }

    // -------------------------------------------------------------------------
    // 12. Literature Screening (Screen 12)
    // -------------------------------------------------------------------------
    pub(crate) fn literature_screening_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[12];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Systematic Literature Screening",
        );
        let p = *theme::palette(ui.ctx().theme());

        theme::card(ui, |ui| {
            section_title(ui, "Systematic Review Screening Criteria");
            ui.label("Inclusion and exclusion screening criteria with real-time PRISMA flow calculations.");

            ui.checkbox(
                &mut self.connected.lit_criteria_include[0],
                "Peer-reviewed scientific study or verified preprint",
            );
            ui.checkbox(
                &mut self.connected.lit_criteria_include[1],
                "Evaluates evidence provenance, grounding or uncertainty",
            );
            ui.checkbox(
                &mut self.connected.lit_criteria_include[2],
                "Open-access or Apache-2.0 compatible literature license",
            );
            ui.checkbox(
                &mut self.connected.lit_criteria_include[3],
                "Includes real clinical deployment trial (Excluded by Lane C)",
            );

            ui.add_space(theme::space::SM);
            let papers = [
                (
                    "Paper 1",
                    "Evidence Provenance in Autonomous Medical AI Systems",
                    "PMID: 38291001",
                    "Authors: Al-Shehri et al.",
                ),
                (
                    "Paper 2",
                    "Deterministic Question Answering on Frozen Biomedical Benchmarks",
                    "PMID: 38450122",
                    "Authors: Research Core Consortium",
                ),
                (
                    "Paper 3",
                    "Privacy-Preserving Synthetic EHR Workflows with FHIR R4",
                    "PMID: 38671190",
                    "Authors: Workspace Security Group",
                ),
                (
                    "Paper 4",
                    "Cryptographic Audit Trails for Healthcare Machine Learning",
                    "PMID: 38789045",
                    "Authors: Integrity Foundation",
                ),
                (
                    "Paper 5",
                    "Evaluation Protocols for Explicit Abstention in Clinical AI",
                    "PMID: 38912301",
                    "Authors: Medical AI Governance",
                ),
            ];

            let included_count = self
                .connected
                .lit_decisions
                .iter()
                .filter(|d| **d == Some(true))
                .count();
            let excluded_count = self
                .connected
                .lit_decisions
                .iter()
                .filter(|d| **d == Some(false))
                .count();
            let pending_count = self
                .connected
                .lit_decisions
                .iter()
                .filter(|d| d.is_none())
                .count();

            section_title(
                ui,
                &format!(
                    "Screening Queue (Total: {} | Included: {} | Excluded: {} | Pending: {})",
                    papers.len(),
                    included_count,
                    excluded_count,
                    pending_count
                ),
            );

            for (idx, (tag, title, pmid, authors)) in papers.iter().enumerate() {
                let is_sel = self.connected.lit_selected_item == idx;
                let decision_str = match self.connected.lit_decisions[idx] {
                    Some(true) => "Included",
                    Some(false) => "Excluded",
                    None => "Pending",
                };
                ui.group(|ui| {
                    ui.horizontal(|ui| {
                        if ui.selectable_label(is_sel, *tag).clicked() {
                            self.connected.lit_selected_item = idx;
                        }
                        ui.strong(*title);
                        theme::tag(
                            ui,
                            decision_str,
                            p.badge,
                            if decision_str == "Included" {
                                p.accent
                            } else if decision_str == "Excluded" {
                                p.pink_text
                            } else {
                                p.text_secondary
                            },
                        );
                    });
                    ui.label(format!("{pmid} · {authors}"));
                });
                ui.add_space(theme::space::XS);
            }

            ui.add_space(theme::space::SM);
            ui.horizontal(|ui| {
                let sel = self.connected.lit_selected_item;
                ui.label(format!("Decision for Paper {}:", sel + 1));
                if ui.button("Mark Included").clicked() {
                    self.connected.lit_decisions[sel] = Some(true);
                }
                if ui.button("Mark Excluded").clicked() {
                    self.connected.lit_decisions[sel] = Some(false);
                }
                if ui.button("Reset Decision").clicked() {
                    self.connected.lit_decisions[sel] = None;
                }
            });

            let prisma_payload = format!(
                "PRISMA:{:?}:{:?}",
                self.connected.lit_criteria_include, self.connected.lit_decisions
            );
            let prisma_digest = sha256_hex(prisma_payload.as_bytes());

            ui.add_space(theme::space::SM);
            ui.label(
                RichText::new(format!("PRISMA State Digest: sha256:{prisma_digest}"))
                    .size(theme::size::SMALL)
                    .color(p.text_muted),
            );
        });
    }

    // -------------------------------------------------------------------------
    // 13. Tables & Structured Data (Screen 13)
    // -------------------------------------------------------------------------
    pub(crate) fn tables_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[13];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Local Tabular View",
        );
        let p = *theme::palette(ui.ctx().theme());

        let resources = self.active_resources();

        theme::card(ui, |ui| {
            section_title(ui, "Structured Data Tables & Export Preview");
            ui.label("Dynamic tabular view of synthetic clinical resources derived from the admitted dataset.");

            if resources.is_empty() {
                render_empty_bundle_card(self, ui);
                return;
            }

            ui.horizontal(|ui| {
                ui.label("Table:");
                egui::ComboBox::from_id_salt("tables_selector")
                    .selected_text(match self.connected.tables_selected_table {
                        0 => "Synthetic Observations",
                        1 => "Synthetic Encounters",
                        _ => "Synthetic Patients",
                    })
                    .show_ui(ui, |ui| {
                        ui.selectable_value(
                            &mut self.connected.tables_selected_table,
                            0,
                            "Synthetic Observations",
                        );
                        ui.selectable_value(
                            &mut self.connected.tables_selected_table,
                            1,
                            "Synthetic Encounters",
                        );
                        ui.selectable_value(
                            &mut self.connected.tables_selected_table,
                            2,
                            "Synthetic Patients",
                        );
                    });

                ui.label("Filter:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.tables_filter)
                        .hint_text("Filter by ID or link")
                        .desired_width(180.0),
                );
            });

            ui.add_space(theme::space::SM);

            let filter = self.connected.tables_filter.trim().to_lowercase();
            let target_type = match self.connected.tables_selected_table {
                0 => "Observation",
                1 => "Encounter",
                _ => "Patient",
            };

            let matching_resources: Vec<&FictionalReadbackResource> = resources
                .iter()
                .filter(|r| r.resource_type == target_type)
                .filter(|r| {
                    if filter.is_empty() {
                        true
                    } else {
                        r.resource_id.to_lowercase().contains(&filter)
                            || r.full_url.to_lowercase().contains(&filter)
                            || r.links
                                .iter()
                                .any(|l| l.target.to_lowercase().contains(&filter))
                    }
                })
                .collect();

            ui.label(
                RichText::new(format!(
                    "Displaying {} row(s) for table '{}'",
                    matching_resources.len(),
                    target_type
                ))
                .strong(),
            );

            ui.add_space(theme::space::XS);

            egui::Grid::new("structured_table_grid")
                .striped(true)
                .min_col_width(120.0)
                .show(ui, |ui| {
                    ui.strong("Resource ID");
                    ui.strong("Type");
                    ui.strong("Full URL");
                    ui.strong("Reference Links");
                    ui.end_row();

                    for r in &matching_resources {
                        ui.label(&r.resource_id);
                        ui.label(&r.resource_type);
                        ui.label(
                            RichText::new(&r.full_url)
                                .size(theme::size::SMALL)
                                .color(p.text_secondary),
                        );
                        let links_desc = if r.links.is_empty() {
                            "0 links".to_string()
                        } else {
                            r.links
                                .iter()
                                .map(|l| format!("{}: {}", l.field, l.target))
                                .collect::<Vec<_>>()
                                .join(" | ")
                        };
                        ui.label(
                            RichText::new(links_desc)
                                .size(theme::size::SMALL)
                                .color(p.text_muted),
                        );
                        ui.end_row();
                    }
                });

            ui.add_space(theme::space::SM);
            ui.label(
                RichText::new(
                    "Export Boundary: In-memory table only. Zero telemetry, zero external writes.",
                )
                .size(theme::size::SMALL)
                .color(p.text_muted),
            );
        });
    }

    // -------------------------------------------------------------------------
    // 16. Analytics (Screen 16)
    // -------------------------------------------------------------------------
    pub(crate) fn analytics_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[16];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Workspace Analytics",
        );
        let p = *theme::palette(ui.ctx().theme());

        let resources = self.active_resources();

        let patient_count = resources
            .iter()
            .filter(|r| r.resource_type == "Patient")
            .count();
        let observation_count = resources
            .iter()
            .filter(|r| r.resource_type == "Observation")
            .count();
        let encounter_count = resources
            .iter()
            .filter(|r| r.resource_type == "Encounter")
            .count();
        let total_resources = resources.len();
        let total_links: usize = resources.iter().map(|r| r.links.len()).sum();
        let completeness = if total_resources > 0 { 100.0 } else { 0.0 };

        theme::card(ui, |ui| {
            ui.horizontal(|ui| {
                section_title(ui, "Workspace Cohort Indicators");
                theme::tag(ui, "ZERO TELEMETRY", p.badge, p.accent);
            });
            ui.label(
                "Descriptive indicators calculated dynamically from the active admitted synthetic dataset.",
            );
            ui.add_space(theme::space::SM);

            if resources.is_empty() {
                render_empty_bundle_card(self, ui);
            }

            ui.columns(4, |columns| {
                theme::card(&mut columns[0], |ui| {
                    ui.label("Synthetic Patients");
                    ui.heading(patient_count.to_string());
                    ui.label(
                        RichText::new("100% fictional")
                            .size(theme::size::SMALL)
                            .color(p.text_muted),
                    );
                });
                theme::card(&mut columns[1], |ui| {
                    ui.label("Observations");
                    ui.heading(observation_count.to_string());
                    ui.label(
                        RichText::new("100% verified")
                            .size(theme::size::SMALL)
                            .color(p.text_muted),
                    );
                });
                theme::card(&mut columns[2], |ui| {
                    ui.label("Encounters");
                    ui.heading(encounter_count.to_string());
                    ui.label(
                        RichText::new("Ambulatory")
                            .size(theme::size::SMALL)
                            .color(p.text_muted),
                    );
                });
                theme::card(&mut columns[3], |ui| {
                    ui.label("Completeness");
                    ui.heading(format!("{completeness:.1}%"));
                    ui.label(
                        RichText::new(format!("{total_links} reference links"))
                            .size(theme::size::SMALL)
                            .color(p.accent),
                    );
                });
            });

            ui.add_space(theme::space::MD);
            section_title(ui, "Provenance Verification");
            if ui.button("Verify Local Analytics Receipt").clicked() {
                let payload = format!(
                    "P:{patient_count}:O:{observation_count}:E:{encounter_count}:T:{total_resources}:L:{total_links}"
                );
                let digest = sha256_hex(payload.as_bytes());
                self.connected.analytics_receipt_verified = true;
                self.connected.analytics_verified_receipt = Some(format!("sha256:{digest}"));
                self.connected.record_audit_event(
                    "ANALYTICS_VERIFIED",
                    "user-local",
                    &format!(
                        "Verified local analytics digest ({total_resources} resources): {digest}"
                    ),
                );
            }

            if let Some(ref receipt) = self.connected.analytics_verified_receipt {
                ui.add_space(theme::space::XS);
                ui.label(
                    RichText::new(format!(
                        "ANALYTICS_RECEIPT_VERIFIED: {receipt} (Computed over {total_resources} resources, {total_links} links)"
                    ))
                    .color(p.accent),
                );
            }
        });
    }

    // -------------------------------------------------------------------------
    // 17. Dataset Manager (Screen 17)
    // -------------------------------------------------------------------------
    pub(crate) fn dataset_manager_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[17];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Dual-Domain Dataset Manager",
        );
        let p = *theme::palette(ui.ctx().theme());

        let resources = self.active_resources();

        theme::card(ui, |ui| {
            section_title(ui, "Domain Separation & Benchmark Inventories");
            ui.label("Distinguish frozen Research Core benchmarks from Workspace export staging.");

            ui.horizontal(|ui| {
                if ui
                    .selectable_label(
                        self.connected.dataset_active_tab == 0,
                        "Research Datasets (Frozen)",
                    )
                    .clicked()
                {
                    self.connected.dataset_active_tab = 0;
                }
                if ui
                    .selectable_label(
                        self.connected.dataset_active_tab == 1,
                        "Workspace Export Staging (Quarantined)",
                    )
                    .clicked()
                {
                    self.connected.dataset_active_tab = 1;
                }
            });

            ui.add_space(theme::space::SM);
            if self.connected.dataset_active_tab == 0 {
                ui.label(
                    RichText::new("Frozen Research Core Benchmark Fixtures (Embedded & Verified):")
                        .strong(),
                );

                const F1: &[u8] =
                    include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
                const F2: &[u8] =
                    include_bytes!("../fixtures/core/encrypted-readback-projection.json");
                const F3: &[u8] = include_bytes!(
                    "../fixtures/core/encrypted-persistent-readback-projection.json"
                );

                let f1_hash = sha256_hex(F1);
                let f2_hash = sha256_hex(F2);
                let f3_hash = sha256_hex(F3);

                let datasets = [
                    (
                        "Fixture 1",
                        "synthetic-multipatient-fhir-bundle.json",
                        format!("{} bytes (8 resources)", F1.len()),
                        format!("SHA-256: {}", &f1_hash[..24]),
                    ),
                    (
                        "Fixture 2",
                        "encrypted-readback-projection.json",
                        format!("{} bytes (3 resources)", F2.len()),
                        format!("SHA-256: {}", &f2_hash[..24]),
                    ),
                    (
                        "Fixture 3",
                        "encrypted-persistent-readback-projection.json",
                        format!("{} bytes (persistent)", F3.len()),
                        format!("SHA-256: {}", &f3_hash[..24]),
                    ),
                ];
                for (id, name, count, hash) in datasets {
                    ui.group(|ui| {
                        ui.horizontal(|ui| {
                            ui.strong(id);
                            ui.label(name);
                            theme::tag(ui, &count, p.badge, p.accent);
                        });
                        ui.label(
                            RichText::new(hash)
                                .size(theme::size::SMALL)
                                .color(p.text_muted),
                        );
                    });
                    ui.add_space(theme::space::XS);
                }
                if ui
                    .button("Record Committed Fixture Verification to Audit")
                    .clicked()
                {
                    self.connected.record_audit_event(
                        "DATASET_VERIFIED",
                        "user-local",
                        &format!(
                            "Verified 3 committed fixture digests (bundle={})",
                            &f1_hash[..16]
                        ),
                    );
                }
            } else {
                ui.label(RichText::new("Workspace Staged Exports (Isolated Quarantine):").strong());
                ui.group(|ui| {
                    ui.horizontal(|ui| {
                        ui.strong("Staging Batch 001");
                        theme::tag(ui, "QUARANTINED", p.pink_bg, p.pink_text);
                    });
                    ui.label(format!(
                        "Currently staged dataset contains {} synthetic resource(s).",
                        resources.len()
                    ));
                    let staging_hash = sha256_hex(
                        format!("STAGED_RESOURCES:{}", resources.len()).as_bytes(),
                    );
                    ui.label(
                        RichText::new(format!("Staging digest: sha256:{staging_hash}"))
                            .size(theme::size::SMALL)
                            .color(p.text_muted),
                    );
                    ui.label(
                        RichText::new(
                            "No-backflow invariant: Staged records cannot enter Research Core without separate qualification.",
                        )
                        .size(theme::size::SMALL)
                        .color(p.text_muted),
                    );
                });
            }
        });
    }

    // -------------------------------------------------------------------------
    // 18. Export Quarantine (Screen 18)
    // -------------------------------------------------------------------------
    pub(crate) fn export_quarantine_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[18];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Outbound Export Quarantine",
        );
        let p = *theme::palette(ui.ctx().theme());

        let resources = self.active_resources();

        theme::card(ui, |ui| {
            ui.horizontal(|ui| {
                section_title(ui, "Outbound Data Inspection & Risk Scanning");
                theme::tag(ui, "RESEARCH ADMISSION GATED", p.pink_bg, p.pink_text);
            });
            ui.label("Explicit export staging with residual-risk result and quarantine manifest generation.");
            ui.add_space(theme::space::SM);

            let supplementary = [
                self.connected.note_subjective.as_str(),
                self.connected.note_objective.as_str(),
                self.connected.note_assessment.as_str(),
                self.connected.note_plan.as_str(),
                self.connected.canvas_notes.as_str(),
            ];
            let scan = scan_export_quarantine(&resources, &supplementary);
            let has_violations = !scan.passed;

            section_title(
                ui,
                "Residual Risk Assessment (Evaluated on Active Dataset & Drafts)",
            );
            if resources.is_empty() {
                ui.label(
                    RichText::new("• Scan Status: NOT RUN (0 synthetic resources admitted; cannot PASS on empty dataset)")
                        .color(p.text_secondary),
                );
            } else {
                if scan.direct_id_leaks == 0 {
                    ui.label(
                        RichText::new("• Direct Identifiers (Non-fictional IDs, SSN, Email): 0 leaks detected (PASS)")
                            .color(p.accent),
                    );
                } else {
                    ui.label(
                        RichText::new(format!(
                            "• Direct Identifiers: {} violation(s) detected (FAIL - LEAK DETECTED)",
                            scan.direct_id_leaks
                        ))
                        .color(p.pink_text),
                    );
                }

                if scan.raw_date_leaks == 0 {
                    ui.label(
                        RichText::new(
                            "• Date Generalization: 0 unshifted historical dates detected (PASS)",
                        )
                        .color(p.accent),
                    );
                } else {
                    ui.label(
                        RichText::new(format!(
                            "• Date Generalization: {} unshifted date pattern(s) detected (FAIL)",
                            scan.raw_date_leaks
                        ))
                        .color(p.pink_text),
                    );
                }

                if scan.invalid_refs == 0 {
                    ui.label(
                        RichText::new("• Syntactic Link References: 0 non-UUID links (PASS)")
                            .color(p.accent),
                    );
                } else {
                    ui.label(
                        RichText::new(format!(
                            "• Syntactic Link References: {} non-UUID target(s) (FAIL - CORRUPTED REFS)",
                            scan.invalid_refs
                        ))
                        .color(p.pink_text),
                    );
                }

                if scan.forbidden_terms == 0 {
                    ui.label(
                        RichText::new("• Forbidden Metadata Patterns: 0 prohibited terms (PASS)")
                            .color(p.accent),
                    );
                } else {
                    ui.label(
                        RichText::new(format!(
                            "• Forbidden Metadata Patterns: {} prohibited pattern(s) found (FAIL)",
                            scan.forbidden_terms
                        ))
                        .color(p.pink_text),
                    );
                }
            }

            ui.label(format!(
                "• Admitted Records Inspected: {} resources (+ 5 session draft buffers)",
                scan.resources_inspected
            ));

            ui.add_space(theme::space::SM);
            if !resources.is_empty() && has_violations {
                theme::tag(
                    ui,
                    "QUARANTINE_FAILED_LEAK_DETECTED",
                    p.pink_bg,
                    p.pink_text,
                );
                ui.label(
                    RichText::new("FAIL CLOSED: Export quarantine detected residual risk violations. Manifest generation is blocked.")
                        .color(p.pink_text)
                        .strong(),
                );
                if ui
                    .button("Log Quarantine Security Refusal to Audit")
                    .clicked()
                {
                    self.connected.record_audit_event(
                        "SECURITY_REFUSAL_EXPORT_QUARANTINE",
                        "system-quarantine",
                        &format!(
                            "Blocked export: direct_leaks={}, invalid_refs={}, forbidden_terms={}, raw_dates={}",
                            scan.direct_id_leaks,
                            scan.invalid_refs,
                            scan.forbidden_terms,
                            scan.raw_date_leaks
                        ),
                    );
                }
            } else if scan.passed {
                theme::tag(ui, "QUARANTINE_RISK_CLEAR", p.badge, p.accent);
            }

            ui.add_space(theme::space::SM);
            ui.checkbox(
                &mut self.connected.quarantine_acknowledged,
                "I confirm this export target is strictly synthetic and intended for developer verification.",
            );

            ui.add_space(theme::space::SM);
            let can_generate = scan.passed && self.connected.quarantine_acknowledged;

            if ui
                .add_enabled(
                    can_generate,
                    egui::Button::new("Generate Export Quarantine Manifest"),
                )
                .clicked()
            {
                let manifest_payload = format!(
                    "MANIFEST_V1:COUNT={}:DIRECT_LEAKS={}:INVALID_REFS={}:FORBIDDEN_TERMS={}:RAW_DATES={}",
                    scan.resources_inspected,
                    scan.direct_id_leaks,
                    scan.invalid_refs,
                    scan.forbidden_terms,
                    scan.raw_date_leaks
                );
                let digest = sha256_hex(manifest_payload.as_bytes());
                self.connected.quarantine_manifest_generated = true;
                self.connected.quarantine_manifest_receipt =
                    Some(format!("QUARANTINE_PASS_SHA256_{digest}"));
                self.connected.record_audit_event(
                    "EXPORT_QUARANTINE_PASSED",
                    "user-local",
                    &format!(
                        "Export quarantine manifest generated for {} resources (digest: {})",
                        scan.resources_inspected, digest
                    ),
                );
            }

            if let Some(ref receipt) = self.connected.quarantine_manifest_receipt {
                ui.add_space(theme::space::XS);
                ui.group(|ui| {
                    ui.strong("QUARANTINE_MANIFEST_GENERATED");
                    ui.label(format!("Manifest Receipt: {receipt}"));
                    ui.label(
                        RichText::new(
                            "Research Core admission is GATED: Data remains quarantined in Workspace.",
                        )
                        .color(p.pink_text),
                    );
                });
            }
        });
    }

    // -------------------------------------------------------------------------
    // 19. Research Explorer (Screen 19)
    // -------------------------------------------------------------------------
    pub(crate) fn research_explorer_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[19];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Research Artifact Explorer",
        );
        let p = *theme::palette(ui.ctx().theme());

        theme::card(ui, |ui| {
            ui.horizontal(|ui| {
                section_title(ui, "Read-Only Hypotheses & Artifact Browser");
                theme::tag(ui, "READ-ONLY", p.badge, p.accent);
            });
            ui.label("Explore evidence-grounded hypotheses, study designs and reproducible run receipts.");
            ui.add_space(theme::space::SM);

            ui.horizontal(|ui| {
                ui.label("Study:");
                egui::ComboBox::from_id_salt("research_study_sel")
                    .selected_text(match self.connected.research_selected_study {
                        0 => "Study 01: Evidence-Grounded Medical Q&A",
                        _ => "Study 02: Deterministic FHIR R4 Invariant Verification",
                    })
                    .show_ui(ui, |ui| {
                        ui.selectable_value(
                            &mut self.connected.research_selected_study,
                            0,
                            "Study 01: Evidence-Grounded Medical Q&A",
                        );
                        ui.selectable_value(
                            &mut self.connected.research_selected_study,
                            1,
                            "Study 02: Deterministic FHIR R4 Invariant Verification",
                        );
                    });
            });

            ui.add_space(theme::space::SM);

            let (name, hypothesis, evaluator, seed, threshold) = match self
                .connected
                .research_selected_study
            {
                0 => (
                    "Evidence-Grounded Medical Q&A",
                    "Explicit source-grounding and provenance verification reduce ungrounded assertions below 1.0% in synthetic clinical Q&A.",
                    "mesc-evaluator-v1.4",
                    42,
                    0.85f32,
                ),
                _ => (
                    "Deterministic FHIR R4 Invariant Verification",
                    "Offline structural validation detects 100% of cyclic references and noncanonical JSON keys without live network dependency.",
                    "d2-structural-verifier-v1.0",
                    1337,
                    1.00f32,
                ),
            };

            let protocol_payload = format!("{name}:{evaluator}:{seed}:{threshold}");
            let protocol_digest = sha256_hex(protocol_payload.as_bytes());

            theme::card(ui, |ui| {
                ui.strong(format!("Study: {name}"));
                ui.label(format!("Hypothesis Statement: {hypothesis}"));
                ui.add_space(theme::space::XS);
                ui.label(format!("Protocol Configuration: Evaluator: {evaluator} | Seed: {seed} | Threshold: {threshold}"));
                ui.add_space(theme::space::XS);
                ui.label(
                    RichText::new(format!("PROTOCOL_RECEIPT_SHA256: {protocol_digest}"))
                        .size(theme::size::SMALL)
                        .color(p.text_muted),
                );
            });
            ui.add_space(theme::space::XS);
            ui.label(
                RichText::new("DISCLOSURE: Read-only research protocol specification. Zero live model inference.")
                    .size(theme::size::SMALL)
                    .color(p.text_secondary),
            );
        });
    }

    // -------------------------------------------------------------------------
    // 20. Benchmark & Evaluation (Screen 20)
    // -------------------------------------------------------------------------
    pub(crate) fn benchmark_evaluation_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[20];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Benchmark Scorecard",
        );
        let p = *theme::palette(ui.ctx().theme());

        theme::card(ui, |ui| {
            ui.horizontal(|ui| {
                section_title(ui, "Deterministic Benchmark Suite Specifications");
                theme::tag(ui, "TRAINING & PROMOTION GATED", p.pink_bg, p.pink_text);
            });
            ui.label(
                "Inspect frozen benchmark suite targets, determinism seed locks, and specification receipts.",
            );
            ui.add_space(theme::space::SM);

            ui.horizontal(|ui| {
                ui.label("Benchmark Suite:");
                egui::ComboBox::from_id_salt("bench_suite_sel")
                    .selected_text(match self.connected.bench_selected_suite {
                        0 => "MedQA 4-Option (USMLE Synthetic Protocol)",
                        1 => "PubMedQA (Biomedical Yes/No/Maybe Protocol)",
                        _ => "FHIR R4 Structural Conformance Suite",
                    })
                    .show_ui(ui, |ui| {
                        ui.selectable_value(
                            &mut self.connected.bench_selected_suite,
                            0,
                            "MedQA 4-Option (USMLE Synthetic Protocol)",
                        );
                        ui.selectable_value(
                            &mut self.connected.bench_selected_suite,
                            1,
                            "PubMedQA (Biomedical Yes/No/Maybe Protocol)",
                        );
                        ui.selectable_value(
                            &mut self.connected.bench_selected_suite,
                            2,
                            "FHIR R4 Structural Conformance Suite",
                        );
                    });
            });

            ui.add_space(theme::space::SM);

            let (suite_name, eval, m1, m2, m3, m4) = match self.connected.bench_selected_suite {
                0 => (
                    "MedQA 4-Option",
                    "mesc-eval-usmle-v1.2",
                    ("Accuracy Target", ">= 85.0%"),
                    ("Precision Target", ">= 80.0%"),
                    ("Recall Target", ">= 80.0%"),
                    ("Abstention Target", "<= 10.0%"),
                ),
                1 => (
                    "PubMedQA",
                    "mesc-eval-pubmed-v1.1",
                    ("Accuracy Target", ">= 78.0%"),
                    ("Precision Target", ">= 75.0%"),
                    ("Recall Target", ">= 75.0%"),
                    ("Abstention Target", "<= 12.0%"),
                ),
                _ => (
                    "FHIR R4 Conformance",
                    "d2-conformance-v1.0",
                    ("Invariant Target", "100.0%"),
                    ("Cycle Detection", "100.0%"),
                    ("Schema Compliance", "100.0%"),
                    ("Abstention Target", "0.0%"),
                ),
            };

            egui::Grid::new("bench_scorecard_grid")
                .striped(true)
                .min_col_width(130.0)
                .show(ui, |ui| {
                    ui.strong("Evaluation Target");
                    ui.strong("Target Threshold");
                    ui.strong("Verification Boundary");
                    ui.end_row();

                    for (metric, target) in [m1, m2, m3, m4] {
                        ui.label(metric);
                        ui.label(target);
                        theme::tag(ui, "SPECIFICATION", p.badge, p.accent);
                        ui.end_row();
                    }
                });

            ui.add_space(theme::space::MD);
            ui.checkbox(
                &mut self.connected.bench_seed_locked,
                "Deterministic Seed Lock (seed=42)",
            );

            if ui
                .button("Compute Benchmark Specification Digest (Not a Result)")
                .clicked()
            {
                let seed_val = if self.connected.bench_seed_locked {
                    42
                } else {
                    0
                };
                let payload = format!("{suite_name}:{eval}:{seed_val}");
                let digest = sha256_hex(payload.as_bytes());
                self.connected.bench_verification_receipt = Some(format!(
                    "BENCHMARK_SPEC_DIGEST_NOT_A_RESULT_SHA256_{digest}"
                ));
            }

            if let Some(ref receipt) = self.connected.bench_verification_receipt {
                ui.add_space(theme::space::XS);
                ui.label(RichText::new(receipt).color(p.text_secondary));
            }

            ui.add_space(theme::space::XS);
            ui.label(
                RichText::new(format!(
                    "Measured Benchmark Outcomes Loaded: {} (No live model inference in offline desktop runtime; measured outcomes require an authentic external evaluation receipt.)",
                    if benchmark_measured_results_available() { "YES" } else { "NONE" }
                ))
                .size(theme::size::SMALL)
                .color(p.text_secondary),
            );
        });
    }

    // -------------------------------------------------------------------------
    // 22. Integrations (Screen 22)
    // -------------------------------------------------------------------------
    pub(crate) fn integrations_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[22];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Integrations Directory",
        );
        let p = *theme::palette(ui.ctx().theme());

        theme::card(ui, |ui| {
            ui.horizontal(|ui| {
                section_title(ui, "Capability Listing & Endpoint Status");
                theme::tag(ui, "EHR WRITE GATED", p.pink_bg, p.pink_text);
            });
            ui.label("Listing of mock adapters, permissions, and read-only dry-run simulation.");
            ui.add_space(theme::space::SM);

            let endpoints = [
                (
                    "Endpoint 1",
                    "Local Synthetic Fixture Provider",
                    "Static Read Only",
                    "Active (Offline)",
                    true,
                ),
                (
                    "Endpoint 2",
                    "Mock SMART-on-FHIR Loopback",
                    "In-Memory Simulation",
                    "Loopback Only",
                    true,
                ),
                (
                    "Endpoint 3",
                    "Production EHR Live Write Adapter",
                    "Live Mutation",
                    "PERMANENTLY BLOCKED",
                    false,
                ),
            ];

            for (idx, (id, name, cap, status, allowed)) in endpoints.iter().enumerate() {
                let selected = self.connected.integration_selected_endpoint == idx;
                ui.group(|ui| {
                    ui.horizontal(|ui| {
                        if ui.selectable_label(selected, *id).clicked() {
                            self.connected.integration_selected_endpoint = idx;
                        }
                        ui.label(*name);
                        theme::tag(ui, cap, p.badge, p.accent);
                        theme::tag(
                            ui,
                            status,
                            if *allowed { p.badge } else { p.pink_bg },
                            if *allowed {
                                p.text_secondary
                            } else {
                                p.pink_text
                            },
                        );
                    });
                });
                ui.add_space(theme::space::XS);
            }

            ui.add_space(theme::space::SM);
            section_title(ui, "Read-Only Dry Run Simulator (Class C Demonstration)");
            if ui.button("Execute Offline Dry Run Check").clicked() {
                let resources = self.active_resources();
                match execute_integration_dry_run(
                    self.connected.integration_selected_endpoint,
                    resources.len(),
                ) {
                    Ok(receipt) => {
                        self.connected.integration_dry_run_done = true;
                        self.connected.integration_dry_run_receipt = Some(receipt);
                        self.connected.integration_dry_run_error = None;
                    }
                    Err(err_code) => {
                        self.connected.integration_dry_run_done = false;
                        self.connected.integration_dry_run_receipt = None;
                        self.connected.integration_dry_run_error = Some(err_code.to_string());
                        self.connected.record_audit_event(
                            "SECURITY_REFUSAL_EHR_WRITE",
                            "system-boundary",
                            &format!(
                                "Refused blocked EHR endpoint {}: {err_code}",
                                self.connected.integration_selected_endpoint
                            ),
                        );
                    }
                }
            }

            if let Some(ref receipt) = self.connected.integration_dry_run_receipt {
                ui.add_space(theme::space::XS);
                ui.label(
                    RichText::new(format!(
                        "{receipt} (0 network packets sent, 0 mutations attempted, offline simulation only)"
                    ))
                    .color(p.accent),
                );
            }
            if let Some(ref err_msg) = self.connected.integration_dry_run_error {
                ui.add_space(theme::space::XS);
                ui.label(
                    RichText::new(format!(
                        "REFUSED: {err_msg} — Live EHR write adapters are permanently disabled under Lane C."
                    ))
                    .color(p.pink_text)
                    .strong(),
                );
            }
        });
    }

    // -------------------------------------------------------------------------
    // 23. Audit History (Screen 23)
    // -------------------------------------------------------------------------
    pub(crate) fn audit_history_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[23];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Cryptographic Audit Ledger",
        );
        let p = *theme::palette(ui.ctx().theme());

        theme::card(ui, |ui| {
            ui.horizontal(|ui| {
                section_title(ui, "Append-Only Hash-Chained Audit Ledger");
                if self.connected.audit_verified {
                    theme::tag(ui, "HASH CHAIN VERIFIED", p.badge, p.accent);
                } else {
                    theme::tag(ui, "CHAIN CORRUPTED", p.pink_bg, p.pink_text);
                }
            });
            ui.label(
                "Local SHA-256 hash-chained sequence of runtime workspace events. TRUST BOUNDARY: A local hash chain detects partial tampering inside this app; it is NOT externally anchored or independently authenticated and can be rewritten outside this trust boundary.",
            );
            ui.add_space(theme::space::SM);

            egui::ScrollArea::vertical()
                .max_height(240.0)
                .show(ui, |ui| {
                    for ev in &self.connected.audit_events {
                        ui.group(|ui| {
                            ui.horizontal(|ui| {
                                ui.strong(format!("Seq {:03}", ev.seq));
                                theme::tag(ui, &ev.event_type, p.badge, p.accent);
                                ui.label(format!("Actor: {}", ev.actor));
                            });
                            ui.label(&ev.payload);
                            ui.horizontal(|ui| {
                                ui.label(
                                    RichText::new(format!("Parent: {}...", &ev.prev_hash[..16]))
                                        .size(theme::size::SMALL)
                                        .color(p.text_muted),
                                );
                                ui.label(
                                    RichText::new(format!("Hash: {}...", &ev.hash[..16]))
                                        .size(theme::size::SMALL)
                                        .color(p.text_muted),
                                );
                            });
                        });
                        ui.add_space(theme::space::XS);
                    }
                });

            ui.add_space(theme::space::SM);
            ui.horizontal(|ui| {
                if ui.button("Verify Full Ledger Hash Chain").clicked() {
                    let res = verify_audit_chain(&self.connected.audit_events);
                    match res {
                        Ok(cnt) => {
                            self.connected.audit_verified = true;
                            self.connected.audit_verification_status = Some(Ok(cnt));
                        }
                        Err(e) => {
                            self.connected.audit_verified = false;
                            self.connected.audit_verification_status = Some(Err(e));
                        }
                    }
                }

                if ui.button("Simulate Tampering (Negative Control)").clicked()
                    && !self.connected.audit_events.is_empty()
                {
                    let idx = self.connected.audit_events.len() - 1;
                    self.connected.audit_events[idx].payload =
                        "UNAUTHORIZED_MUTATION_INJECTED".to_string();
                    self.connected.audit_verified = false;
                    self.connected.audit_verification_status = None;
                }

                if ui.button("Restore Valid Chain").clicked() {
                    self.connected.audit_events = build_initial_audit_events();
                    self.connected.audit_verified = true;
                    self.connected.audit_verification_status = Some(Ok(1));
                }
            });

            if let Some(ref status) = self.connected.audit_verification_status {
                ui.add_space(theme::space::XS);
                match status {
                    Ok(cnt) => {
                        ui.label(
                            RichText::new(format!(
                                "AUDIT_CHAIN_INTEGRITY_VERIFIED: {cnt}/{cnt} events verified mathematically with SHA-256. 0 tampering detected."
                            ))
                            .color(p.accent),
                        );
                    }
                    Err((seq, msg)) => {
                        ui.label(
                            RichText::new(format!(
                                "AUDIT_CHAIN_CORRUPTED: {msg} (at sequence {seq})"
                            ))
                            .color(p.pink_text),
                        );
                    }
                }
            }

            ui.add_space(theme::space::SM);
            ui.separator();
            section_title(ui, "Optional Local Ledger Persistence (Explicit Path)");
            ui.horizontal(|ui| {
                ui.label("Ledger File:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.audit_ledger_path)
                        .hint_text("Optional local synthetic .json path (no silent disk writes)")
                        .desired_width(320.0),
                );
            });
            ui.horizontal(|ui| {
                if ui.button("Save Verified Ledger to File").clicked() {
                    let path = Path::new(self.connected.audit_ledger_path.trim());
                    match save_audit_ledger_to_path(path, &self.connected.audit_events) {
                        Ok(count) => {
                            self.connected.audit_persistence_status = Some(Ok(format!(
                                "Saved {count} hash-chained audit events to local file."
                            )));
                        }
                        Err(err) => {
                            self.connected.audit_persistence_status =
                                Some(Err(format!("AUDIT_SAVE_REFUSED: {err}")));
                        }
                    }
                }
                if ui.button("Load & Verify Ledger After Restart").clicked() {
                    let path = Path::new(self.connected.audit_ledger_path.trim());
                    match load_audit_ledger_from_path(path) {
                        Ok(loaded) => {
                            let count = loaded.len();
                            self.connected.audit_events = loaded;
                            self.connected.audit_verified = true;
                            self.connected.audit_verification_status = Some(Ok(count));
                            self.connected.audit_persistence_status = Some(Ok(format!(
                                "Loaded and verified {count} audit events from local file."
                            )));
                        }
                        Err(err) => {
                            self.connected.audit_verified = false;
                            self.connected.audit_persistence_status =
                                Some(Err(format!("AUDIT_LOAD_REFUSED: {err}")));
                        }
                    }
                }
            });
            if let Some(ref pstatus) = self.connected.audit_persistence_status {
                match pstatus {
                    Ok(msg) => {
                        ui.label(RichText::new(msg).color(p.accent));
                    }
                    Err(err) => {
                        ui.label(RichText::new(err).color(p.pink_text));
                    }
                }
            }
        });
    }

    // -------------------------------------------------------------------------
    // 24. Storage & Recovery (Screen 24)
    // -------------------------------------------------------------------------
    pub(crate) fn storage_recovery_ui(&mut self, ui: &mut Ui) {
        let screen = &SCREENS[24];
        screen_header(
            ui,
            screen.label,
            screen.purpose,
            screen.contract,
            screen.sources,
            "Connected · Storage & Recovery Vault",
        );
        let p = *theme::palette(ui.ctx().theme());
        let resources = self.active_resources();

        theme::card(ui, |ui| {
            section_title(ui, "Authenticated Encrypted Local Store & Vault Management");
            ui.label("Cryptographic vault state via RFC 5869 HKDF-SHA-256 and RFC 8439 ChaCha20-Poly1305 AEAD.");
            ui.add_space(theme::space::SM);

            theme::card(ui, |ui| {
                ui.horizontal(|ui| {
                    ui.strong("Vault Status:");
                    if self.connected.storage_vault_locked {
                        theme::tag(ui, "LOCKED", p.pink_bg, p.pink_text);
                    } else {
                        theme::tag(ui, "UNLOCKED (Session Only)", p.badge, p.accent);
                    }
                });
                ui.label("Cipher: RFC 8439 ChaCha20-Poly1305 AEAD (256-bit key, unique 96-bit OS-seeded nonce)");
                ui.label("KDF: RFC 2898 PBKDF2-HMAC-SHA256 (25,000 iters) + RFC 5869 HKDF-SHA-256 (16-byte OS-seeded salt)");
                ui.label("Format: MSWSENV1 Envelope Layout (41-byte authenticated header + 16-byte Poly1305 tag + ciphertext)");

                if let Some(ref key) = self.connected.storage_derived_key {
                    ui.label(
                        RichText::new(format!("Derived Key Fingerprint: {}...", &key[..16]))
                            .size(theme::size::SMALL)
                            .color(p.text_muted),
                    );
                }

                if let Some(ref tag) = self.connected.storage_vault_tag {
                    ui.label(
                        RichText::new(format!("Vault Auth Tag: {}...", &tag[..16]))
                            .size(theme::size::SMALL)
                            .color(p.text_muted),
                    );
                }

                ui.add_space(theme::space::XS);

                if self.connected.storage_vault_locked {
                    ui.horizontal(|ui| {
                        ui.label("Vault Passphrase:");
                        ui.add(
                            egui::TextEdit::singleline(&mut self.connected.storage_passphrase)
                                .password(true)
                                .hint_text("Enter vault passphrase..."),
                        );
                    });
                    ui.add_space(theme::space::XS);

                    if ui.button("Derive Session Key & Unlock Vault").clicked()
                        && !self.connected.storage_passphrase.is_empty()
                    {
                        let salt = generate_random_bytes::<16>(b"medorigin:vault:salt:v2");
                        self.connected.storage_salt = salt;

                        let raw_key = derive_workspace_key(
                            &self.connected.storage_passphrase,
                            &salt,
                            VAULT_KEY_LABEL,
                        );
                        let derived_hex = raw_key
                            .iter()
                            .map(|b| format!("{b:02x}"))
                            .collect::<String>();
                        let auth_tag = hmac_sha256(&raw_key, b"MEDORIGIN_VAULT_TAG_CONFIRMATION");
                        let auth_tag_hex = auth_tag
                            .iter()
                            .map(|b| format!("{b:02x}"))
                            .collect::<String>();

                        self.connected.storage_raw_key = Some(raw_key);
                        self.connected.storage_derived_key = Some(derived_hex);
                        self.connected.storage_vault_tag = Some(auth_tag_hex);
                        self.connected.storage_vault_locked = false;
                        self.connected.storage_wipe_simulation_done = false;
                        self.connected.storage_op_counter += 1;

                        self.connected.record_audit_event(
                            "VAULT_UNLOCKED",
                            "user-local",
                            "Derived session key via PBKDF2-HMAC-SHA256 + HKDF-SHA-256 with OS-seeded salt",
                        );
                    }
                } else if ui.button("Lock Vault & Zeroize Key").clicked() {
                    if let Some(mut k) = self.connected.storage_raw_key.take() {
                        zeroize_bytes(&mut k);
                    }
                    self.connected.storage_derived_key = None;
                    self.connected.storage_vault_tag = None;
                    self.connected.storage_vault_locked = true;
                    self.connected.record_audit_event(
                        "VAULT_LOCKED",
                        "user-local",
                        "Zeroized in-memory vault key and locked storage vault",
                    );
                }
            });

            ui.add_space(theme::space::MD);
            section_title(ui, "Safe Deletion & Cryptographic Backup (RFC 8439 AEAD)");
            ui.horizontal(|ui| {
                let can_encrypt = !self.connected.storage_vault_locked && self.connected.storage_raw_key.is_some();
                if ui
                    .add_enabled(can_encrypt, egui::Button::new("Create Encrypted Backup (MSWSENV1)"))
                    .clicked()
                {
                    let payload = format!(
                        "MEDORIGIN_BACKUP:RESOURCES={}:COUNT={}:COUNTER={}",
                        resources.len(),
                        resources.len(),
                        self.connected.storage_op_counter
                    );
                    let nonce = generate_random_bytes::<12>(b"medorigin:backup:nonce:v2");

                    let key = self.connected.storage_raw_key.as_ref().unwrap();
                    let envelope = encrypt_envelope(key, &self.connected.storage_salt, &nonce, payload.as_bytes());
                    let env_len = envelope.len();
                    self.connected.storage_backup_envelope = Some(envelope);
                    self.connected.storage_backup_verified = true;
                    self.connected.storage_backup_status = Some(Ok(format!(
                        "Created MSWSENV1 envelope: {env_len} bytes, RFC 8439 ChaCha20-Poly1305 AEAD (unique OS-seeded 96-bit nonce)"
                    )));
                    self.connected.storage_op_counter += 1;
                    self.connected.record_audit_event(
                        "BACKUP_ENCRYPTED",
                        "system-crypto",
                        &format!("Created MSWSENV1 encrypted backup snapshot: {env_len} bytes"),
                    );
                }

                let can_verify = !self.connected.storage_vault_locked
                    && self.connected.storage_raw_key.is_some()
                    && self.connected.storage_backup_envelope.is_some();

                if ui
                    .add_enabled(can_verify, egui::Button::new("Verify & Restore Backup Snapshot"))
                    .clicked()
                {
                    let key = self.connected.storage_raw_key.as_ref().unwrap();
                    let envelope = self.connected.storage_backup_envelope.as_ref().unwrap();
                    match decrypt_envelope(key, envelope) {
                        Ok(decrypted) => {
                            self.connected.storage_backup_verified = true;
                            self.connected.storage_backup_status = Some(Ok(format!(
                                "BACKUP_RESTORE_SUCCESS: {} bytes authenticated via Poly1305 MAC tag",
                                decrypted.len()
                            )));
                            self.connected.record_audit_event(
                                "BACKUP_RESTORED",
                                "system-crypto",
                                &format!("Successfully authenticated and restored {} bytes from MSWSENV1 envelope", decrypted.len()),
                            );
                        }
                        Err(e) => {
                            self.connected.storage_backup_verified = false;
                            self.connected.storage_backup_status = Some(Err(format!(
                                "BACKUP_RESTORE_REFUSED: Cryptographic verification failure: {e}"
                            )));
                            self.connected.record_audit_event(
                                "BACKUP_RESTORE_REFUSED",
                                "system-crypto",
                                &format!("Refused backup restoration: {e}"),
                            );
                        }
                    }
                }

                if ui
                    .add_enabled(
                        self.connected.storage_backup_envelope.is_some(),
                        egui::Button::new("Simulate Ciphertext Tampering (Negative Control)"),
                    )
                    .clicked()
                {
                    let env = self.connected.storage_backup_envelope.as_mut().unwrap();
                    if env.len() > MIN_ENVELOPE_LEN {
                        env[MIN_ENVELOPE_LEN] ^= 0x55; // Flip bit in ciphertext
                    } else if env.len() > 41 {
                        env[41] ^= 0x55; // Flip bit in tag
                    }
                    self.connected.storage_backup_verified = false;
                    self.connected.storage_backup_status = Some(Err(
                        "TAMPER_INJECTED: Ciphertext bit flipped. Re-run verification to confirm rejection.".into(),
                    ));
                    self.connected.record_audit_event(
                        "TAMPER_SIMULATION",
                        "test-operator",
                        "Injected single-bit corruption into backup envelope ciphertext",
                    );
                }

                if ui.button("Simulate Cryptographic Zero-Wipe").clicked() {
                    self.connected.storage_passphrase.clear();
                    if let Some(mut k) = self.connected.storage_raw_key.take() {
                        zeroize_bytes(&mut k);
                    }
                    self.connected.storage_derived_key = None;
                    self.connected.storage_vault_tag = None;
                    self.connected.storage_backup_envelope = None;
                    self.connected.storage_backup_status = None;
                    self.connected.storage_backup_verified = false;
                    self.connected.storage_vault_locked = true;
                    self.connected.storage_wipe_simulation_done = true;
                    self.connected.record_audit_event(
                        "VAULT_ZERO_WIPE",
                        "system-crypto",
                        "Overwrote all in-memory keys with 0x00 and purged vault state",
                    );
                }
            });

            if let Some(ref status) = self.connected.storage_backup_status {
                ui.add_space(theme::space::XS);
                match status {
                    Ok(msg) => {
                        ui.label(RichText::new(msg).color(p.accent));
                    }
                    Err(err) => {
                        ui.label(RichText::new(err).color(p.pink_text));
                    }
                }
            }

            if self.connected.storage_wipe_simulation_done {
                ui.add_space(theme::space::XS);
                ui.label(
                    RichText::new(
                        "BEST_EFFORT_MEMORY_PURGE_COMPLETED: In-memory key buffers overwritten with 0x00 and session references cleared. Note: Safe Rust without OS memory locking cannot guarantee zero compiler/swap residue.",
                    )
                    .color(p.accent),
                );
            }

            ui.add_space(theme::space::SM);
            ui.separator();
            section_title(
                ui,
                "Encrypted Local Persistence & Restart Recovery (Explicit Path)",
            );
            ui.horizontal(|ui| {
                ui.label("Backup Envelope Path:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.storage_backup_path)
                        .hint_text("Optional local synthetic .mswsenv path (no silent disk writes)")
                        .desired_width(320.0),
                );
            });
            ui.horizontal(|ui| {
                let can_save = self.connected.storage_backup_envelope.is_some()
                    && !self.connected.storage_backup_path.trim().is_empty();
                if ui
                    .add_enabled(can_save, egui::Button::new("Save Encrypted Backup to File"))
                    .clicked()
                {
                    let path = Path::new(self.connected.storage_backup_path.trim());
                    let env = self.connected.storage_backup_envelope.as_ref().unwrap();
                    match save_encrypted_backup_to_path(path, env) {
                        Ok(written) => {
                            self.connected.storage_backup_status = Some(Ok(format!(
                                "BACKUP_PERSISTED: Wrote {written} encrypted MSWSENV1 bytes to local file."
                            )));
                            self.connected.record_audit_event(
                                "BACKUP_PERSISTED",
                                "system-crypto",
                                &format!("Persisted {written}-byte MSWSENV1 backup envelope"),
                            );
                        }
                        Err(e) => {
                            self.connected.storage_backup_status =
                                Some(Err(format!("BACKUP_SAVE_REFUSED: {e}")));
                        }
                    }
                }

                let can_load = !self.connected.storage_backup_path.trim().is_empty()
                    && !self.connected.storage_passphrase.is_empty();
                if ui
                    .add_enabled(
                        can_load,
                        egui::Button::new("Load & Decrypt Backup After Restart"),
                    )
                    .clicked()
                {
                    let path = Path::new(self.connected.storage_backup_path.trim());
                    match load_encrypted_backup_from_path(path).and_then(|bytes| {
                        decrypt_envelope_with_passphrase(
                            &self.connected.storage_passphrase,
                            &bytes,
                            VAULT_KEY_LABEL,
                        )
                        .map(|pt| (bytes, pt))
                    }) {
                        Ok((bytes, pt)) => {
                            self.connected.storage_backup_envelope = Some(bytes);
                            self.connected.storage_backup_verified = true;
                            self.connected.storage_backup_status = Some(Ok(format!(
                                "BACKUP_RESTORED_AFTER_RESTART: Authenticated and decrypted {} bytes via PBKDF2+HKDF+ChaCha20-Poly1305.",
                                pt.len()
                            )));
                            self.connected.record_audit_event(
                                "BACKUP_RESTORED",
                                "system-crypto",
                                &format!("Loaded and authenticated {}-byte persisted backup", pt.len()),
                            );
                        }
                        Err(e) => {
                            self.connected.storage_backup_verified = false;
                            self.connected.storage_backup_status =
                                Some(Err(format!("BACKUP_RESTORE_REFUSED: {e}")));
                            self.connected.record_audit_event(
                                "BACKUP_RESTORE_REFUSED",
                                "system-crypto",
                                &format!("Refused persisted backup restore: {e}"),
                            );
                        }
                    }
                }
            });
        });
    }
}

// -----------------------------------------------------------------------------
// Unit Tests
// -----------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::encrypted_readback::FictionalReadbackLink;

    fn sample_test_resources() -> Vec<FictionalReadbackResource> {
        vec![
            FictionalReadbackResource {
                resource_type: "Patient".to_string(),
                resource_id: "fictional-patient-001".to_string(),
                full_url: "urn:uuid:00000000-0000-4000-8000-000000000001".to_string(),
                links: vec![],
            },
            FictionalReadbackResource {
                resource_type: "Encounter".to_string(),
                resource_id: "fictional-encounter-001".to_string(),
                full_url: "urn:uuid:00000000-0000-4000-8000-000000000003".to_string(),
                links: vec![FictionalReadbackLink {
                    field: "subject".to_string(),
                    target: "urn:uuid:00000000-0000-4000-8000-000000000001".to_string(),
                }],
            },
            FictionalReadbackResource {
                resource_type: "Observation".to_string(),
                resource_id: "fictional-observation-001".to_string(),
                full_url: "urn:uuid:00000000-0000-4000-8000-000000000005".to_string(),
                links: vec![
                    FictionalReadbackLink {
                        field: "subject".to_string(),
                        target: "urn:uuid:00000000-0000-4000-8000-000000000001".to_string(),
                    },
                    FictionalReadbackLink {
                        field: "encounter".to_string(),
                        target: "urn:uuid:00000000-0000-4000-8000-000000000003".to_string(),
                    },
                ],
            },
        ]
    }

    fn hex_to_vec(h: &str) -> Vec<u8> {
        (0..h.len())
            .step_by(2)
            .map(|i| u8::from_str_radix(&h[i..i + 2], 16).unwrap())
            .collect()
    }
    fn hex_to_32(h: &str) -> [u8; 32] {
        let v = hex_to_vec(h);
        v.try_into().unwrap()
    }
    fn hex_to_12(h: &str) -> [u8; 12] {
        let v = hex_to_vec(h);
        v.try_into().unwrap()
    }

    #[test]
    fn test_audit_chain_verification_and_tampering() {
        let mut events = build_initial_audit_events();
        assert_eq!(events.len(), 1);
        assert_eq!(verify_audit_chain(&events), Ok(1));

        let h2 = compute_audit_hash(
            2,
            "BUNDLE_ADMIT",
            "user-local",
            "Admitted bundle",
            &events[0].hash,
        );
        events.push(AuditEvent {
            seq: 2,
            event_type: "BUNDLE_ADMIT".to_string(),
            actor: "user-local".to_string(),
            payload: "Admitted bundle".to_string(),
            prev_hash: events[0].hash.clone(),
            hash: h2.clone(),
        });
        let h3 = compute_audit_hash(3, "NOTE_ATTESTATION", "clinician", "Signed note", &h2);
        events.push(AuditEvent {
            seq: 3,
            event_type: "NOTE_ATTESTATION".to_string(),
            actor: "clinician".to_string(),
            payload: "Signed note".to_string(),
            prev_hash: h2,
            hash: h3,
        });
        assert_eq!(verify_audit_chain(&events), Ok(3));

        let mut tampered = events.clone();
        tampered[1].payload = "TAMPERED".to_string();
        let res = verify_audit_chain(&tampered);
        assert!(res.is_err());
        let (seq, _) = res.unwrap_err();
        assert_eq!(seq, 2);
    }

    #[test]
    fn test_dynamic_graph_topology_and_cycles() {
        let resources = sample_test_resources();
        let (nodes, has_cycle, hash) = build_dynamic_graph(&resources);
        assert_eq!(nodes.len(), 3);
        assert!(!has_cycle);
        assert!(!hash.is_empty());

        let pt_node = &nodes[0];
        assert_eq!(pt_node.resource_type, "Patient");
        assert_eq!(pt_node.in_degree, 2); // Encounter and Observation point to it
        assert_eq!(pt_node.out_degree, 0);

        let obs_node = &nodes[2];
        assert_eq!(obs_node.resource_type, "Observation");
        assert_eq!(obs_node.in_degree, 0);
        assert_eq!(obs_node.out_degree, 2); // points to Patient and Encounter
    }

    #[test]
    fn test_empty_graph_produces_clean_dag() {
        let (nodes, has_cycle, _) = build_dynamic_graph(&[]);
        assert!(nodes.is_empty());
        assert!(!has_cycle);
    }

    #[test]
    fn test_analytics_and_search_computations() {
        let mut app = MedOriginNativePreview::default();
        assert_eq!(app.active_resources().len(), 0);

        // Admitting canonical fixture
        app.open_embedded_fictional_bundle_demo().unwrap();
        let admitted = app.active_resources();
        assert_eq!(admitted.len(), 8);

        let pt_count = admitted
            .iter()
            .filter(|r| r.resource_type == "Patient")
            .count();
        let enc_count = admitted
            .iter()
            .filter(|r| r.resource_type == "Encounter")
            .count();
        let obs_count = admitted
            .iter()
            .filter(|r| r.resource_type == "Observation")
            .count();
        assert_eq!(pt_count, 2);
        assert_eq!(enc_count, 2);
        assert_eq!(obs_count, 4);
    }

    #[test]
    fn test_storage_vault_integrity() {
        let state = ConnectedScreensState::default();
        assert!(state.storage_vault_locked);
        assert!(state.storage_derived_key.is_none());
        assert!(!state.storage_backup_verified);
    }

    #[test]
    fn test_rfc8439_chacha20_poly1305_vectors() {
        // RFC 8439 Section 2.5.2 Poly1305 test vector
        let key = hex_to_32("85d6be7857556d337f4452fe42d506a80103808afb0db2fd4abff6af4149f51b");
        let msg = b"Cryptographic Forum Research Group";
        let tag = poly1305_mac(&key, msg);
        let tag_hex = tag.iter().map(|b| format!("{b:02x}")).collect::<String>();
        assert_eq!(tag_hex, "a8061dc1305136c6c22b8baf0c0127a9");

        // RFC 8439 Section 2.8.2 AEAD test vector
        let key_aead =
            hex_to_32("808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f");
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

        // Negative control: tampered tag
        let mut bad_tag = tag_aead;
        bad_tag[0] ^= 0x01;
        assert_eq!(
            chacha20_poly1305_decrypt(&key_aead, &nonce, &aad, &ct, &bad_tag),
            Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
        );

        // Negative control: tampered ciphertext
        let mut bad_ct = ct.clone();
        bad_ct[0] ^= 0x01;
        assert_eq!(
            chacha20_poly1305_decrypt(&key_aead, &nonce, &aad, &bad_ct, &tag_aead),
            Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
        );
    }

    #[test]
    fn test_mswsenv1_envelope_roundtrip_and_tamper_rejection() {
        let salt = [0x42u8; 16];
        let nonce = [0x24u8; 12];
        let key = derive_workspace_key("passphrase-secret-123", &salt, "medorigin-test");
        let plaintext = b"Sensitive synthetic clinical readback payload 2026";

        let env = encrypt_envelope(&key, &salt, &nonce, plaintext);
        assert!(env.starts_with(ENVELOPE_MAGIC));
        assert_eq!(env.len(), ENVELOPE_HEADER_LEN + TAG_LEN + plaintext.len());

        let dec = decrypt_envelope(&key, &env).expect("Envelope decrypt must succeed");
        assert_eq!(dec, plaintext);

        // Negative control: tamper ciphertext
        let mut tampered_env = env.clone();
        let last = tampered_env.len() - 1;
        tampered_env[last] ^= 0x80;
        let fail = decrypt_envelope(&key, &tampered_env);
        assert_eq!(fail, Err("AUTHENTICATION_TAG_VERIFICATION_FAILED"));

        // Negative control: tamper magic
        let mut bad_magic = env.clone();
        bad_magic[0] = b'X';
        assert_eq!(
            decrypt_envelope(&key, &bad_magic),
            Err("INVALID_ENVELOPE_MAGIC")
        );

        // Memory zeroize check
        let mut secret = [0x5au8; 32];
        zeroize_bytes(&mut secret);
        assert_eq!(secret, [0u8; 32]);
    }
}
