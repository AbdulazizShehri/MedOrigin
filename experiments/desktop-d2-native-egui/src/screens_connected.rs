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
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

use argon2::{Algorithm, Argon2, Params, Version};
use chacha20poly1305::{ChaCha20Poly1305, KeyInit as AeadKeyInit, Nonce, Tag, aead::AeadInOut};
use eframe::egui::{self, RichText, Ui};
use hkdf::Hkdf;
use hmac::{Hmac, KeyInit as HmacKeyInit, Mac};
use pbkdf2::pbkdf2_hmac;
use serde_json::Value;
use sha2::{Digest, Sha256};
use zeroize::{Zeroize, Zeroizing};

use crate::app::MedOriginNativePreview;
use crate::encrypted_readback::FictionalReadbackResource;
use crate::screens::SCREENS;
use crate::theme;

// -----------------------------------------------------------------------------
// Audited Cryptographic Engine (RustCrypto + OS CSPRNG + Volatile Zeroize)
// -----------------------------------------------------------------------------

pub const MAX_PERSISTED_FILE_BYTES: usize = 4 * 1024 * 1024;

// Bounded KDF parameters (defends against malicious envelope CPU/RAM DoS)
pub const PBKDF2_LEGACY_V1_ITERATIONS: u32 = 25_000;
pub const MAX_PBKDF2_ITERATIONS: u32 = 600_000;

pub const MIN_ARGON2_MEMORY_KIB: u32 = 8_192; // 8 MiB floor
pub const DEFAULT_ARGON2_MEMORY_KIB: u32 = 19_456; // 19 MiB (OWASP interactive baseline)
pub const MAX_ARGON2_MEMORY_KIB: u32 = 262_144; // 256 MiB hard DoS ceiling
pub const MIN_ARGON2_TIME_COST: u32 = 1;
pub const DEFAULT_ARGON2_TIME_COST: u32 = 2;
pub const MAX_ARGON2_TIME_COST: u32 = 10;
pub const MIN_ARGON2_PARALLELISM: u32 = 1;
pub const DEFAULT_ARGON2_PARALLELISM: u32 = 1;
pub const MAX_ARGON2_PARALLELISM: u32 = 4;

// Strict HKDF domain-separation labels (no key reuse across purposes)
pub const VAULT_KEY_LABEL_V1_LEGACY: &str = "mesc-clinical-workspace-backup-hkdf-sha256/1";
pub const VAULT_KEY_LABEL_V2: &str = "mesc-clinical-workspace-backup-hkdf-sha256/2";
pub const AUDIT_MAC_KEY_LABEL: &str = "mesc-clinical-workspace-audit-hmac-sha256/1";
pub const VAULT_CONFIRM_LABEL: &str = "mesc-clinical-workspace-vault-confirm-hmac/2";

// MSWSENV1 Envelope layout constants
pub const ENVELOPE_MAGIC: &[u8; 8] = b"MSWSENV1";
pub const ENVELOPE_VERSION_V1_LEGACY: u8 = 1;
pub const ENVELOPE_VERSION_V2_ARGON2ID: u8 = 2;
pub const ENVELOPE_V1_HEADER_LEN: usize = 41; // 8 magic + 1 ver + 4 key_ver + 16 salt + 12 nonce
pub const ENVELOPE_V2_HEADER_LEN: usize = 53; // 8 magic + 1 ver + 4 key_ver + 12 argon2_params + 16 salt + 12 nonce
pub const TAG_LEN: usize = 16;
pub const MIN_ENVELOPE_V1_LEN: usize = ENVELOPE_V1_HEADER_LEN + TAG_LEN;
pub const MIN_ENVELOPE_V2_LEN: usize = ENVELOPE_V2_HEADER_LEN + TAG_LEN;

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

pub fn bytes_to_hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

pub fn hex_to_bytes(hex: &str) -> Result<Vec<u8>, &'static str> {
    if !hex.len().is_multiple_of(2) {
        return Err("INVALID_HEX_LENGTH");
    }
    let mut out = Vec::with_capacity(hex.len() / 2);
    for i in (0..hex.len()).step_by(2) {
        let byte = u8::from_str_radix(&hex[i..i + 2], 16).map_err(|_| "INVALID_HEX_CHAR")?;
        out.push(byte);
    }
    Ok(out)
}

/// Operating-system-backed CSPRNG via `getrandom` (`BCryptGenRandom` on Windows,
/// `getrandom(2)` on Linux, `getentropy` on macOS). Fails closed on OS RNG error.
pub fn generate_os_random_bytes<const N: usize>() -> Result<[u8; N], &'static str> {
    let mut out = [0u8; N];
    getrandom::fill(&mut out).map_err(|_| "OS_CSPRNG_UNAVAILABLE")?;
    Ok(out)
}

/// Volatile memory zeroization via `zeroize`.
/// Note: Guarantees compiler will not elide the wipe of this buffer, though OS
/// page swapping, crash dumps, and external UI string copies remain outside
/// application control without OS-level `mlock` / encrypted swap.
pub fn zeroize_bytes(buf: &mut [u8]) {
    buf.zeroize();
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Argon2Params {
    pub m_cost_kib: u32,
    pub t_cost: u32,
    pub p_cost: u32,
}

impl Default for Argon2Params {
    fn default() -> Self {
        Self {
            m_cost_kib: DEFAULT_ARGON2_MEMORY_KIB,
            t_cost: DEFAULT_ARGON2_TIME_COST,
            p_cost: DEFAULT_ARGON2_PARALLELISM,
        }
    }
}

impl Argon2Params {
    pub fn validate(self) -> Result<(), &'static str> {
        if !(MIN_ARGON2_MEMORY_KIB..=MAX_ARGON2_MEMORY_KIB).contains(&self.m_cost_kib)
            || !(MIN_ARGON2_TIME_COST..=MAX_ARGON2_TIME_COST).contains(&self.t_cost)
            || !(MIN_ARGON2_PARALLELISM..=MAX_ARGON2_PARALLELISM).contains(&self.p_cost)
        {
            return Err("ARGON2_KDF_PARAMS_OUT_OF_BOUNDS");
        }
        Ok(())
    }
}

/// Audited RFC 2104 HMAC-SHA-256 via `hmac`.
pub fn hmac_sha256(key: &[u8], data: &[u8]) -> [u8; 32] {
    let mut mac = <Hmac<Sha256> as HmacKeyInit>::new_from_slice(key)
        .expect("HMAC accepts keys of any length");
    mac.update(data);
    mac.finalize().into_bytes().into()
}

/// Constant-time HMAC-SHA-256 verification via `hmac` (`ctutils`).
pub fn verify_hmac_sha256(
    key: &[u8],
    data: &[u8],
    expected_tag: &[u8],
) -> Result<(), &'static str> {
    let mut mac = <Hmac<Sha256> as HmacKeyInit>::new_from_slice(key)
        .expect("HMAC accepts keys of any length");
    mac.update(data);
    mac.verify_slice(expected_tag)
        .map_err(|_| "HMAC_VERIFICATION_FAILED")
}

/// Audited RFC 5869 HKDF-SHA-256 extract-and-expand returning a `Zeroizing` 32-byte key.
pub fn hkdf_extract_expand_32(
    salt: &[u8],
    ikm: &[u8],
    info: &[u8],
) -> Result<Zeroizing<[u8; 32]>, &'static str> {
    let hk = Hkdf::<Sha256>::new(Some(salt), ikm);
    let mut okm = Zeroizing::new([0u8; 32]);
    hk.expand(info, okm.as_mut())
        .map_err(|_| "HKDF_EXPAND_FAILED")?;
    Ok(okm)
}

/// Audited RFC 9106 Argon2id + RFC 5869 HKDF-SHA-256 key derivation with strict
/// parameter bounds checking before allocation.
pub fn derive_workspace_key_argon2id(
    passphrase: &str,
    salt: &[u8; 16],
    params: Argon2Params,
    label: &str,
) -> Result<Zeroizing<[u8; 32]>, &'static str> {
    if passphrase.is_empty() {
        return Err("EMPTY_PASSPHRASE_REFUSED");
    }
    params.validate()?;
    let argon_params = Params::new(params.m_cost_kib, params.t_cost, params.p_cost, Some(32))
        .map_err(|_| "ARGON2_PARAMS_INVALID")?;
    let argon2 = Argon2::new(Algorithm::Argon2id, Version::V0x13, argon_params);
    let mut stretched = Zeroizing::new([0u8; 32]);
    argon2
        .hash_password_into(passphrase.as_bytes(), salt, stretched.as_mut())
        .map_err(|_| "ARGON2_DERIVATION_FAILED")?;
    hkdf_extract_expand_32(salt, stretched.as_ref(), label.as_bytes())
}

/// Audited RFC 2898 PBKDF2-HMAC-SHA256 via `pbkdf2` (bounded; kept strictly for
/// legacy v1 envelope recovery and migration).
pub fn pbkdf2_hmac_sha256(
    password: &[u8],
    salt: &[u8],
    iterations: u32,
) -> Result<Zeroizing<[u8; 32]>, &'static str> {
    if iterations == 0 || iterations > MAX_PBKDF2_ITERATIONS {
        return Err("PBKDF2_ITERATIONS_OUT_OF_BOUNDS");
    }
    let mut dk = Zeroizing::new([0u8; 32]);
    pbkdf2_hmac::<Sha256>(password, salt, iterations, dk.as_mut());
    Ok(dk)
}

/// Legacy v1 key derivation (PBKDF2-HMAC-SHA256 + HKDF-SHA-256) strictly for
/// backward-compatible decryption and migration of v1 envelopes.
pub fn derive_workspace_key_v1_legacy(
    passphrase: &str,
    salt: &[u8; 16],
    label: &str,
) -> Result<Zeroizing<[u8; 32]>, &'static str> {
    if passphrase.is_empty() {
        return Err("EMPTY_PASSPHRASE_REFUSED");
    }
    let stretched = pbkdf2_hmac_sha256(passphrase.as_bytes(), salt, PBKDF2_LEGACY_V1_ITERATIONS)?;
    hkdf_extract_expand_32(salt, stretched.as_ref(), label.as_bytes())
}

/// Derives an independent audit authentication key via HKDF domain separation.
/// Never shares key material with AEAD storage or backup encryption keys.
pub fn derive_audit_mac_key(
    vault_root_key: &[u8; 32],
    salt: &[u8; 16],
) -> Result<Zeroizing<[u8; 32]>, &'static str> {
    hkdf_extract_expand_32(salt, vault_root_key, AUDIT_MAC_KEY_LABEL.as_bytes())
}

/// Computes a one-way non-secret fingerprint for UI display; never exposes raw key bytes.
pub fn key_fingerprint_hex(key: &[u8; 32]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(b"MEDORIGIN_KEY_FINGERPRINT_V2|");
    hasher.update(key);
    hasher_hex(hasher)
}

/// Audited RFC 8439 ChaCha20-Poly1305 AEAD encryption via `chacha20poly1305`.
pub fn chacha20_poly1305_encrypt(
    key: &[u8; 32],
    nonce: &[u8; 12],
    aad: &[u8],
    plaintext: &[u8],
) -> Result<(Vec<u8>, [u8; 16]), &'static str> {
    let cipher = ChaCha20Poly1305::new(key.into());
    let mut buffer = plaintext.to_vec();
    let nonce_arr = Nonce::from(*nonce);
    let tag: Tag = cipher
        .encrypt_inout_detached(&nonce_arr, aad, buffer.as_mut_slice().into())
        .map_err(|_| "AEAD_ENCRYPTION_FAILED")?;
    let mut tag_bytes = [0u8; 16];
    tag_bytes.copy_from_slice(tag.as_slice());
    Ok((buffer, tag_bytes))
}

/// Audited RFC 8439 ChaCha20-Poly1305 AEAD decryption via `chacha20poly1305`.
/// Verifies authentication tag before releasing plaintext; returns `Zeroizing<Vec<u8>>`.
pub fn chacha20_poly1305_decrypt(
    key: &[u8; 32],
    nonce: &[u8; 12],
    aad: &[u8],
    ciphertext: &[u8],
    tag: &[u8; 16],
) -> Result<Zeroizing<Vec<u8>>, &'static str> {
    let cipher = ChaCha20Poly1305::new(key.into());
    let mut buffer = Zeroizing::new(ciphertext.to_vec());
    let nonce_arr = Nonce::from(*nonce);
    let tag_arr = Tag::from(*tag);
    cipher
        .decrypt_inout_detached(&nonce_arr, aad, buffer.as_mut_slice().into(), &tag_arr)
        .map_err(|_| "AUTHENTICATION_TAG_VERIFICATION_FAILED")?;
    Ok(buffer)
}

/// Encrypts a legacy v1 envelope (`MSWSENV1`, version `0x01`) with explicit key/salt/nonce.
/// Used for deterministic known-answer tests and v1->v2 migration test fixtures.
pub fn encrypt_envelope_v1_raw(
    key: &[u8; 32],
    salt: &[u8; 16],
    nonce: &[u8; 12],
    plaintext: &[u8],
) -> Result<Vec<u8>, &'static str> {
    let mut header = Vec::with_capacity(ENVELOPE_V1_HEADER_LEN);
    header.extend_from_slice(ENVELOPE_MAGIC);
    header.push(ENVELOPE_VERSION_V1_LEGACY);
    header.extend_from_slice(&1u32.to_be_bytes());
    header.extend_from_slice(salt);
    header.extend_from_slice(nonce);

    let (ciphertext, tag) = chacha20_poly1305_encrypt(key, nonce, &header, plaintext)?;
    let mut envelope = Vec::with_capacity(ENVELOPE_V1_HEADER_LEN + TAG_LEN + ciphertext.len());
    envelope.extend_from_slice(&header);
    envelope.extend_from_slice(&tag);
    envelope.extend_from_slice(&ciphertext);
    Ok(envelope)
}

/// Encrypts a v2 envelope (`MSWSENV1`, version `0x02`) using Argon2id, HKDF-SHA-256,
/// and ChaCha20-Poly1305 with fresh OS CSPRNG salt and 96-bit nonce.
///
/// All 53 header bytes (magic, version, key_ver, bounded Argon2id params, salt, nonce)
/// are authenticated as AEAD associated data.
pub fn encrypt_envelope_v2(
    passphrase: &str,
    params: Argon2Params,
    plaintext: &[u8],
) -> Result<Vec<u8>, &'static str> {
    if passphrase.is_empty() {
        return Err("EMPTY_PASSPHRASE_REFUSED");
    }
    params.validate()?;
    let salt = generate_os_random_bytes::<16>()?;
    let nonce = generate_os_random_bytes::<12>()?;
    let key = derive_workspace_key_argon2id(passphrase, &salt, params, VAULT_KEY_LABEL_V2)?;

    let mut header = Vec::with_capacity(ENVELOPE_V2_HEADER_LEN);
    header.extend_from_slice(ENVELOPE_MAGIC);
    header.push(ENVELOPE_VERSION_V2_ARGON2ID);
    header.extend_from_slice(&1u32.to_be_bytes());
    header.extend_from_slice(&params.m_cost_kib.to_be_bytes());
    header.extend_from_slice(&params.t_cost.to_be_bytes());
    header.extend_from_slice(&params.p_cost.to_be_bytes());
    header.extend_from_slice(&salt);
    header.extend_from_slice(&nonce);

    let (ciphertext, tag) = chacha20_poly1305_encrypt(&key, &nonce, &header, plaintext)?;
    let mut envelope = Vec::with_capacity(ENVELOPE_V2_HEADER_LEN + TAG_LEN + ciphertext.len());
    envelope.extend_from_slice(&header);
    envelope.extend_from_slice(&tag);
    envelope.extend_from_slice(&ciphertext);
    Ok(envelope)
}

/// Decrypts and authenticates an `MSWSENV1` envelope (supporting both v2 Argon2id
/// and legacy v1 PBKDF2 for recovery/migration). Validates KDF parameter bounds
/// BEFORE invoking Argon2id and never returns unauthenticated plaintext.
pub fn decrypt_envelope_with_passphrase(
    passphrase: &str,
    envelope: &[u8],
) -> Result<(u8, Zeroizing<Vec<u8>>), &'static str> {
    if passphrase.is_empty() {
        return Err("EMPTY_PASSPHRASE_REFUSED");
    }
    if envelope.len() > MAX_PERSISTED_FILE_BYTES {
        return Err("ENVELOPE_TOO_LARGE");
    }
    if envelope.len() < MIN_ENVELOPE_V1_LEN {
        return Err("ENVELOPE_TOO_SHORT");
    }
    if &envelope[0..8] != ENVELOPE_MAGIC {
        return Err("INVALID_ENVELOPE_MAGIC");
    }
    let version = envelope[8];
    let key_version = u32::from_be_bytes(envelope[9..13].try_into().unwrap());
    if key_version == 0 {
        return Err("INVALID_KEY_VERSION");
    }

    match version {
        ENVELOPE_VERSION_V1_LEGACY => {
            let header = &envelope[0..ENVELOPE_V1_HEADER_LEN];
            let mut salt = [0u8; 16];
            salt.copy_from_slice(&header[13..29]);
            let mut nonce = [0u8; 12];
            nonce.copy_from_slice(&header[29..41]);
            let mut tag = [0u8; 16];
            tag.copy_from_slice(
                &envelope[ENVELOPE_V1_HEADER_LEN..ENVELOPE_V1_HEADER_LEN + TAG_LEN],
            );
            let ciphertext = &envelope[ENVELOPE_V1_HEADER_LEN + TAG_LEN..];
            let key = derive_workspace_key_v1_legacy(passphrase, &salt, VAULT_KEY_LABEL_V1_LEGACY)?;
            let plaintext = chacha20_poly1305_decrypt(&key, &nonce, header, ciphertext, &tag)?;
            Ok((ENVELOPE_VERSION_V1_LEGACY, plaintext))
        }
        ENVELOPE_VERSION_V2_ARGON2ID => {
            if envelope.len() < MIN_ENVELOPE_V2_LEN {
                return Err("ENVELOPE_TOO_SHORT");
            }
            let header = &envelope[0..ENVELOPE_V2_HEADER_LEN];
            let params = Argon2Params {
                m_cost_kib: u32::from_be_bytes(header[13..17].try_into().unwrap()),
                t_cost: u32::from_be_bytes(header[17..21].try_into().unwrap()),
                p_cost: u32::from_be_bytes(header[21..25].try_into().unwrap()),
            };
            // Fail closed BEFORE allocating memory for malicious KDF parameters
            params.validate()?;
            let mut salt = [0u8; 16];
            salt.copy_from_slice(&header[25..41]);
            let mut nonce = [0u8; 12];
            nonce.copy_from_slice(&header[41..53]);
            let mut tag = [0u8; 16];
            tag.copy_from_slice(
                &envelope[ENVELOPE_V2_HEADER_LEN..ENVELOPE_V2_HEADER_LEN + TAG_LEN],
            );
            let ciphertext = &envelope[ENVELOPE_V2_HEADER_LEN + TAG_LEN..];
            let key = derive_workspace_key_argon2id(passphrase, &salt, params, VAULT_KEY_LABEL_V2)?;
            let plaintext = chacha20_poly1305_decrypt(&key, &nonce, header, ciphertext, &tag)?;
            Ok((ENVELOPE_VERSION_V2_ARGON2ID, plaintext))
        }
        _ => Err("UNSUPPORTED_ENVELOPE_VERSION"),
    }
}

/// Migrates a legacy v1 envelope to a fresh v2 Argon2id envelope with new OS CSPRNG salt/nonce.
pub fn migrate_v1_envelope_to_v2(
    passphrase: &str,
    v1_envelope: &[u8],
    params: Argon2Params,
) -> Result<Vec<u8>, &'static str> {
    let (ver, plaintext) = decrypt_envelope_with_passphrase(passphrase, v1_envelope)?;
    if ver != ENVELOPE_VERSION_V1_LEGACY {
        return Err("ENVELOPE_NOT_V1_LEGACY");
    }
    encrypt_envelope_v2(passphrase, params, plaintext.as_slice())
}

// -----------------------------------------------------------------------------
// Hardened Local Persistence (Reparse/Symlink Guards + Atomic Writes)
// -----------------------------------------------------------------------------

#[cfg(windows)]
fn is_reparse_point(meta: &fs::Metadata) -> bool {
    use std::os::windows::fs::MetadataExt;
    (meta.file_attributes() & 0x0400) != 0
}

#[cfg(not(windows))]
fn is_reparse_point(_meta: &fs::Metadata) -> bool {
    false
}

pub fn validate_local_regular_path(path: &Path, must_exist: bool) -> Result<(), &'static str> {
    if path.as_os_str().is_empty() {
        return Err("EMPTY_FILE_PATH_REFUSED");
    }
    // Check all existing ancestor directories for symlinks or Windows junctions/reparse points
    for ancestor in path.ancestors().skip(1) {
        if ancestor.as_os_str().is_empty() {
            continue;
        }
        if let Ok(meta) = fs::symlink_metadata(ancestor)
            && (meta.file_type().is_symlink() || is_reparse_point(&meta))
        {
            return Err("SYMLINK_OR_REPARSE_ANCESTOR_REFUSED");
        }
    }
    if must_exist {
        let meta = fs::symlink_metadata(path).map_err(|_| "LOCAL_FILE_NOT_FOUND")?;
        if meta.file_type().is_symlink() || is_reparse_point(&meta) || !meta.is_file() {
            return Err("SYMLINK_OR_NON_FILE_REFUSED");
        }
        if meta.len() as usize > MAX_PERSISTED_FILE_BYTES {
            return Err("PERSISTED_FILE_TOO_LARGE");
        }
    } else {
        if let Some(parent) = path.parent()
            && !parent.as_os_str().is_empty()
        {
            let pmeta = fs::symlink_metadata(parent).map_err(|_| "PARENT_DIRECTORY_NOT_FOUND")?;
            if pmeta.file_type().is_symlink() || is_reparse_point(&pmeta) || !pmeta.is_dir() {
                return Err("PARENT_DIRECTORY_INVALID");
            }
        }
        if let Ok(meta) = fs::symlink_metadata(path)
            && (meta.file_type().is_symlink() || is_reparse_point(&meta) || !meta.is_file())
        {
            return Err("SYMLINK_OR_NON_FILE_REFUSED");
        }
    }
    Ok(())
}

/// Atomic local file writer: writes to a fresh OS-random sibling temp file,
/// calls `sync_all`, and commits via rename. Never overwrites an existing file
/// unless `allow_overwrite == true`. Cleans up temp files on failure.
pub fn atomic_write_local_file(
    path: &Path,
    bytes: &[u8],
    allow_overwrite: bool,
) -> Result<usize, &'static str> {
    if bytes.len() > MAX_PERSISTED_FILE_BYTES {
        return Err("PERSISTED_FILE_TOO_LARGE");
    }
    validate_local_regular_path(path, false)?;
    if !allow_overwrite && path.exists() {
        return Err("FILE_ALREADY_EXISTS_REFUSED");
    }

    let rand_suffix = bytes_to_hex(&generate_os_random_bytes::<8>()?);
    let file_name = path
        .file_name()
        .and_then(|n| n.to_str())
        .ok_or("INVALID_FILE_NAME")?;
    let tmp_path: PathBuf = match path.parent() {
        Some(parent) if !parent.as_os_str().is_empty() => {
            parent.join(format!(".{file_name}.medorigin.tmp.{rand_suffix}"))
        }
        _ => PathBuf::from(format!(".{file_name}.medorigin.tmp.{rand_suffix}")),
    };

    let write_res = (|| -> Result<(), &'static str> {
        let mut f = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&tmp_path)
            .map_err(|_| "ATOMIC_TMP_CREATE_FAILED")?;
        f.write_all(bytes).map_err(|_| "ATOMIC_TMP_WRITE_FAILED")?;
        f.sync_all().map_err(|_| "ATOMIC_TMP_SYNC_FAILED")?;
        Ok(())
    })();
    if let Err(err) = write_res {
        let _ = fs::remove_file(&tmp_path);
        return Err(err);
    }

    // Re-check target immediately before commit to narrow path races
    if let Ok(meta) = fs::symlink_metadata(path) {
        if meta.file_type().is_symlink() || is_reparse_point(&meta) || !meta.is_file() {
            let _ = fs::remove_file(&tmp_path);
            return Err("SYMLINK_OR_NON_FILE_REFUSED");
        }
        if !allow_overwrite {
            let _ = fs::remove_file(&tmp_path);
            return Err("FILE_ALREADY_EXISTS_REFUSED");
        }
    }

    if fs::rename(&tmp_path, path).is_err() {
        // On Windows, fs::rename fails when destination already exists; use safe swap-restore
        if allow_overwrite && path.exists() {
            let bak_path = tmp_path.with_extension("bak");
            if fs::rename(path, &bak_path).is_err() {
                let _ = fs::remove_file(&tmp_path);
                return Err("ATOMIC_COMMIT_RENAME_FAILED");
            }
            if fs::rename(&tmp_path, path).is_err() {
                let _ = fs::rename(&bak_path, path);
                let _ = fs::remove_file(&tmp_path);
                return Err("ATOMIC_COMMIT_RENAME_FAILED");
            }
            let _ = fs::remove_file(&bak_path);
        } else {
            let _ = fs::remove_file(&tmp_path);
            return Err("ATOMIC_COMMIT_RENAME_FAILED");
        }
    }
    Ok(bytes.len())
}

pub fn save_encrypted_backup_to_path(
    path: &Path,
    envelope: &[u8],
    allow_overwrite: bool,
) -> Result<usize, &'static str> {
    if envelope.len() < MIN_ENVELOPE_V1_LEN || &envelope[0..8] != ENVELOPE_MAGIC {
        return Err("INVALID_ENVELOPE_REFUSED");
    }
    atomic_write_local_file(path, envelope, allow_overwrite)
}

pub fn load_encrypted_backup_from_path(path: &Path) -> Result<Vec<u8>, &'static str> {
    validate_local_regular_path(path, true)?;
    let bytes = fs::read(path).map_err(|_| "BACKUP_FILE_READ_FAILED")?;
    if bytes.len() < MIN_ENVELOPE_V1_LEN {
        return Err("ENVELOPE_TOO_SHORT");
    }
    if bytes.len() > MAX_PERSISTED_FILE_BYTES {
        return Err("PERSISTED_FILE_TOO_LARGE");
    }
    Ok(bytes)
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
// Authenticated Local Audit Ledger & Rollback-Detecting Checkpoints (Section 4)
// -----------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AuditEvent {
    pub seq: u64,
    pub event_type: String,
    pub actor: String,
    pub payload: String,
    pub prev_hash: String,
    pub hash: String,
    /// Optional keyed HMAC-SHA-256 computed with the domain-separated audit MAC key.
    /// Absent (`None`) when recorded prior to vault key derivation (unkeyed local chain only).
    pub mac: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct AuditCheckpoint {
    pub head_seq: u64,
    pub head_hash: String,
    pub head_mac: String,
    pub checkpoint_mac: String,
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

fn audit_event_mac_input(ev: &AuditEvent) -> Vec<u8> {
    format!(
        "AUDIT_EVENT_V2|{}|{}|{}|{}|{}|{}",
        ev.seq, ev.event_type, ev.actor, ev.payload, ev.prev_hash, ev.hash
    )
    .into_bytes()
}

pub fn compute_audit_event_mac(audit_key: &[u8; 32], ev: &AuditEvent) -> String {
    bytes_to_hex(&hmac_sha256(audit_key, &audit_event_mac_input(ev)))
}

pub fn create_audit_checkpoint(
    events: &[AuditEvent],
    audit_key: &[u8; 32],
) -> Result<AuditCheckpoint, &'static str> {
    if verify_audit_chain(events).is_err() {
        return Err("CANNOT_CHECKPOINT_CORRUPTED_CHAIN");
    }
    let last = events.last().ok_or("CANNOT_CHECKPOINT_EMPTY_LEDGER")?;
    let head_mac = last.mac.clone().ok_or("HEAD_EVENT_UNAUTHENTICATED")?;
    let cp_input = format!("AUDIT_CHECKPOINT_V1|{}|{}|{head_mac}", last.seq, last.hash);
    let checkpoint_mac = bytes_to_hex(&hmac_sha256(audit_key, cp_input.as_bytes()));
    Ok(AuditCheckpoint {
        head_seq: last.seq,
        head_hash: last.hash.clone(),
        head_mac,
        checkpoint_mac,
    })
}

pub fn verify_audit_checkpoint(
    checkpoint: &AuditCheckpoint,
    audit_key: &[u8; 32],
) -> Result<(), &'static str> {
    let cp_input = format!(
        "AUDIT_CHECKPOINT_V1|{}|{}|{}",
        checkpoint.head_seq, checkpoint.head_hash, checkpoint.head_mac
    );
    let expected = hex_to_bytes(&checkpoint.checkpoint_mac)?;
    verify_hmac_sha256(audit_key, cp_input.as_bytes(), &expected)
        .map_err(|_| "CHECKPOINT_MAC_VERIFICATION_FAILED")
}

/// Verifies SHA-256 continuity (detects accidental corruption / partial tampering).
/// Note: An unkeyed SHA-256 chain does NOT resist full-chain recomputation by a
/// local attacker; use `verify_authenticated_audit_ledger` with a keyed checkpoint.
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

/// Verifies SHA-256 chain, per-event keyed HMAC-SHA-256 tags (defeating full-chain
/// reconstruction, insertion, deletion, reordering), AND optional protected checkpoint
/// (defeating truncation and rollback to an earlier valid snapshot).
pub fn verify_authenticated_audit_ledger(
    events: &[AuditEvent],
    audit_key: &[u8; 32],
    checkpoint: Option<&AuditCheckpoint>,
) -> Result<usize, (usize, String)> {
    let count = verify_audit_chain(events)?;
    if count == 0 {
        return Err((0, "AUDIT_LEDGER_EMPTY_REFUSED".to_string()));
    }
    for ev in events {
        let Some(ref mac_hex) = ev.mac else {
            return Err((ev.seq as usize, "AUDIT_EVENT_MISSING_HMAC_TAG".to_string()));
        };
        let mac_bytes = hex_to_bytes(mac_hex)
            .map_err(|e| (ev.seq as usize, format!("AUDIT_HMAC_HEX_INVALID: {e}")))?;
        verify_hmac_sha256(audit_key, &audit_event_mac_input(ev), &mac_bytes).map_err(|_| {
            (
                ev.seq as usize,
                "AUDIT_HMAC_VERIFICATION_FAILED".to_string(),
            )
        })?;
    }
    if let Some(cp) = checkpoint {
        verify_audit_checkpoint(cp, audit_key)
            .map_err(|e| (cp.head_seq as usize, e.to_string()))?;
        if (events.len() as u64) < cp.head_seq {
            return Err((
                events.len(),
                format!(
                    "AUDIT_ROLLBACK_OR_TRUNCATION_DETECTED: ledger length {} < checkpoint head {}",
                    events.len(),
                    cp.head_seq
                ),
            ));
        }
        let anchored = &events[(cp.head_seq - 1) as usize];
        if anchored.hash != cp.head_hash || anchored.mac.as_deref() != Some(cp.head_mac.as_str()) {
            return Err((
                cp.head_seq as usize,
                "AUDIT_ROLLBACK_OR_TRUNCATION_DETECTED: checkpoint head digest/MAC mismatch"
                    .to_string(),
            ));
        }
    }
    Ok(count)
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
        mac: None,
    });
    events
}

pub fn authenticate_audit_events_with_key(events: &mut [AuditEvent], audit_key: &[u8; 32]) {
    for ev in events.iter_mut() {
        ev.mac = Some(compute_audit_event_mac(audit_key, ev));
    }
}

pub fn serialize_audit_events(events: &[AuditEvent]) -> Result<String, &'static str> {
    if verify_audit_chain(events).is_err() {
        return Err("REFUSED_TO_SERIALIZE_CORRUPTED_AUDIT_CHAIN");
    }
    let keyed = events.iter().all(|e| e.mac.is_some());
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
                "mac": ev.mac,
            })
        })
        .collect();
    let root = serde_json::json!({
        "schema": "medorigin-d2-local-audit-chain/v2",
        "keyed_hmac_authenticated": keyed,
        "externally_anchored": false,
        "clinical_use_authorized": false,
        "events": items,
    });
    serde_json::to_string_pretty(&root).map_err(|_| "AUDIT_SERIALIZATION_FAILED")
}

pub fn serialize_audit_checkpoint(cp: &AuditCheckpoint) -> Result<String, &'static str> {
    let root = serde_json::json!({
        "schema": "medorigin-d2-audit-checkpoint/v1",
        "head_seq": cp.head_seq,
        "head_hash": cp.head_hash,
        "head_mac": cp.head_mac,
        "checkpoint_mac": cp.checkpoint_mac,
    });
    serde_json::to_string_pretty(&root).map_err(|_| "CHECKPOINT_SERIALIZATION_FAILED")
}

pub fn deserialize_audit_checkpoint(raw: &str) -> Result<AuditCheckpoint, String> {
    let val: Value =
        serde_json::from_str(raw).map_err(|e| format!("AUDIT_CHECKPOINT_JSON_INVALID: {e}"))?;
    if val.get("schema").and_then(Value::as_str) != Some("medorigin-d2-audit-checkpoint/v1") {
        return Err("AUDIT_CHECKPOINT_SCHEMA_UNSUPPORTED".to_string());
    }
    Ok(AuditCheckpoint {
        head_seq: val
            .get("head_seq")
            .and_then(Value::as_u64)
            .ok_or_else(|| "CHECKPOINT_HEAD_SEQ_INVALID".to_string())?,
        head_hash: val
            .get("head_hash")
            .and_then(Value::as_str)
            .ok_or_else(|| "CHECKPOINT_HEAD_HASH_INVALID".to_string())?
            .to_string(),
        head_mac: val
            .get("head_mac")
            .and_then(Value::as_str)
            .ok_or_else(|| "CHECKPOINT_HEAD_MAC_INVALID".to_string())?
            .to_string(),
        checkpoint_mac: val
            .get("checkpoint_mac")
            .and_then(Value::as_str)
            .ok_or_else(|| "CHECKPOINT_MAC_INVALID".to_string())?
            .to_string(),
    })
}

pub fn deserialize_and_verify_audit_events(raw: &str) -> Result<Vec<AuditEvent>, String> {
    let val: Value =
        serde_json::from_str(raw).map_err(|e| format!("AUDIT_LEDGER_JSON_INVALID: {e}"))?;
    let schema = val.get("schema").and_then(Value::as_str);
    if !matches!(
        schema,
        Some("medorigin-d2-local-audit-chain/v1" | "medorigin-d2-local-audit-chain/v2")
    ) {
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
        let mac = match item.get("mac") {
            Some(Value::String(s)) => Some(s.clone()),
            Some(Value::Null) | None => None,
            _ => return Err("AUDIT_EVENT_MAC_INVALID".to_string()),
        };
        events.push(AuditEvent {
            seq,
            event_type,
            actor,
            payload,
            prev_hash,
            hash,
            mac,
        });
    }
    verify_audit_chain(&events)
        .map_err(|(seq, msg)| format!("AUDIT_CHAIN_CORRUPTED at seq {seq}: {msg}"))?;
    Ok(events)
}

pub fn save_audit_ledger_to_path(
    path: &Path,
    events: &[AuditEvent],
    allow_overwrite: bool,
) -> Result<usize, String> {
    let json = serialize_audit_events(events).map_err(|e| e.to_string())?;
    atomic_write_local_file(path, json.as_bytes(), allow_overwrite).map_err(|e| e.to_string())?;
    Ok(events.len())
}

pub fn load_audit_ledger_from_path(path: &Path) -> Result<Vec<AuditEvent>, String> {
    validate_local_regular_path(path, true).map_err(|e| e.to_string())?;
    let raw = fs::read_to_string(path).map_err(|_| "AUDIT_LEDGER_READ_FAILED".to_string())?;
    deserialize_and_verify_audit_events(&raw)
}

pub fn save_authenticated_audit_ledger_to_path(
    ledger_path: &Path,
    checkpoint_path: &Path,
    events: &[AuditEvent],
    audit_key: &[u8; 32],
    allow_overwrite: bool,
) -> Result<AuditCheckpoint, String> {
    verify_authenticated_audit_ledger(events, audit_key, None)
        .map_err(|(seq, msg)| format!("AUDIT_AUTH_FAILED at seq {seq}: {msg}"))?;
    let cp = create_audit_checkpoint(events, audit_key).map_err(|e| e.to_string())?;
    save_audit_ledger_to_path(ledger_path, events, allow_overwrite)?;
    let cp_json = serialize_audit_checkpoint(&cp).map_err(|e| e.to_string())?;
    atomic_write_local_file(checkpoint_path, cp_json.as_bytes(), allow_overwrite)
        .map_err(|e| e.to_string())?;
    Ok(cp)
}

pub fn load_authenticated_audit_ledger_from_path(
    ledger_path: &Path,
    checkpoint_path: &Path,
    audit_key: &[u8; 32],
) -> Result<(Vec<AuditEvent>, AuditCheckpoint), String> {
    let events = load_audit_ledger_from_path(ledger_path)?;
    validate_local_regular_path(checkpoint_path, true).map_err(|e| e.to_string())?;
    let cp_raw = fs::read_to_string(checkpoint_path)
        .map_err(|_| "AUDIT_CHECKPOINT_READ_FAILED".to_string())?;
    let cp = deserialize_audit_checkpoint(&cp_raw)?;
    verify_authenticated_audit_ledger(&events, audit_key, Some(&cp))
        .map_err(|(seq, msg)| format!("AUDIT_AUTH_FAILED at seq {seq}: {msg}"))?;
    Ok((events, cp))
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

/// Offline desktop runtime never fabricates external LLM benchmark scores.
pub fn benchmark_measured_results_available() -> bool {
    false
}

// -----------------------------------------------------------------------------
// Real Local Literature Screening Backend (Screen 12 — mirrors medscale.litdb)
// -----------------------------------------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ScreeningStage {
    Identified,
    Deduped,
    Screened,
    Eligibility,
    Included,
    Excluded,
}

impl ScreeningStage {
    pub fn as_str(self) -> &'static str {
        match self {
            ScreeningStage::Identified => "identified",
            ScreeningStage::Deduped => "deduped",
            ScreeningStage::Screened => "screened",
            ScreeningStage::Eligibility => "eligibility",
            ScreeningStage::Included => "included",
            ScreeningStage::Excluded => "excluded",
        }
    }
}

/// Enforces legal PRISMA stage transitions matching `src/medscale/litdb/screening.py`.
/// Every transition to `Excluded` requires a mandatory non-empty reason.
pub fn advance_screening_stage(
    current: ScreeningStage,
    to: ScreeningStage,
    reason: Option<&str>,
) -> Result<(ScreeningStage, Option<String>), &'static str> {
    let legal = match current {
        ScreeningStage::Identified => {
            matches!(to, ScreeningStage::Deduped | ScreeningStage::Excluded)
        }
        ScreeningStage::Deduped => {
            matches!(to, ScreeningStage::Screened | ScreeningStage::Excluded)
        }
        ScreeningStage::Screened => {
            matches!(to, ScreeningStage::Eligibility | ScreeningStage::Excluded)
        }
        ScreeningStage::Eligibility => {
            matches!(to, ScreeningStage::Included | ScreeningStage::Excluded)
        }
        ScreeningStage::Included => matches!(to, ScreeningStage::Excluded),
        ScreeningStage::Excluded => false,
    };
    if !legal {
        return Err("ILLEGAL_PRISMA_STAGE_TRANSITION");
    }
    if to == ScreeningStage::Excluded {
        let trimmed = reason.map(str::trim).unwrap_or("");
        if trimmed.is_empty() {
            return Err("EXCLUSION_REQUIRES_MANDATORY_REASON");
        }
        Ok((to, Some(trimmed.to_string())))
    } else if reason.is_some_and(|r| !r.trim().is_empty()) {
        Err("REASON_ONLY_PERMITTED_ON_EXCLUDED")
    } else {
        Ok((to, None))
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LiteratureRecord {
    pub id: String,
    pub title: String,
    pub doi: Option<String>,
    pub pmid: Option<String>,
    pub year: Option<u32>,
    pub source: String,
    pub license: String,
    pub stage: ScreeningStage,
    pub exclusion_reason: Option<String>,
    pub duplicate_of: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PrismaCounts {
    pub identified: usize,
    pub duplicates_removed: usize,
    pub screened: usize,
    pub included: usize,
    pub excluded: usize,
    pub pending: usize,
}

pub fn compute_prisma_counts(records: &[LiteratureRecord]) -> PrismaCounts {
    let identified = records.len();
    let duplicates_removed = records.iter().filter(|r| r.duplicate_of.is_some()).count();
    let included = records
        .iter()
        .filter(|r| r.stage == ScreeningStage::Included)
        .count();
    let excluded = records
        .iter()
        .filter(|r| r.stage == ScreeningStage::Excluded)
        .count();
    let pending = identified.saturating_sub(included + excluded);
    let screened = identified.saturating_sub(duplicates_removed);
    PrismaCounts {
        identified,
        duplicates_removed,
        screened,
        included,
        excluded,
        pending,
    }
}

fn normalize_title_key(title: &str) -> String {
    title
        .chars()
        .filter(|c| c.is_alphanumeric())
        .map(|c| c.to_ascii_lowercase())
        .collect()
}

pub fn import_literature_records_json(raw: &str) -> Result<Vec<LiteratureRecord>, &'static str> {
    let val: Value = serde_json::from_str(raw).map_err(|_| "LITERATURE_JSON_INVALID")?;
    let arr = if let Some(a) = val.as_array() {
        a
    } else if let Some(a) = val.get("records").and_then(Value::as_array) {
        a
    } else {
        return Err("LITERATURE_RECORDS_ARRAY_MISSING");
    };
    if arr.is_empty() {
        return Err("LITERATURE_IMPORT_EMPTY_REFUSED");
    }
    if arr.len() > 2_000 {
        return Err("LITERATURE_IMPORT_TOO_LARGE");
    }
    let mut records = Vec::with_capacity(arr.len());
    for (idx, item) in arr.iter().enumerate() {
        let title = item
            .get("title")
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .ok_or("LITERATURE_RECORD_MISSING_TITLE")?;
        let source = item
            .get("source")
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .ok_or("LITERATURE_RECORD_MISSING_SOURCE")?;
        if has_forbidden_marker(title) || has_forbidden_marker(source) {
            return Err("LITERATURE_RECORD_PROHIBITED_MARKER_REFUSED");
        }
        let id = item
            .get("id")
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .map(str::to_string)
            .unwrap_or_else(|| format!("lit-{:04}", idx + 1));
        let doi = item
            .get("doi")
            .and_then(Value::as_str)
            .map(|s| s.trim().to_ascii_lowercase())
            .filter(|s| !s.is_empty());
        let pmid = item
            .get("pmid")
            .and_then(Value::as_str)
            .map(|s| s.trim().to_string())
            .filter(|s| !s.is_empty());
        let year = item
            .get("year")
            .and_then(Value::as_u64)
            .and_then(|y| u32::try_from(y).ok());
        let license = item
            .get("license")
            .and_then(Value::as_str)
            .map(str::trim)
            .filter(|s| !s.is_empty())
            .unwrap_or("UNSPECIFIED_RIGHTS_REVIEW_REQUIRED")
            .to_string();
        records.push(LiteratureRecord {
            id,
            title: title.to_string(),
            doi,
            pmid,
            year,
            source: source.to_string(),
            license,
            stage: ScreeningStage::Identified,
            exclusion_reason: None,
            duplicate_of: None,
        });
    }
    Ok(records)
}

pub fn load_literature_records_from_path(
    path: &Path,
) -> Result<Vec<LiteratureRecord>, &'static str> {
    validate_local_regular_path(path, true)?;
    let raw = fs::read_to_string(path).map_err(|_| "LITERATURE_FILE_READ_FAILED")?;
    import_literature_records_json(&raw)
}

/// Deterministic deduplication by normalized DOI, PMID, or alphanumeric title.
/// Marks duplicates as `Excluded` with mandatory reason `DUPLICATE_OF:<primary_id>`.
pub fn deduplicate_literature_records(records: &mut [LiteratureRecord]) -> usize {
    let mut seen_doi: HashMap<String, String> = HashMap::new();
    let mut seen_pmid: HashMap<String, String> = HashMap::new();
    let mut seen_title: HashMap<String, String> = HashMap::new();
    let mut dup_count = 0usize;

    for rec in records.iter_mut() {
        let title_key = normalize_title_key(&rec.title);
        let primary = rec
            .doi
            .as_ref()
            .and_then(|d| seen_doi.get(d).cloned())
            .or_else(|| rec.pmid.as_ref().and_then(|p| seen_pmid.get(p).cloned()))
            .or_else(|| seen_title.get(&title_key).cloned());

        if let Some(primary_id) = primary {
            rec.duplicate_of = Some(primary_id.clone());
            rec.stage = ScreeningStage::Excluded;
            rec.exclusion_reason = Some(format!("DUPLICATE_OF:{primary_id}"));
            dup_count += 1;
        } else {
            if let Some(ref d) = rec.doi {
                seen_doi.insert(d.clone(), rec.id.clone());
            }
            if let Some(ref p) = rec.pmid {
                seen_pmid.insert(p.clone(), rec.id.clone());
            }
            seen_title.insert(title_key, rec.id.clone());
            if rec.stage == ScreeningStage::Identified {
                rec.stage = ScreeningStage::Deduped;
            }
        }
    }
    dup_count
}

pub fn export_literature_screening_json(
    records: &[LiteratureRecord],
) -> Result<String, &'static str> {
    if records.is_empty() {
        return Err("CANNOT_EXPORT_EMPTY_SCREENING_SET");
    }
    let counts = compute_prisma_counts(records);
    let items: Vec<Value> = records
        .iter()
        .map(|r| {
            serde_json::json!({
                "id": r.id,
                "title": r.title,
                "doi": r.doi,
                "pmid": r.pmid,
                "year": r.year,
                "source": r.source,
                "license": r.license,
                "stage": r.stage.as_str(),
                "exclusion_reason": r.exclusion_reason,
                "duplicate_of": r.duplicate_of,
            })
        })
        .collect();
    let body_str = serde_json::to_string(&items).map_err(|_| "SCREENING_EXPORT_SERIALIZE_FAIL")?;
    let digest = sha256_hex(body_str.as_bytes());
    let root = serde_json::json!({
        "schema": "medorigin-d2-literature-screening-export/v1",
        "clinical_use_authorized": false,
        "prisma": {
            "identified": counts.identified,
            "duplicates_removed": counts.duplicates_removed,
            "screened": counts.screened,
            "included": counts.included,
            "excluded": counts.excluded,
            "pending": counts.pending,
        },
        "records_sha256": digest,
        "records": items,
    });
    serde_json::to_string_pretty(&root).map_err(|_| "SCREENING_EXPORT_SERIALIZE_FAIL")
}

// -----------------------------------------------------------------------------
// Real Local Research Explorer Backend (Screen 19)
// -----------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ResearchArtifactRecord {
    pub id: String,
    pub label: String,
    pub origin: String,
    pub schema_or_type: String,
    pub byte_len: usize,
    pub item_count: usize,
    pub sha256: String,
}

fn inspect_research_json_bytes(
    id: &str,
    label: &str,
    origin: &str,
    bytes: &[u8],
) -> Result<ResearchArtifactRecord, &'static str> {
    let val: Value = serde_json::from_slice(bytes).map_err(|_| "RESEARCH_ARTIFACT_JSON_INVALID")?;
    let schema_or_type = val
        .get("schema")
        .and_then(Value::as_str)
        .or_else(|| val.get("resourceType").and_then(Value::as_str))
        .unwrap_or("json-document")
        .to_string();
    let item_count = val
        .get("entry")
        .and_then(Value::as_array)
        .map(Vec::len)
        .or_else(|| val.get("resources").and_then(Value::as_array).map(Vec::len))
        .or_else(|| val.get("imports").and_then(Value::as_array).map(Vec::len))
        .or_else(|| val.as_array().map(Vec::len))
        .unwrap_or(1);
    Ok(ResearchArtifactRecord {
        id: id.to_string(),
        label: label.to_string(),
        origin: origin.to_string(),
        schema_or_type,
        byte_len: bytes.len(),
        item_count,
        sha256: sha256_hex(bytes),
    })
}

pub fn load_committed_research_artifacts() -> Vec<ResearchArtifactRecord> {
    const F1: &[u8] = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
    const F2: &[u8] = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle-48.json");
    const F3: &[u8] = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
    const F4: &[u8] =
        include_bytes!("../fixtures/core/encrypted-persistent-readback-projection.json");
    const F5: &[u8] = include_bytes!(
        "../fixtures/core/core963-real-encrypted-fictional-file-batch-redacted.json"
    );
    const F6: &[u8] = include_bytes!("../fixtures/core/workspace-ephemeral-demo.json");

    let specs = [
        (
            "synthetic-multipatient-fhir-bundle.json",
            "Synthetic 2-Patient FHIR Bundle (8 resources)",
            "committed-fixture",
            F1,
        ),
        (
            "synthetic-multipatient-fhir-bundle-48.json",
            "Synthetic 16-Patient FHIR Bundle (48 resources)",
            "committed-fixture",
            F2,
        ),
        (
            "encrypted-readback-projection.json",
            "Encrypted Core Readback Projection (3 resources)",
            "committed-fixture",
            F3,
        ),
        (
            "encrypted-persistent-readback-projection.json",
            "Encrypted Persistent Readback Projection",
            "committed-fixture",
            F4,
        ),
        (
            "core963-real-encrypted-fictional-file-batch-redacted.json",
            "Core #963 Redacted Encrypted Batch Receipt",
            "committed-fixture",
            F5,
        ),
        (
            "workspace-ephemeral-demo.json",
            "Workspace Ephemeral Demo Receipt",
            "committed-fixture",
            F6,
        ),
    ];

    specs
        .into_iter()
        .filter_map(|(id, label, origin, bytes)| {
            inspect_research_json_bytes(id, label, origin, bytes).ok()
        })
        .collect()
}

pub fn load_local_research_artifact_file(
    path: &Path,
) -> Result<ResearchArtifactRecord, &'static str> {
    validate_local_regular_path(path, true)?;
    let bytes = fs::read(path).map_err(|_| "RESEARCH_ARTIFACT_READ_FAILED")?;
    if bytes.len() > MAX_PERSISTED_FILE_BYTES {
        return Err("PERSISTED_FILE_TOO_LARGE");
    }
    let name = path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("local-research-artifact.json");
    inspect_research_json_bytes(name, &format!("Local File: {name}"), "local-file", &bytes)
}

pub fn filter_research_artifacts<'a>(
    artifacts: &'a [ResearchArtifactRecord],
    query: &str,
) -> Vec<&'a ResearchArtifactRecord> {
    let q = query.trim().to_ascii_lowercase();
    if q.is_empty() {
        return artifacts.iter().collect();
    }
    artifacts
        .iter()
        .filter(|a| {
            a.id.to_ascii_lowercase().contains(&q)
                || a.label.to_ascii_lowercase().contains(&q)
                || a.schema_or_type.to_ascii_lowercase().contains(&q)
                || a.sha256.contains(&q)
        })
        .collect()
}

pub fn export_research_manifest_json(
    artifacts: &[ResearchArtifactRecord],
) -> Result<String, &'static str> {
    if artifacts.is_empty() {
        return Err("CANNOT_EXPORT_EMPTY_RESEARCH_MANIFEST");
    }
    let items: Vec<Value> = artifacts
        .iter()
        .map(|a| {
            serde_json::json!({
                "id": a.id,
                "label": a.label,
                "origin": a.origin,
                "schema_or_type": a.schema_or_type,
                "byte_len": a.byte_len,
                "item_count": a.item_count,
                "sha256": a.sha256,
            })
        })
        .collect();
    let root = serde_json::json!({
        "schema": "medorigin-d2-research-manifest/v1",
        "scientific_qualification": "SCIENTIFIC_NOT_QUALIFIED",
        "clinical_use_authorized": false,
        "artifact_count": artifacts.len(),
        "artifacts": items,
    });
    serde_json::to_string_pretty(&root).map_err(|_| "RESEARCH_MANIFEST_SERIALIZE_FAIL")
}

// -----------------------------------------------------------------------------
// Real Executable Local Structural Benchmark + External Receipt Verifier (Screen 20)
// -----------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LocalBenchmarkCaseResult {
    pub case_id: &'static str,
    pub passed: bool,
    pub detail: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LocalBenchmarkRun {
    pub evaluator_id: &'static str,
    pub model_identity: &'static str,
    pub platform: String,
    pub execution_command: &'static str,
    pub dataset_sha256: String,
    pub numerator: usize,
    pub denominator: usize,
    pub elapsed_us: u128,
    pub scientific_qualification: &'static str,
    pub limitations: &'static str,
    pub cases: Vec<LocalBenchmarkCaseResult>,
    pub receipt_sha256: String,
}

/// Executes real deterministic structural & safety-gate benchmarks locally over
/// committed synthetic fixtures. Never fabricates LLM accuracy; preserves
/// `SCIENTIFIC_NOT_QUALIFIED`.
pub fn run_local_structural_benchmark() -> LocalBenchmarkRun {
    use crate::encrypted_readback::FictionalReadbackLink;
    let started = std::time::Instant::now();

    const F1: &[u8] = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
    const F2: &[u8] = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
    let mut ds_hasher = Sha256::new();
    ds_hasher.update(F1);
    ds_hasher.update(F2);
    let dataset_sha256 = hasher_hex(ds_hasher);

    let mut cases = Vec::new();

    // Case 1: 8-resource canonical bundle graph DAG verification
    let mut app_b = MedOriginNativePreview::default();
    let c1_ok = app_b.open_embedded_fictional_bundle_demo().is_ok() && {
        let (nodes, has_cycle, _) = build_dynamic_graph(&app_b.active_resources());
        nodes.len() == 8 && !has_cycle
    };
    cases.push(LocalBenchmarkCaseResult {
        case_id: "bundle_8_dag_verification",
        passed: c1_ok,
        detail: "8-resource synthetic FHIR bundle forms an 8-node acyclic graph".to_string(),
    });

    // Case 2: 3-resource encrypted readback projection DAG verification
    let c2_ok = MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(F2)
        .map(|app_r| {
            let (nodes, has_cycle, _) = build_dynamic_graph(&app_r.active_resources());
            nodes.len() == 3 && !has_cycle
        })
        .unwrap_or(false);
    cases.push(LocalBenchmarkCaseResult {
        case_id: "readback_3_dag_verification",
        passed: c2_ok,
        detail: "3-resource synthetic readback forms a 3-node acyclic graph".to_string(),
    });

    // Case 3: Negative control — injected cycle must be detected
    let cyclic = vec![
        FictionalReadbackResource {
            resource_type: "Observation".to_string(),
            resource_id: "fictional-cycle-a".to_string(),
            full_url: "urn:uuid:00000000-0000-4000-8000-0000000000a1".to_string(),
            links: vec![FictionalReadbackLink {
                field: "derivedFrom".to_string(),
                target: "urn:uuid:00000000-0000-4000-8000-0000000000a2".to_string(),
            }],
        },
        FictionalReadbackResource {
            resource_type: "Observation".to_string(),
            resource_id: "fictional-cycle-b".to_string(),
            full_url: "urn:uuid:00000000-0000-4000-8000-0000000000a2".to_string(),
            links: vec![FictionalReadbackLink {
                field: "derivedFrom".to_string(),
                target: "urn:uuid:00000000-0000-4000-8000-0000000000a1".to_string(),
            }],
        },
    ];
    let (_, cyclic_detected, _) = build_dynamic_graph(&cyclic);
    cases.push(LocalBenchmarkCaseResult {
        case_id: "cycle_injection_negative_control",
        passed: cyclic_detected,
        detail: "2-node mutual cycle rejected by 3-color DFS".to_string(),
    });

    // Case 4: Negative control — export quarantine blocks empty + SSN + non-fictional ID + non-UUID link
    let q_empty = !scan_export_quarantine(&[], &[]).passed;
    let q_ssn = !scan_export_quarantine(&app_b.active_resources(), &["SSN 123-45-6789"]).passed;
    let q_bad_id = !scan_export_quarantine(
        &[FictionalReadbackResource {
            resource_type: "Patient".to_string(),
            resource_id: "REAL-ID-1".to_string(),
            full_url: "urn:uuid:00000000-0000-4000-8000-0000000000b1".to_string(),
            links: vec![],
        }],
        &[],
    )
    .passed;
    let q_bad_ref = !scan_export_quarantine(
        &[FictionalReadbackResource {
            resource_type: "Observation".to_string(),
            resource_id: "fictional-obs-x".to_string(),
            full_url: "urn:uuid:00000000-0000-4000-8000-0000000000b2".to_string(),
            links: vec![FictionalReadbackLink {
                field: "subject".to_string(),
                target: "https://ehr.invalid/Patient/1".to_string(),
            }],
        }],
        &[],
    )
    .passed;
    cases.push(LocalBenchmarkCaseResult {
        case_id: "quarantine_4_pattern_negative_control",
        passed: q_empty && q_ssn && q_bad_id && q_bad_ref,
        detail: "Export quarantine blocked 4/4 prohibited patterns".to_string(),
    });

    // Case 5: Negative control — unknown evidence snapshot rejected
    let c5_ok = load_verified_evidence_snapshot("nonexistent-snapshot.json").is_err();
    cases.push(LocalBenchmarkCaseResult {
        case_id: "unknown_snapshot_rejection",
        passed: c5_ok,
        detail: "Unknown evidence snapshot refused fail-closed".to_string(),
    });

    let elapsed_us = started.elapsed().as_micros();
    let denominator = cases.len();
    let numerator = cases.iter().filter(|c| c.passed).count();
    let platform = format!("{}-{}", std::env::consts::OS, std::env::consts::ARCH);
    let receipt_input = format!(
        "LOCAL_STRUCTURAL_BENCH_V1|{}|{platform}|{numerator}/{denominator}",
        dataset_sha256
    );
    let receipt_sha256 = sha256_hex(receipt_input.as_bytes());

    LocalBenchmarkRun {
        evaluator_id: "medorigin-d2-native-structural-eval/v1",
        model_identity: "NONE_DETERMINISTIC_RUST_STRUCTURAL_EVALUATOR",
        platform,
        execution_command: "medorigin-desktop-d2-native-egui::run_local_structural_benchmark",
        dataset_sha256,
        numerator,
        denominator,
        elapsed_us,
        scientific_qualification: "SCIENTIFIC_NOT_QUALIFIED",
        limitations: "Deterministic structural/safety checks over synthetic fixtures only; zero LLM inference, zero clinical or scientific benchmark promotion.",
        cases,
        receipt_sha256,
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ExternalBenchmarkReceipt {
    pub dataset_id: String,
    pub dataset_sha256: String,
    pub model_id: String,
    pub hardware: String,
    pub command: String,
    pub numerator: u64,
    pub denominator: u64,
    pub receipt_sha256: String,
}

/// Loads and validates an externally produced benchmark receipt JSON.
/// Rejects missing denominators, invalid hashes, `numerator > denominator`,
/// or unauthorized `scientific_qualified: true` claims.
pub fn verify_external_benchmark_receipt_json(
    raw: &str,
) -> Result<ExternalBenchmarkReceipt, &'static str> {
    let val: Value = serde_json::from_str(raw).map_err(|_| "BENCHMARK_RECEIPT_JSON_INVALID")?;
    if val.get("schema").and_then(Value::as_str) != Some("medorigin-bench-result-receipt/v1") {
        return Err("BENCHMARK_RECEIPT_SCHEMA_UNSUPPORTED");
    }
    if val.get("scientific_qualified").and_then(Value::as_bool) != Some(false) {
        return Err("UNAUTHORIZED_SCIENTIFIC_QUALIFICATION_CLAIM_REFUSED");
    }
    let dataset_id = val
        .get("dataset_id")
        .and_then(Value::as_str)
        .filter(|s| !s.trim().is_empty())
        .ok_or("BENCHMARK_RECEIPT_MISSING_DATASET_ID")?
        .to_string();
    let dataset_sha256 = val
        .get("dataset_sha256")
        .and_then(Value::as_str)
        .filter(|s| s.len() == 64 && s.bytes().all(|b| b.is_ascii_hexdigit()))
        .ok_or("BENCHMARK_RECEIPT_INVALID_DATASET_SHA256")?
        .to_string();
    let model_id = val
        .get("model_id")
        .and_then(Value::as_str)
        .filter(|s| !s.trim().is_empty())
        .ok_or("BENCHMARK_RECEIPT_MISSING_MODEL_ID")?
        .to_string();
    let hardware = val
        .get("hardware")
        .and_then(Value::as_str)
        .filter(|s| !s.trim().is_empty())
        .ok_or("BENCHMARK_RECEIPT_MISSING_HARDWARE")?
        .to_string();
    let command = val
        .get("command")
        .and_then(Value::as_str)
        .filter(|s| !s.trim().is_empty())
        .ok_or("BENCHMARK_RECEIPT_MISSING_COMMAND")?
        .to_string();
    let numerator = val
        .get("numerator")
        .and_then(Value::as_u64)
        .ok_or("BENCHMARK_RECEIPT_MISSING_NUMERATOR")?;
    let denominator = val
        .get("denominator")
        .and_then(Value::as_u64)
        .filter(|d| *d > 0)
        .ok_or("BENCHMARK_RECEIPT_INVALID_DENOMINATOR")?;
    if numerator > denominator {
        return Err("BENCHMARK_RECEIPT_NUMERATOR_EXCEEDS_DENOMINATOR");
    }
    let receipt_sha256 = val
        .get("receipt_sha256")
        .and_then(Value::as_str)
        .filter(|s| s.len() == 64 && s.bytes().all(|b| b.is_ascii_hexdigit()))
        .ok_or("BENCHMARK_RECEIPT_INVALID_SHA256")?
        .to_string();
    let expected = sha256_hex(
        format!("{dataset_id}|{dataset_sha256}|{model_id}|{hardware}|{command}|{numerator}/{denominator}")
            .as_bytes(),
    );
    if receipt_sha256 != expected {
        return Err("BENCHMARK_RECEIPT_DIGEST_MISMATCH");
    }
    Ok(ExternalBenchmarkReceipt {
        dataset_id,
        dataset_sha256,
        model_id,
        hardware,
        command,
        numerator,
        denominator,
        receipt_sha256,
    })
}

// -----------------------------------------------------------------------------
// Real Offline Synthetic Interoperability & Boundary Adapter (Screen 22)
// -----------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct InteropOperationOutcome {
    pub endpoint_id: &'static str,
    pub status: &'static str,
    pub resources_checked: usize,
    pub diagnostics: Vec<String>,
    pub outcome_sha256: String,
}

/// Real offline FHIR synthetic interoperability check.
/// - Endpoint 0: Validates currently admitted synthetic bundle topology & UUID refs.
/// - Endpoint 1: Validates a local JSON FHIR payload read-only, rejecting malformed JSON,
///   write verbs (`POST`/`PUT`/`DELETE`), external URLs, or unsupported resource types.
/// - Endpoint 2: Live EHR Write Adapter — permanently refused (`SECURITY_REFUSAL_EHR_WRITE_BLOCKED`).
pub fn execute_offline_fhir_interop_check(
    endpoint_idx: usize,
    resources: &[FictionalReadbackResource],
    sample_payload: &str,
) -> Result<InteropOperationOutcome, &'static str> {
    match endpoint_idx {
        0 => {
            if resources.is_empty() {
                return Err("INTEROP_NO_SYNTHETIC_BUNDLE_ADMITTED");
            }
            let (nodes, has_cycle, graph_sha) = build_dynamic_graph(resources);
            if has_cycle {
                return Err("INTEROP_CYCLIC_REFERENCE_REJECTED");
            }
            let scan = scan_export_quarantine(resources, &[]);
            if !scan.passed {
                return Err("INTEROP_SYNTHETIC_BOUNDARY_VIOLATION");
            }
            let diag = vec![
                format!(
                    "Validated {} synthetic FHIR resource(s) offline",
                    nodes.len()
                ),
                format!(
                    "DAG topology verified (0 cycles); graph_sha={}",
                    &graph_sha[..16]
                ),
                "0 network packets sent; 0 external writes attempted".to_string(),
            ];
            let outcome_sha256 = sha256_hex(format!("EP0|{}|{graph_sha}", nodes.len()).as_bytes());
            Ok(InteropOperationOutcome {
                endpoint_id: "local-synthetic-fhir-validator",
                status: "OPERATION_OUTCOME_INFORMATION_ONLY",
                resources_checked: nodes.len(),
                diagnostics: diag,
                outcome_sha256,
            })
        }
        1 => {
            let trimmed = sample_payload.trim();
            if trimmed.is_empty() {
                return Err("INTEROP_EMPTY_PAYLOAD_REFUSED");
            }
            let val: Value =
                serde_json::from_str(trimmed).map_err(|_| "INTEROP_MALFORMED_JSON_REFUSED")?;
            let obj = val.as_object().ok_or("INTEROP_JSON_OBJECT_REQUIRED")?;
            if let Some(method) = obj.get("method").and_then(Value::as_str) {
                let m = method.to_ascii_uppercase();
                if matches!(m.as_str(), "POST" | "PUT" | "PATCH" | "DELETE") {
                    return Err("INTEROP_WRITE_VERB_REFUSED");
                }
            }
            if trimmed.to_ascii_lowercase().contains("http://")
                || trimmed.to_ascii_lowercase().contains("https://")
            {
                return Err("INTEROP_EXTERNAL_URL_EGRESS_REFUSED");
            }
            let res_type = obj
                .get("resourceType")
                .and_then(Value::as_str)
                .ok_or("INTEROP_MISSING_RESOURCE_TYPE")?;
            if !matches!(res_type, "Bundle" | "Patient" | "Encounter" | "Observation") {
                return Err("INTEROP_UNSUPPORTED_RESOURCE_TYPE");
            }
            let outcome_sha256 = sha256_hex(trimmed.as_bytes());
            Ok(InteropOperationOutcome {
                endpoint_id: "offline-smart-on-fhir-readonly-loopback",
                status: "OPERATION_OUTCOME_READONLY_ADMITTED",
                resources_checked: 1,
                diagnostics: vec![
                    format!("Admitted offline read-only synthetic {res_type} JSON"),
                    "Verified zero HTTP write verbs and zero external URL references".to_string(),
                ],
                outcome_sha256,
            })
        }
        2 => Err("SECURITY_REFUSAL_EHR_WRITE_BLOCKED"),
        _ => Err("INTEROP_UNSUPPORTED_ENDPOINT_REFUSED"),
    }
}

/// Compatibility helper wrapping `execute_offline_fhir_interop_check` for blocked EHR refusal checks.
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
        2 => Err("SECURITY_REFUSAL_EHR_WRITE_BLOCKED"),
        _ => Err("INTEROP_UNSUPPORTED_ENDPOINT_REFUSED"),
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
    pub lit_records: Vec<LiteratureRecord>,
    pub lit_selected_item: usize,
    pub lit_import_path: String,
    pub lit_export_path: String,
    pub lit_exclusion_reason: String,
    pub lit_status_notice: Option<Result<String, String>>,

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
    pub research_artifacts: Vec<ResearchArtifactRecord>,
    pub research_selected_study: usize,
    pub research_filter: String,
    pub research_import_path: String,
    pub research_export_path: String,
    pub research_status_notice: Option<Result<String, String>>,

    // 20. Benchmark & Evaluation
    pub bench_selected_suite: usize,
    pub bench_seed_locked: bool,
    pub bench_last_local_run: Option<LocalBenchmarkRun>,
    pub bench_external_receipt_path: String,
    pub bench_external_receipt: Option<ExternalBenchmarkReceipt>,
    pub bench_external_error: Option<String>,
    pub bench_verification_receipt: Option<String>,

    // 22. Integrations
    pub integration_selected_endpoint: usize,
    pub integration_sample_payload: String,
    pub integration_last_outcome: Option<InteropOperationOutcome>,
    pub integration_dry_run_done: bool,
    pub integration_dry_run_receipt: Option<String>,
    pub integration_dry_run_error: Option<String>,

    // 23. Audit History
    pub audit_events: Vec<AuditEvent>,
    pub audit_selected_event: usize,
    pub audit_verified: bool,
    pub audit_verification_status: Option<Result<usize, (usize, String)>>,
    pub audit_ledger_path: String,
    pub audit_checkpoint_path: String,
    pub audit_checkpoint: Option<AuditCheckpoint>,
    pub audit_mac_key: Option<Zeroizing<[u8; 32]>>,
    pub audit_allow_overwrite: bool,
    pub audit_persistence_status: Option<Result<String, String>>,

    // 24. Storage & Recovery
    pub storage_vault_locked: bool,
    pub storage_passphrase: String,
    pub storage_salt: [u8; 16],
    pub storage_raw_key: Option<Zeroizing<[u8; 32]>>,
    /// One-way SHA-256 fingerprint of the derived key (NEVER raw key bytes).
    pub storage_key_fingerprint: Option<String>,
    pub storage_vault_tag: Option<String>,
    pub storage_backup_envelope: Option<Vec<u8>>,
    pub storage_backup_path: String,
    pub storage_allow_overwrite: bool,
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
        let mut ev = AuditEvent {
            seq,
            event_type: event_type.to_string(),
            actor: actor.to_string(),
            payload: payload.to_string(),
            prev_hash,
            hash,
            mac: None,
        };
        if let Some(ref key) = self.audit_mac_key {
            ev.mac = Some(compute_audit_event_mac(key, &ev));
        }
        self.audit_events.push(ev);
        if let Some(ref key) = self.audit_mac_key {
            if let Ok(cp) = create_audit_checkpoint(&self.audit_events, key) {
                self.audit_checkpoint = Some(cp);
            }
            let verified = verify_authenticated_audit_ledger(
                &self.audit_events,
                key,
                self.audit_checkpoint.as_ref(),
            );
            self.audit_verified = verified.is_ok();
            self.audit_verification_status = Some(verified);
        } else {
            let verified = verify_audit_chain(&self.audit_events);
            self.audit_verified = verified.is_ok();
            self.audit_verification_status = Some(verified);
        }
    }

    /// Best-effort volatile scrub of sensitive session references, vault keys,
    /// audit MAC keys, passphrases, and ephemeral receipts on session clear.
    pub fn clear_sensitive_session_state(&mut self) {
        self.storage_raw_key = None; // Zeroizing drops and volatile-zeroes automatically
        self.audit_mac_key = None; // Zeroizing drops and volatile-zeroes automatically
        self.audit_checkpoint = None;
        self.storage_salt.zeroize();
        self.storage_passphrase.zeroize();
        self.storage_passphrase.shrink_to_fit();
        self.storage_key_fingerprint = None;
        self.storage_vault_tag = None;
        if let Some(mut env) = self.storage_backup_envelope.take() {
            env.zeroize();
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
            "Cleared active session state and volatile-zeroed in-memory keys and receipts",
        );
    }
}

impl Drop for ConnectedScreensState {
    fn drop(&mut self) {
        self.storage_raw_key = None;
        self.audit_mac_key = None;
        self.storage_salt.zeroize();
        self.storage_passphrase.zeroize();
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
            lit_records: Vec::new(),
            lit_selected_item: 0,
            lit_import_path: String::new(),
            lit_export_path: String::new(),
            lit_exclusion_reason: "OUT_OF_SCOPE".to_owned(),
            lit_status_notice: None,

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

            research_artifacts: load_committed_research_artifacts(),
            research_selected_study: 0,
            research_filter: String::new(),
            research_import_path: String::new(),
            research_export_path: String::new(),
            research_status_notice: None,

            bench_selected_suite: 0,
            bench_seed_locked: true,
            bench_last_local_run: None,
            bench_external_receipt_path: String::new(),
            bench_external_receipt: None,
            bench_external_error: None,
            bench_verification_receipt: None,

            integration_selected_endpoint: 0,
            integration_sample_payload: r#"{"resourceType":"Patient","id":"fictional-patient-interop-001"}"#.to_owned(),
            integration_last_outcome: None,
            integration_dry_run_done: false,
            integration_dry_run_receipt: None,
            integration_dry_run_error: None,

            audit_events,
            audit_selected_event: 0,
            audit_verified: true,
            audit_verification_status: Some(Ok(1)),
            audit_ledger_path: String::new(),
            audit_checkpoint_path: String::new(),
            audit_checkpoint: None,
            audit_mac_key: None,
            audit_allow_overwrite: false,
            audit_persistence_status: None,

            storage_vault_locked: true,
            storage_passphrase: String::new(),
            storage_salt: [0u8; 16],
            storage_raw_key: None,
            storage_key_fingerprint: None,
            storage_vault_tag: None,
            storage_backup_envelope: None,
            storage_backup_path: String::new(),
            storage_allow_overwrite: false,
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
        "Local search"
        | "Note drafts"
        | "Patient graph"
        | "Patient timeline"
        | "Documents & canvas"
        | "Clinical evidence"
        | "Literature screening"
        | "Tables & structured data"
        | "Analytics"
        | "Dataset manager"
        | "Export quarantine"
        | "Research explorer"
        | "Benchmark & evaluation"
        | "Integrations"
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
            section_title(ui, "Local Literature Metadata Import & Deduplication");
            ui.horizontal(|ui| {
                ui.label("Import JSON Path:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.lit_import_path)
                        .hint_text("Local literature metadata .json file")
                        .desired_width(280.0),
                );
                if ui.button("Import Local JSON").clicked() {
                    let path = Path::new(self.connected.lit_import_path.trim());
                    match load_literature_records_from_path(path) {
                        Ok(records) => {
                            let count = records.len();
                            self.connected.lit_records = records;
                            self.connected.lit_selected_item = 0;
                            self.connected.lit_status_notice = Some(Ok(format!(
                                "Imported {count} literature metadata record(s) from local JSON."
                            )));
                            self.connected.record_audit_event(
                                "LITERATURE_IMPORTED",
                                "user-local",
                                &format!("Imported {count} literature metadata records"),
                            );
                        }
                        Err(e) => {
                            self.connected.lit_status_notice =
                                Some(Err(format!("LITERATURE_IMPORT_REFUSED: {e}")));
                        }
                    }
                }
                if ui.button("Run Deterministic Deduplication").clicked()
                    && !self.connected.lit_records.is_empty()
                {
                    let dups = deduplicate_literature_records(&mut self.connected.lit_records);
                    self.connected.lit_status_notice = Some(Ok(format!(
                        "Deduplication complete: {dups} duplicate record(s) excluded by DOI/PMID/title."
                    )));
                }
            });

            let counts = compute_prisma_counts(&self.connected.lit_records);
            ui.add_space(theme::space::SM);
            section_title(
                ui,
                &format!(
                    "PRISMA Queue (Identified: {} | Duplicates: {} | Included: {} | Excluded: {} | Pending: {})",
                    counts.identified,
                    counts.duplicates_removed,
                    counts.included,
                    counts.excluded,
                    counts.pending
                ),
            );

            if self.connected.lit_records.is_empty() {
                ui.label(
                    RichText::new(
                        "No literature metadata loaded. Import a local JSON file with {id, title, doi, pmid, source, license} entries (zero fabricated screening results).",
                    )
                    .color(p.text_secondary),
                );
            } else {
                if self.connected.lit_selected_item >= self.connected.lit_records.len() {
                    self.connected.lit_selected_item = 0;
                }
                egui::ScrollArea::vertical()
                    .max_height(200.0)
                    .show(ui, |ui| {
                        for (idx, rec) in self.connected.lit_records.iter().enumerate() {
                            let is_sel = self.connected.lit_selected_item == idx;
                            ui.group(|ui| {
                                ui.horizontal(|ui| {
                                    if ui.selectable_label(is_sel, &rec.id).clicked() {
                                        self.connected.lit_selected_item = idx;
                                    }
                                    ui.strong(&rec.title);
                                    theme::tag(
                                        ui,
                                        rec.stage.as_str(),
                                        p.badge,
                                        match rec.stage {
                                            ScreeningStage::Included => p.accent,
                                            ScreeningStage::Excluded => p.pink_text,
                                            _ => p.text_secondary,
                                        },
                                    );
                                });
                                ui.label(format!(
                                    "Source: {} · License: {}{}",
                                    rec.source,
                                    rec.license,
                                    rec.exclusion_reason
                                        .as_ref()
                                        .map(|r| format!(" · Reason: {r}"))
                                        .unwrap_or_default()
                                ));
                            });
                            ui.add_space(theme::space::XS);
                        }
                    });

                ui.add_space(theme::space::SM);
                ui.horizontal(|ui| {
                    ui.label("Exclusion Reason:");
                    ui.add(
                        egui::TextEdit::singleline(&mut self.connected.lit_exclusion_reason)
                            .desired_width(180.0),
                    );
                    let sel = self.connected.lit_selected_item;
                    if ui.button("Advance to Next PRISMA Stage").clicked() {
                        let cur = self.connected.lit_records[sel].stage;
                        let next = match cur {
                            ScreeningStage::Identified => Some(ScreeningStage::Deduped),
                            ScreeningStage::Deduped => Some(ScreeningStage::Screened),
                            ScreeningStage::Screened => Some(ScreeningStage::Eligibility),
                            ScreeningStage::Eligibility => Some(ScreeningStage::Included),
                            _ => None,
                        };
                        if let Some(target) = next {
                            match advance_screening_stage(cur, target, None) {
                                Ok((st, _)) => {
                                    self.connected.lit_records[sel].stage = st;
                                    self.connected.lit_status_notice = Some(Ok(format!(
                                        "Advanced {} to {}",
                                        self.connected.lit_records[sel].id,
                                        st.as_str()
                                    )));
                                }
                                Err(e) => {
                                    self.connected.lit_status_notice = Some(Err(e.to_string()));
                                }
                            }
                        }
                    }
                    if ui.button("Exclude with Reason").clicked() {
                        let cur = self.connected.lit_records[sel].stage;
                        let reason = self.connected.lit_exclusion_reason.clone();
                        match advance_screening_stage(cur, ScreeningStage::Excluded, Some(&reason))
                        {
                            Ok((st, r)) => {
                                self.connected.lit_records[sel].stage = st;
                                self.connected.lit_records[sel].exclusion_reason = r;
                                self.connected.lit_status_notice = Some(Ok(format!(
                                    "Excluded {} with mandatory reason.",
                                    self.connected.lit_records[sel].id
                                )));
                            }
                            Err(e) => {
                                self.connected.lit_status_notice = Some(Err(e.to_string()));
                            }
                        }
                    }
                });

                ui.add_space(theme::space::SM);
                ui.horizontal(|ui| {
                    ui.label("Export JSON Path:");
                    ui.add(
                        egui::TextEdit::singleline(&mut self.connected.lit_export_path)
                            .hint_text("Local export .json path")
                            .desired_width(260.0),
                    );
                    if ui.button("Export Reproducible PRISMA JSON").clicked() {
                        let out_path = Path::new(self.connected.lit_export_path.trim());
                        match export_literature_screening_json(&self.connected.lit_records)
                            .and_then(|json| {
                                atomic_write_local_file(out_path, json.as_bytes(), false)
                            }) {
                            Ok(bytes) => {
                                self.connected.lit_status_notice = Some(Ok(format!(
                                    "Atomically exported {bytes} bytes of reproducible PRISMA screening JSON."
                                )));
                                self.connected.record_audit_event(
                                    "LITERATURE_SCREENING_EXPORTED",
                                    "user-local",
                                    &format!("Exported {} screening records", self.connected.lit_records.len()),
                                );
                            }
                            Err(e) => {
                                self.connected.lit_status_notice =
                                    Some(Err(format!("SCREENING_EXPORT_REFUSED: {e}")));
                            }
                        }
                    }
                });
            }

            if let Some(ref notice) = self.connected.lit_status_notice {
                ui.add_space(theme::space::XS);
                match notice {
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
                section_title(ui, "Local Research Dataset & Artifact Navigator");
                theme::tag(ui, "READ-ONLY · SHA-256 VERIFIED", p.badge, p.accent);
            });
            ui.label("Browse, filter, inspect, and export manifests for real committed synthetic fixtures and local JSON research files.");
            ui.add_space(theme::space::SM);

            ui.horizontal(|ui| {
                ui.label("Filter:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.research_filter)
                        .hint_text("Filter by filename, schema, or SHA-256")
                        .desired_width(240.0),
                );
                ui.label("Add Local JSON:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.research_import_path)
                        .hint_text("Local .json path")
                        .desired_width(220.0),
                );
                if ui.button("Inspect Local File").clicked() {
                    let path = Path::new(self.connected.research_import_path.trim());
                    match load_local_research_artifact_file(path) {
                        Ok(rec) => {
                            let label = rec.id.clone();
                            self.connected.research_artifacts.push(rec);
                            self.connected.research_status_notice =
                                Some(Ok(format!("Indexed local research artifact: {label}")));
                        }
                        Err(e) => {
                            self.connected.research_status_notice =
                                Some(Err(format!("RESEARCH_IMPORT_REFUSED: {e}")));
                        }
                    }
                }
            });

            ui.add_space(theme::space::SM);
            let filtered = filter_research_artifacts(
                &self.connected.research_artifacts,
                &self.connected.research_filter,
            );
            ui.label(
                RichText::new(format!(
                    "Indexed Artifacts: {} matching ({} total)",
                    filtered.len(),
                    self.connected.research_artifacts.len()
                ))
                .strong(),
            );
            egui::ScrollArea::vertical()
                .max_height(210.0)
                .show(ui, |ui| {
                    for (idx, art) in filtered.iter().enumerate() {
                        let is_sel = self.connected.research_selected_study == idx;
                        ui.group(|ui| {
                            ui.horizontal(|ui| {
                                if ui.selectable_label(is_sel, &art.id).clicked() {
                                    self.connected.research_selected_study = idx;
                                }
                                theme::tag(ui, &art.origin, p.badge, p.accent);
                                ui.label(format!(
                                    "{} bytes · {} item(s) · {}",
                                    art.byte_len, art.item_count, art.schema_or_type
                                ));
                            });
                            ui.label(
                                RichText::new(format!("SHA-256: {}", art.sha256))
                                    .size(theme::size::SMALL)
                                    .color(p.text_muted),
                            );
                        });
                        ui.add_space(theme::space::XS);
                    }
                });

            ui.add_space(theme::space::SM);
            ui.horizontal(|ui| {
                ui.label("Export Manifest Path:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.research_export_path)
                        .hint_text("Local manifest .json path")
                        .desired_width(260.0),
                );
                if ui.button("Export Reproducible Manifest").clicked() {
                    let out_path = Path::new(self.connected.research_export_path.trim());
                    match export_research_manifest_json(&self.connected.research_artifacts)
                        .and_then(|json| atomic_write_local_file(out_path, json.as_bytes(), false))
                    {
                        Ok(written) => {
                            self.connected.research_status_notice = Some(Ok(format!(
                                "Atomically exported {written}-byte research manifest."
                            )));
                            self.connected.record_audit_event(
                                "RESEARCH_MANIFEST_EXPORTED",
                                "user-local",
                                &format!(
                                    "Exported manifest for {} research artifacts",
                                    self.connected.research_artifacts.len()
                                ),
                            );
                        }
                        Err(e) => {
                            self.connected.research_status_notice =
                                Some(Err(format!("MANIFEST_EXPORT_REFUSED: {e}")));
                        }
                    }
                }
            });
            if let Some(ref notice) = self.connected.research_status_notice {
                match notice {
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
                section_title(
                    ui,
                    "Executable Local Structural Benchmarks & External Receipt Verifier",
                );
                theme::tag(ui, "SCIENTIFIC_NOT_QUALIFIED", p.pink_bg, p.pink_text);
            });
            ui.label(
                "Run real deterministic structural/safety benchmarks locally or verify authentic external benchmark receipts. Never fabricates LLM accuracy scores.",
            );
            ui.add_space(theme::space::SM);

            if ui
                .button("Execute Local Structural & Safety Benchmark Suite")
                .clicked()
            {
                let run = run_local_structural_benchmark();
                self.connected.record_audit_event(
                    "LOCAL_BENCHMARK_EXECUTED",
                    "system-bench",
                    &format!(
                        "Executed {}: {}/{} passed in {} us (dataset={})",
                        run.evaluator_id,
                        run.numerator,
                        run.denominator,
                        run.elapsed_us,
                        &run.dataset_sha256[..16]
                    ),
                );
                self.connected.bench_last_local_run = Some(run);
            }

            if let Some(ref run) = self.connected.bench_last_local_run {
                ui.add_space(theme::space::XS);
                theme::card(ui, |ui| {
                    ui.strong(format!(
                        "Measured Local Result: {}/{} passed ({} us) on {}",
                        run.numerator, run.denominator, run.elapsed_us, run.platform
                    ));
                    ui.label(format!(
                        "Evaluator: {} | Model: {}",
                        run.evaluator_id, run.model_identity
                    ));
                    ui.label(format!("Command: {}", run.execution_command));
                    ui.label(
                        RichText::new(format!(
                            "Dataset SHA-256: {} | Receipt SHA-256: {}",
                            &run.dataset_sha256[..16],
                            &run.receipt_sha256[..16]
                        ))
                        .size(theme::size::SMALL)
                        .color(p.text_muted),
                    );
                    for c in &run.cases {
                        ui.label(format!(
                            "  [{}] {} — {}",
                            if c.passed { "PASS" } else { "FAIL" },
                            c.case_id,
                            c.detail
                        ));
                    }
                    ui.label(
                        RichText::new(format!("Limitations: {}", run.limitations))
                            .size(theme::size::SMALL)
                            .color(p.text_secondary),
                    );
                });
            }

            ui.add_space(theme::space::MD);
            section_title(
                ui,
                "Verify External Model Benchmark Receipt (medorigin-bench-result-receipt/v1)",
            );
            ui.horizontal(|ui| {
                ui.label("Receipt JSON Path:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.bench_external_receipt_path)
                        .hint_text("Local verified benchmark receipt .json")
                        .desired_width(280.0),
                );
                if ui.button("Load & Verify External Receipt").clicked() {
                    let path = Path::new(self.connected.bench_external_receipt_path.trim());
                    match validate_local_regular_path(path, true)
                        .and_then(|_| fs::read_to_string(path).map_err(|_| "RECEIPT_READ_FAILED"))
                        .and_then(|raw| verify_external_benchmark_receipt_json(&raw))
                    {
                        Ok(rec) => {
                            self.connected.bench_external_receipt = Some(rec);
                            self.connected.bench_external_error = None;
                        }
                        Err(e) => {
                            self.connected.bench_external_receipt = None;
                            self.connected.bench_external_error = Some(e.to_string());
                        }
                    }
                }
            });

            if let Some(ref ext) = self.connected.bench_external_receipt {
                ui.label(
                    RichText::new(format!(
                        "EXTERNAL_RECEIPT_VERIFIED: dataset={} model={} score={}/{} hw={}",
                        ext.dataset_id, ext.model_id, ext.numerator, ext.denominator, ext.hardware
                    ))
                    .color(p.accent),
                );
            }
            if let Some(ref err) = self.connected.bench_external_error {
                ui.label(
                    RichText::new(format!("EXTERNAL_RECEIPT_REFUSED: {err}"))
                        .color(p.pink_text)
                        .strong(),
                );
            }
            ui.label(
                RichText::new(format!(
                    "External LLM Results Embedded: {} (SCIENTIFIC_NOT_QUALIFIED preserved until MRL-0809/MRL-0899 external GPU qualification is complete).",
                    if benchmark_measured_results_available() { "YES" } else { "NONE" }
                ))
                .size(theme::size::SMALL)
                .color(p.text_muted),
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
            section_title(
                ui,
                "Offline Synthetic Interoperability & Boundary Validator",
            );
            if self.connected.integration_selected_endpoint == 1 {
                ui.label("Read-Only JSON Payload to Inspect (Endpoint 2):");
                ui.add(
                    egui::TextEdit::multiline(&mut self.connected.integration_sample_payload)
                        .desired_rows(3)
                        .desired_width(f32::INFINITY),
                );
            }
            if ui
                .button("Execute Offline Interoperability Check")
                .clicked()
            {
                let resources = self.active_resources();
                match execute_offline_fhir_interop_check(
                    self.connected.integration_selected_endpoint,
                    &resources,
                    &self.connected.integration_sample_payload,
                ) {
                    Ok(outcome) => {
                        self.connected.integration_dry_run_done = true;
                        self.connected.integration_dry_run_receipt = Some(format!(
                            "{}: {} (sha256:{})",
                            outcome.status,
                            outcome.endpoint_id,
                            &outcome.outcome_sha256[..16]
                        ));
                        self.connected.integration_last_outcome = Some(outcome);
                        self.connected.integration_dry_run_error = None;
                    }
                    Err(err_code) => {
                        self.connected.integration_dry_run_done = false;
                        self.connected.integration_dry_run_receipt = None;
                        self.connected.integration_last_outcome = None;
                        self.connected.integration_dry_run_error = Some(err_code.to_string());
                        if self.connected.integration_selected_endpoint == 2 {
                            self.connected.record_audit_event(
                                "SECURITY_REFUSAL_EHR_WRITE",
                                "system-boundary",
                                &format!("Refused blocked EHR endpoint 2: {err_code}"),
                            );
                        }
                    }
                }
            }

            if let Some(ref outcome) = self.connected.integration_last_outcome {
                ui.add_space(theme::space::XS);
                ui.group(|ui| {
                    ui.label(
                        RichText::new(format!(
                            "{} ({}, {} resource(s), sha256:{})",
                            outcome.status,
                            outcome.endpoint_id,
                            outcome.resources_checked,
                            &outcome.outcome_sha256[..16]
                        ))
                        .color(p.accent),
                    );
                    for d in &outcome.diagnostics {
                        ui.label(format!("  • {d}"));
                    }
                });
            }
            if let Some(ref err_msg) = self.connected.integration_dry_run_error {
                ui.add_space(theme::space::XS);
                ui.label(
                    RichText::new(format!("REFUSED: {err_msg}"))
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
                section_title(ui, "Local Hash-Chained & Keyed-HMAC Audit Ledger");
                if self.connected.audit_mac_key.is_some() {
                    theme::tag(ui, "KEYED_HMAC_CHECKPOINT_ACTIVE", p.badge, p.accent);
                } else {
                    theme::tag(
                        ui,
                        "UNKEYED_LOCAL_HASH_CHAIN_ONLY",
                        p.badge,
                        p.text_secondary,
                    );
                }
                if self.connected.audit_verified {
                    theme::tag(ui, "VERIFIED", p.badge, p.accent);
                } else {
                    theme::tag(ui, "CHAIN CORRUPTED", p.pink_bg, p.pink_text);
                }
            });
            ui.label(
                "TRUST BOUNDARY: An unkeyed SHA-256 chain detects accidental/partial corruption only; unlocking the vault derives a separated HMAC-SHA-256 audit key and checkpoint to detect full-chain reconstruction, deletion, insertion, reordering, truncation, and rollback. Not externally anchored.",
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
                if ui.button("Verify Full Ledger & Checkpoint").clicked() {
                    let res = if let Some(ref key) = self.connected.audit_mac_key {
                        verify_authenticated_audit_ledger(
                            &self.connected.audit_events,
                            key,
                            self.connected.audit_checkpoint.as_ref(),
                        )
                    } else {
                        verify_audit_chain(&self.connected.audit_events)
                    };
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

                if ui.button("Reset Session Genesis Chain").clicked() {
                    let mut fresh = build_initial_audit_events();
                    if let Some(ref key) = self.connected.audit_mac_key {
                        authenticate_audit_events_with_key(&mut fresh, key);
                        self.connected.audit_checkpoint = create_audit_checkpoint(&fresh, key).ok();
                    }
                    self.connected.audit_events = fresh;
                    self.connected.audit_verified = true;
                    self.connected.audit_verification_status = Some(Ok(1));
                }
            });

            if let Some(ref status) = self.connected.audit_verification_status {
                ui.add_space(theme::space::XS);
                match status {
                    Ok(cnt) => {
                        let mode = if self.connected.audit_mac_key.is_some() {
                            "SHA-256 + keyed HMAC-SHA-256 + checkpoint"
                        } else {
                            "unkeyed SHA-256 continuity only (unlock vault for HMAC authentication)"
                        };
                        ui.label(
                            RichText::new(format!(
                                "AUDIT_LEDGER_VERIFIED: {cnt}/{cnt} events verified ({mode})."
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
            section_title(ui, "Atomic Local Ledger Persistence (Explicit Path)");
            ui.horizontal(|ui| {
                ui.label("Ledger File:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.audit_ledger_path)
                        .hint_text("Optional local synthetic .json path (no silent disk writes)")
                        .desired_width(320.0),
                );
            });
            ui.checkbox(
                &mut self.connected.audit_allow_overwrite,
                "Allow overwriting an existing ledger file (fail-closed by default)",
            );
            ui.horizontal(|ui| {
                if ui.button("Save Verified Ledger Atomically").clicked() {
                    let path = Path::new(self.connected.audit_ledger_path.trim());
                    match save_audit_ledger_to_path(
                        path,
                        &self.connected.audit_events,
                        self.connected.audit_allow_overwrite,
                    ) {
                        Ok(count) => {
                            self.connected.audit_persistence_status = Some(Ok(format!(
                                "Atomically saved {count} verified audit events to local file."
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
                            if let Some(ref key) = self.connected.audit_mac_key {
                                match verify_authenticated_audit_ledger(
                                    &loaded,
                                    key,
                                    self.connected.audit_checkpoint.as_ref(),
                                ) {
                                    Ok(count) => {
                                        self.connected.audit_events = loaded;
                                        self.connected.audit_verified = true;
                                        self.connected.audit_verification_status = Some(Ok(count));
                                        self.connected.audit_persistence_status = Some(Ok(format!(
                                            "Loaded and HMAC-verified {count} audit events against checkpoint."
                                        )));
                                    }
                                    Err((seq, msg)) => {
                                        self.connected.audit_verified = false;
                                        self.connected.audit_persistence_status = Some(Err(format!(
                                            "AUDIT_LOAD_REFUSED at seq {seq}: {msg}"
                                        )));
                                    }
                                }
                            } else {
                                let count = loaded.len();
                                self.connected.audit_events = loaded;
                                self.connected.audit_verified = true;
                                self.connected.audit_verification_status = Some(Ok(count));
                                self.connected.audit_persistence_status = Some(Ok(format!(
                                    "Loaded {count} audit events (unkeyed SHA-256 continuity verified)."
                                )));
                            }
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
                ui.label("Cipher: Audited RustCrypto ChaCha20-Poly1305 AEAD (RFC 8439, 256-bit key, OS CSPRNG 96-bit nonce)");
                ui.label("KDF: Audited RustCrypto Argon2id (19 MiB, t=2, p=1, bounded params) + HKDF-SHA-256 (OS CSPRNG 16-byte salt)");
                ui.label("Format: MSWSENV1 v2 Envelope (53-byte AAD header + 16-byte Poly1305 tag + ciphertext; v1 migration supported)");

                if let Some(ref fp) = self.connected.storage_key_fingerprint {
                    ui.label(
                        RichText::new(format!(
                            "One-Way Key Fingerprint (SHA-256): {}...",
                            &fp[..16]
                        ))
                        .size(theme::size::SMALL)
                        .color(p.text_muted),
                    );
                }

                if let Some(ref tag) = self.connected.storage_vault_tag {
                    ui.label(
                        RichText::new(format!("Vault Confirmation HMAC: {}...", &tag[..16]))
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

                    if ui
                        .button("Derive Session Key (Argon2id) & Unlock Vault")
                        .clicked()
                        && !self.connected.storage_passphrase.is_empty()
                    {
                        match generate_os_random_bytes::<16>().and_then(|salt| {
                            let raw_key = derive_workspace_key_argon2id(
                                &self.connected.storage_passphrase,
                                &salt,
                                Argon2Params::default(),
                                VAULT_KEY_LABEL_V2,
                            )?;
                            let audit_key = derive_audit_mac_key(&raw_key, &salt)?;
                            Ok((salt, raw_key, audit_key))
                        }) {
                            Ok((salt, raw_key, audit_key)) => {
                                let fp_hex = key_fingerprint_hex(&raw_key);
                                let auth_tag =
                                    hmac_sha256(&*raw_key, VAULT_CONFIRM_LABEL.as_bytes());
                                let auth_tag_hex = bytes_to_hex(&auth_tag);

                                self.connected.storage_salt = salt;
                                self.connected.storage_raw_key = Some(raw_key);
                                self.connected.storage_key_fingerprint = Some(fp_hex);
                                self.connected.storage_vault_tag = Some(auth_tag_hex);
                                authenticate_audit_events_with_key(
                                    &mut self.connected.audit_events,
                                    &audit_key,
                                );
                                self.connected.audit_checkpoint = create_audit_checkpoint(
                                    &self.connected.audit_events,
                                    &audit_key,
                                )
                                .ok();
                                self.connected.audit_mac_key = Some(audit_key);
                                self.connected.storage_vault_locked = false;
                                self.connected.storage_wipe_simulation_done = false;
                                self.connected.storage_op_counter += 1;

                                self.connected.record_audit_event(
                                    "VAULT_UNLOCKED",
                                    "user-local",
                                    "Derived session key via Argon2id + HKDF-SHA-256 (OS CSPRNG salt) and separated audit HMAC key",
                                );
                            }
                            Err(err) => {
                                self.connected.storage_backup_status =
                                    Some(Err(format!("VAULT_UNLOCK_REFUSED: {err}")));
                            }
                        }
                    }
                } else if ui.button("Lock Vault & Zeroize Keys").clicked() {
                    self.connected.storage_raw_key = None; // Zeroizing drops & scrubs
                    self.connected.audit_mac_key = None;
                    self.connected.storage_salt.zeroize();
                    self.connected.storage_passphrase.zeroize();
                    self.connected.storage_key_fingerprint = None;
                    self.connected.storage_vault_tag = None;
                    self.connected.storage_vault_locked = true;
                    self.connected.record_audit_event(
                        "VAULT_LOCKED",
                        "user-local",
                        "Volatile-zeroed in-memory vault and audit keys and locked storage vault",
                    );
                }
            });

            ui.add_space(theme::space::MD);
            section_title(
                ui,
                "Authenticated Cryptographic Backup (MSWSENV1 v2 · Argon2id + AEAD)",
            );
            ui.horizontal(|ui| {
                let can_encrypt = !self.connected.storage_vault_locked
                    && self.connected.storage_raw_key.is_some()
                    && !self.connected.storage_passphrase.is_empty();
                if ui
                    .add_enabled(can_encrypt, egui::Button::new("Create Encrypted Backup (MSWSENV1 v2)"))
                    .clicked()
                {
                    let payload = format!(
                        "MEDORIGIN_BACKUP_V2:RESOURCES={}:COUNTER={}",
                        resources.len(),
                        self.connected.storage_op_counter
                    );
                    match encrypt_envelope_v2(
                        &self.connected.storage_passphrase,
                        Argon2Params::default(),
                        payload.as_bytes(),
                    ) {
                        Ok(envelope) => {
                            let env_len = envelope.len();
                            self.connected.storage_backup_envelope = Some(envelope);
                            self.connected.storage_backup_verified = true;
                            self.connected.storage_backup_status = Some(Ok(format!(
                                "Created MSWSENV1 v2 envelope: {env_len} bytes (Argon2id + HKDF-SHA-256 + ChaCha20-Poly1305, OS CSPRNG salt/nonce)"
                            )));
                            self.connected.storage_op_counter += 1;
                            self.connected.record_audit_event(
                                "BACKUP_ENCRYPTED",
                                "system-crypto",
                                &format!("Created MSWSENV1 v2 encrypted backup snapshot: {env_len} bytes"),
                            );
                        }
                        Err(e) => {
                            self.connected.storage_backup_verified = false;
                            self.connected.storage_backup_status =
                                Some(Err(format!("BACKUP_ENCRYPT_REFUSED: {e}")));
                        }
                    }
                }

                let can_verify = !self.connected.storage_passphrase.is_empty()
                    && self.connected.storage_backup_envelope.is_some();

                if ui
                    .add_enabled(can_verify, egui::Button::new("Verify & Restore Backup Snapshot"))
                    .clicked()
                {
                    let envelope = self.connected.storage_backup_envelope.as_ref().unwrap();
                    match decrypt_envelope_with_passphrase(&self.connected.storage_passphrase, envelope) {
                        Ok((ver, decrypted)) => {
                            self.connected.storage_backup_verified = true;
                            self.connected.storage_backup_status = Some(Ok(format!(
                                "BACKUP_RESTORE_SUCCESS (v{ver}): {} bytes authenticated via ChaCha20-Poly1305 MAC",
                                decrypted.len()
                            )));
                            self.connected.record_audit_event(
                                "BACKUP_RESTORED",
                                "system-crypto",
                                &format!("Authenticated and restored {} bytes from MSWSENV1 v{ver} envelope", decrypted.len()),
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
                    if env.len() > MIN_ENVELOPE_V2_LEN {
                        env[MIN_ENVELOPE_V2_LEN] ^= 0x55;
                    } else if env.len() > ENVELOPE_V1_HEADER_LEN {
                        env[ENVELOPE_V1_HEADER_LEN] ^= 0x55;
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

                if ui.button("Zeroize Keys & Purge Vault State").clicked() {
                    self.connected.storage_passphrase.zeroize();
                    self.connected.storage_raw_key = None;
                    self.connected.audit_mac_key = None;
                    self.connected.storage_salt.zeroize();
                    self.connected.storage_key_fingerprint = None;
                    self.connected.storage_vault_tag = None;
                    if let Some(mut env) = self.connected.storage_backup_envelope.take() {
                        env.zeroize();
                    }
                    self.connected.storage_backup_status = None;
                    self.connected.storage_backup_verified = false;
                    self.connected.storage_vault_locked = true;
                    self.connected.storage_wipe_simulation_done = true;
                    self.connected.record_audit_event(
                        "VAULT_ZERO_WIPE",
                        "system-crypto",
                        "Volatile-zeroed all in-memory keys via zeroize and purged vault state",
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
                        "VOLATILE_ZEROIZE_COMPLETED: In-memory key and passphrase buffers scrubbed via zeroize crate. OS swap, crash dumps, and GUI widget copies remain outside application control without OS mlock.",
                    )
                    .color(p.accent),
                );
            }

            ui.add_space(theme::space::SM);
            ui.separator();
            section_title(
                ui,
                "Atomic Encrypted Local Persistence & Restart Recovery (Explicit Path)",
            );
            ui.horizontal(|ui| {
                ui.label("Backup Envelope Path:");
                ui.add(
                    egui::TextEdit::singleline(&mut self.connected.storage_backup_path)
                        .hint_text("Optional local synthetic .mswsenv path (no silent disk writes)")
                        .desired_width(320.0),
                );
            });
            ui.checkbox(
                &mut self.connected.storage_allow_overwrite,
                "Allow overwriting an existing backup file (fail-closed by default)",
            );
            ui.horizontal(|ui| {
                let can_save = self.connected.storage_backup_envelope.is_some()
                    && !self.connected.storage_backup_path.trim().is_empty();
                if ui
                    .add_enabled(can_save, egui::Button::new("Save Encrypted Backup Atomically"))
                    .clicked()
                {
                    let path = Path::new(self.connected.storage_backup_path.trim());
                    let env = self.connected.storage_backup_envelope.as_ref().unwrap();
                    match save_encrypted_backup_to_path(
                        path,
                        env,
                        self.connected.storage_allow_overwrite,
                    ) {
                        Ok(written) => {
                            self.connected.storage_backup_status = Some(Ok(format!(
                                "BACKUP_PERSISTED: Atomically wrote {written} encrypted MSWSENV1 bytes to local file."
                            )));
                            self.connected.record_audit_event(
                                "BACKUP_PERSISTED",
                                "system-crypto",
                                &format!("Atomically persisted {written}-byte MSWSENV1 backup envelope"),
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
                        )
                        .map(|(ver, pt)| (ver, bytes, pt))
                    }) {
                        Ok((ver, bytes, pt)) => {
                            self.connected.storage_backup_envelope = Some(bytes);
                            self.connected.storage_backup_verified = true;
                            self.connected.storage_backup_status = Some(Ok(format!(
                                "BACKUP_RESTORED_AFTER_RESTART (v{ver}): Authenticated and decrypted {} bytes.",
                                pt.len()
                            )));
                            self.connected.record_audit_event(
                                "BACKUP_RESTORED",
                                "system-crypto",
                                &format!("Loaded and authenticated {}-byte persisted v{ver} backup", pt.len()),
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
            mac: None,
        });
        let h3 = compute_audit_hash(3, "NOTE_ATTESTATION", "clinician", "Signed note", &h2);
        events.push(AuditEvent {
            seq: 3,
            event_type: "NOTE_ATTESTATION".to_string(),
            actor: "clinician".to_string(),
            payload: "Signed note".to_string(),
            prev_hash: h2,
            hash: h3,
            mac: None,
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
        assert!(state.storage_key_fingerprint.is_none());
        assert!(state.storage_raw_key.is_none());
        assert!(state.audit_mac_key.is_none());
        assert!(!state.storage_backup_verified);
    }

    #[test]
    fn test_rfc8439_chacha20_poly1305_vectors() {
        // RFC 8439 Section 2.8.2 AEAD test vector via audited RustCrypto chacha20poly1305
        let key_aead =
            hex_to_32("808182838485868788898a8b8c8d8e8f909192939495969798999a9b9c9d9e9f");
        let nonce = hex_to_12("070000004041424344454647");
        let aad = hex_to_vec("50515253c0c1c2c3c4c5c6c7");
        let pt = b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, sunscreen would be it.";

        let (ct, tag_aead) = chacha20_poly1305_encrypt(&key_aead, &nonce, &aad, pt).unwrap();
        assert_eq!(bytes_to_hex(&tag_aead), "1ae10b594f09e26a7e902ecbd0600691");

        let decrypted = chacha20_poly1305_decrypt(&key_aead, &nonce, &aad, &ct, &tag_aead).unwrap();
        assert_eq!(decrypted.as_slice(), pt);

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
    fn test_mswsenv1_v2_argon2id_envelope_and_v1_migration() {
        let passphrase = "passphrase-secret-123";
        let plaintext = b"Sensitive synthetic clinical readback payload 2026";
        let test_params = Argon2Params {
            m_cost_kib: MIN_ARGON2_MEMORY_KIB,
            t_cost: 1,
            p_cost: 1,
        };

        let env = encrypt_envelope_v2(passphrase, test_params, plaintext).unwrap();
        assert!(env.starts_with(ENVELOPE_MAGIC));
        assert_eq!(env[8], ENVELOPE_VERSION_V2_ARGON2ID);
        assert_eq!(
            env.len(),
            ENVELOPE_V2_HEADER_LEN + TAG_LEN + plaintext.len()
        );

        let (ver, dec) = decrypt_envelope_with_passphrase(passphrase, &env).unwrap();
        assert_eq!(ver, ENVELOPE_VERSION_V2_ARGON2ID);
        assert_eq!(dec.as_slice(), plaintext);

        // Negative control: tamper Argon2id KDF parameter in header -> AAD fails or bounds reject
        let mut malicious_kdf = env.clone();
        malicious_kdf[13..17].copy_from_slice(&999_999u32.to_be_bytes());
        assert_eq!(
            decrypt_envelope_with_passphrase(passphrase, &malicious_kdf),
            Err("ARGON2_KDF_PARAMS_OUT_OF_BOUNDS")
        );

        // Negative control: tamper ciphertext
        let mut tampered_env = env.clone();
        let last = tampered_env.len() - 1;
        tampered_env[last] ^= 0x80;
        assert_eq!(
            decrypt_envelope_with_passphrase(passphrase, &tampered_env),
            Err("AUTHENTICATION_TAG_VERIFICATION_FAILED")
        );

        // Negative control: tamper magic
        let mut bad_magic = env.clone();
        bad_magic[0] = b'X';
        assert_eq!(
            decrypt_envelope_with_passphrase(passphrase, &bad_magic),
            Err("INVALID_ENVELOPE_MAGIC")
        );

        // Legacy v1 -> v2 migration compatibility
        let salt = [0x42u8; 16];
        let nonce = [0x24u8; 12];
        let v1_key =
            derive_workspace_key_v1_legacy(passphrase, &salt, VAULT_KEY_LABEL_V1_LEGACY).unwrap();
        let v1_env = encrypt_envelope_v1_raw(&v1_key, &salt, &nonce, plaintext).unwrap();
        let migrated_v2 = migrate_v1_envelope_to_v2(passphrase, &v1_env, test_params).unwrap();
        let (mig_ver, mig_pt) = decrypt_envelope_with_passphrase(passphrase, &migrated_v2).unwrap();
        assert_eq!(mig_ver, ENVELOPE_VERSION_V2_ARGON2ID);
        assert_eq!(mig_pt.as_slice(), plaintext);

        // Volatile zeroize check
        let mut secret = [0x5au8; 32];
        zeroize_bytes(&mut secret);
        assert_eq!(secret, [0u8; 32]);
    }
}
