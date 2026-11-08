//! Private fictional-only per-launch frame admission for D2.
//! CSPRNG nonce/key come from the trusted launcher; not a signed identity,
//! OS-isolated secret, authenticated patient transport or replay-proof service.
//! No network, no subprocess, no PHI and no new external dependencies.

use sha2::{Digest, Sha256};

pub const SESSION_FLAG: &str = "--synthetic-encrypted-readback-session-stdin";
// Explicit fictional-only focused view: identical HMAC admission, different initial UI.
pub const SESSION_FOCUSED_FLAG: &str = "--synthetic-encrypted-readback-session-focused-stdin";
// A distinct source-scoped Core summary, not interchangeable with the
// historical 2KiB encrypted-readback frame or unbound receipt transport.
pub const SESSION_CORE_BATCH_FLAG: &str = "--synthetic-core-file-batch-session-stdin";
// Separate HMAC for one owner Windows protected fictional audit VERIFY result.
pub const SESSION_PROTECTED_AUDIT_FLAG: &str = "--synthetic-protected-audit-session-stdin";
pub const PROTECTED_AUDIT_TAG: &[u8] = b"MedOrigin-D2-FICTIONAL-PROTECTED-AUDIT-V1\0";
pub const PROTECTED_AUDIT_MAX_FRAME: usize =
    crate::protected_audit::MAX_AUDIT_RECEIPT_BYTES + PROTECTED_AUDIT_TAG.len() + 16 + 32;
pub const CORE_BATCH_TAG: &[u8] = b"MedOrigin-D2-FICTIONAL-CORE-BATCH-V1\0";
pub const CORE_BATCH_HEADER_LEN: usize = CORE_BATCH_TAG.len() + 16 + 32;
pub const CORE_BATCH_FRAME_MAX_BYTES: usize = 4096 + CORE_BATCH_HEADER_LEN;
pub const ENV_SESSION_KEY: &str = "MEDORIGIN_D2_FICTIONAL_SESSION_KEY";
pub const ENV_SESSION_NONCE: &str = "MEDORIGIN_D2_FICTIONAL_SESSION_NONCE";
pub const SESSION_TAG: &[u8] = b"MedOrigin-D2-FICTIONAL-SESSION-V1\0";
pub const HEADER_LEN: usize = SESSION_TAG.len() + 16 + 32;

pub fn decode_fixed_hex<const N: usize>(hex: &str) -> Result<[u8; N], &'static str> {
    if hex.len() != N * 2 || !hex.is_ascii() {
        return Err("fictional_session_secret_length_refused");
    }
    let mut out = [0u8; N];
    let bytes = hex.as_bytes();
    for (index, item) in out.iter_mut().enumerate() {
        fn nibble(value: u8) -> Option<u8> {
            match value {
                b'0'..=b'9' => Some(value - b'0'),
                b'a'..=b'f' => Some(value - b'a' + 10),
                _ => None,
            }
        }
        let upper = nibble(bytes[index * 2]).ok_or("fictional_session_hex_refused")?;
        let lower = nibble(bytes[index * 2 + 1]).ok_or("fictional_session_hex_refused")?;
        *item = (upper << 4) | lower;
    }
    Ok(out)
}

fn hmac_sha256(key: &[u8; 32], message: &[u8]) -> [u8; 32] {
    // RFC 2104 HMAC-SHA256 with a fixed 32-byte key, no dependency additions.
    let mut inner_pad = [0x36u8; 64];
    let mut outer_pad = [0x5cu8; 64];
    for (index, byte) in key.iter().enumerate() {
        inner_pad[index] ^= byte;
        outer_pad[index] ^= byte;
    }
    let mut inner = Sha256::new();
    inner.update(inner_pad);
    inner.update(message);
    let inner_digest = inner.finalize();
    let mut outer = Sha256::new();
    outer.update(outer_pad);
    outer.update(inner_digest);
    let final_digest = outer.finalize();
    final_digest.into()
}

fn verify_fictional_frame_domain<'a>(
    raw: &'a [u8],
    nonce: &[u8; 16],
    secret: &[u8; 32],
    domain: &[u8],
    frame_limit: usize,
) -> Result<&'a [u8], &'static str> {
    let header_len = domain.len() + 16 + 32;
    if raw.len() <= header_len || raw.len() > frame_limit {
        return Err("fictional_session_frame_bounds_refused");
    }
    if !raw.starts_with(domain) {
        return Err("fictional_session_domain_refused");
    }
    let observed_nonce = &raw[domain.len()..domain.len() + 16];
    // No early success even if a different earlier nonce has a valid MAC.
    let mut nonce_difference = 0u8;
    for (a, b) in observed_nonce.iter().zip(nonce.iter()) {
        nonce_difference |= a ^ b;
    }
    if nonce_difference != 0 {
        return Err("fictional_session_nonce_stale_or_foreign");
    }
    let tag_start = domain.len() + 16;
    let payload = &raw[header_len..];
    let length =
        u32::try_from(payload.len()).map_err(|_| "fictional_session_payload_length_refused")?;
    let mut authenticated = Vec::with_capacity(domain.len() + 16 + 4 + payload.len());
    authenticated.extend_from_slice(domain);
    authenticated.extend_from_slice(nonce);
    authenticated.extend_from_slice(&length.to_be_bytes());
    authenticated.extend_from_slice(payload);
    let computed = hmac_sha256(secret, &authenticated);
    let expected = &raw[tag_start..header_len];
    let mut difference = 0u8;
    for (a, b) in expected.iter().zip(computed.iter()) {
        difference |= a ^ b;
    }
    if difference != 0 {
        return Err("fictional_session_mac_refused");
    }
    Ok(payload)
}

pub fn verify_fictional_frame<'a>(
    raw: &'a [u8],
    nonce: &[u8; 16],
    secret: &[u8; 32],
) -> Result<&'a [u8], &'static str> {
    verify_fictional_frame_domain(raw, nonce, secret, SESSION_TAG, 2048)
}

/// Per-process random secret and nonce bind the entire redacted receipt to one
/// local launch. Not signer identity, process isolation or clinical custody.
pub fn verify_fictional_core_batch_frame<'a>(
    raw: &'a [u8],
    nonce: &[u8; 16],
    secret: &[u8; 32],
) -> Result<&'a [u8], &'static str> {
    verify_fictional_frame_domain(
        raw,
        nonce,
        secret,
        CORE_BATCH_TAG,
        CORE_BATCH_FRAME_MAX_BYTES,
    )
}

/// Per-launch fictional protected audit verify only. No process signing,
/// patient-data or clinical user authentication claim.
pub fn verify_fictional_protected_audit_frame<'a>(
    raw: &'a [u8],
    nonce: &[u8; 16],
    secret: &[u8; 32],
) -> Result<&'a [u8], &'static str> {
    verify_fictional_frame_domain(
        raw,
        nonce,
        secret,
        PROTECTED_AUDIT_TAG,
        PROTECTED_AUDIT_MAX_FRAME,
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    fn frame_domain(domain: &[u8], payload: &[u8], nonce: &[u8; 16], key: &[u8; 32]) -> Vec<u8> {
        let mut signed = Vec::new();
        signed.extend_from_slice(domain);
        signed.extend_from_slice(nonce);
        signed.extend_from_slice(&(payload.len() as u32).to_be_bytes());
        signed.extend_from_slice(payload);
        let mac = hmac_sha256(key, &signed);
        let mut out = Vec::new();
        out.extend_from_slice(domain);
        out.extend_from_slice(nonce);
        out.extend_from_slice(&mac);
        out.extend_from_slice(payload);
        out
    }

    fn frame(payload: &[u8], nonce: &[u8; 16], key: &[u8; 32]) -> Vec<u8> {
        frame_domain(SESSION_TAG, payload, nonce, key)
    }

    #[test]
    fn protected_audit_frame_is_distinct_from_batch_and_general_sessions() {
        let nonce = [0x19; 16];
        let secret = [0x39; 32];
        let payload = b"fictional-read-only-audit";
        let frame = frame_domain(PROTECTED_AUDIT_TAG, payload, &nonce, &secret);
        assert_eq!(
            verify_fictional_protected_audit_frame(&frame, &nonce, &secret),
            Ok(payload.as_slice())
        );
        assert!(verify_fictional_core_batch_frame(&frame, &nonce, &secret).is_err());
        assert!(verify_fictional_frame(&frame, &nonce, &secret).is_err());
        assert!(verify_fictional_protected_audit_frame(&frame, &[0x1a; 16], &secret).is_err());
        assert!(verify_fictional_protected_audit_frame(&frame, &nonce, &[0x3a; 32]).is_err());
        for i in [
            0,
            PROTECTED_AUDIT_TAG.len(),
            PROTECTED_AUDIT_TAG.len() + 16,
            PROTECTED_AUDIT_TAG.len() + 48,
        ] {
            let mut altered = frame.clone();
            altered[i] ^= 1;
            assert!(verify_fictional_protected_audit_frame(&altered, &nonce, &secret).is_err());
        }
        assert!(verify_fictional_protected_audit_frame(payload, &nonce, &secret).is_err());
        assert!(
            verify_fictional_protected_audit_frame(
                &vec![b'x'; PROTECTED_AUDIT_MAX_FRAME + 1],
                &nonce,
                &secret
            )
            .is_err()
        );
    }

    #[test]
    fn core_batch_frame_is_bound_to_independent_domain_nonce_key_and_raw_source() {
        let raw = include_bytes!(
            "../fixtures/core/core963-real-encrypted-fictional-file-batch-redacted.json"
        );
        let nonce = [0x11; 16];
        let key = [0x22; 32];
        let frame = frame_domain(CORE_BATCH_TAG, raw, &nonce, &key);
        assert!(frame.len() < CORE_BATCH_FRAME_MAX_BYTES);
        assert_eq!(
            verify_fictional_core_batch_frame(&frame, &nonce, &key),
            Ok(raw.as_slice())
        );
        assert!(verify_fictional_core_batch_frame(&frame, &[0x12; 16], &key).is_err());
        assert!(verify_fictional_core_batch_frame(&frame, &nonce, &[0x23; 32]).is_err());
        let wrong_domain = frame_domain(SESSION_TAG, raw, &nonce, &key);
        assert!(verify_fictional_core_batch_frame(&wrong_domain, &nonce, &key).is_err());
        assert!(verify_fictional_frame(&frame, &nonce, &key).is_err());
        for index in [
            0usize,
            CORE_BATCH_TAG.len(),
            CORE_BATCH_HEADER_LEN - 1,
            CORE_BATCH_HEADER_LEN,
        ] {
            let mut tampered = frame.clone();
            tampered[index] ^= 1;
            assert!(verify_fictional_core_batch_frame(&tampered, &nonce, &key).is_err());
        }
        assert!(
            verify_fictional_core_batch_frame(&frame[..CORE_BATCH_HEADER_LEN], &nonce, &key)
                .is_err()
        );
        assert!(
            verify_fictional_core_batch_frame(&[frame.clone(), vec![0]].concat(), &nonce, &key)
                .is_err()
        );
        assert!(
            verify_fictional_core_batch_frame(
                &vec![0; CORE_BATCH_FRAME_MAX_BYTES + 1],
                &nonce,
                &key
            )
            .is_err()
        );
    }

    #[test]
    fn accepted_per_launch_key_and_nonce_reject_stale_replay_and_forgery() {
        let nonce = [0x5au8; 16];
        let key = [0x3bu8; 32];
        let payload = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let valid = frame(payload, &nonce, &key);
        assert_eq!(
            verify_fictional_frame(&valid, &nonce, &key).expect("authenticated QA frame"),
            payload
        );
        assert!(verify_fictional_frame(&valid, &[0x5bu8; 16], &key).is_err());
        assert!(verify_fictional_frame(&valid, &nonce, &[0x3cu8; 32]).is_err());
        for mutated in [
            {
                let mut c = valid.clone();
                c[HEADER_LEN] ^= 1;
                c
            },
            {
                let mut c = valid.clone();
                c[SESSION_TAG.len() + 16] ^= 1;
                c
            },
            {
                let mut c = valid.clone();
                c[0] ^= 1;
                c
            },
            [valid.clone(), vec![b' ']].concat(),
        ] {
            assert!(verify_fictional_frame(&mutated, &nonce, &key).is_err());
        }
        assert!(verify_fictional_frame(payload, &nonce, &key).is_err());
        assert!(verify_fictional_frame(&valid[..HEADER_LEN], &nonce, &key).is_err());
    }

    #[test]
    fn secret_and_nonce_format_fail_closed() {
        assert_eq!(decode_fixed_hex::<16>(&"12".repeat(16)), Ok([0x12u8; 16]));
        assert!(decode_fixed_hex::<16>(&"12".repeat(15)).is_err());
        assert!(decode_fixed_hex::<32>(&"G1".repeat(32)).is_err());
        assert!(decode_fixed_hex::<32>(&"AA".repeat(32)).is_err());
    }

    #[test]
    fn hmac_known_python_standard_library_golden_vector() {
        // Independently expected digest from Python stdlib:
        // hmac.new(bytes([0x3b])*32, b"hello", hashlib.sha256).hexdigest().
        let digest = hmac_sha256(&[0x3bu8; 32], b"hello");
        let actual = digest
            .iter()
            .map(|x| format!("{x:02x}"))
            .collect::<String>();
        assert_eq!(
            actual,
            "5a72ba66ff1caa9cb76fd3b027019532b7d763ce84f7ffa360e4c3b88f7dcea4"
        );
    }
}
