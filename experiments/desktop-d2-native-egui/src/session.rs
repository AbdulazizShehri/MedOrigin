//! Private fictional-only per-launch frame admission for D2.
//! CSPRNG nonce/key come from the trusted launcher; not a signed identity,
//! OS-isolated secret, authenticated patient transport or replay-proof service.
//! No network, no subprocess, no PHI and no new external dependencies.

use sha2::{Digest, Sha256};

pub const SESSION_FLAG: &str = "--synthetic-encrypted-readback-session-stdin";
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

pub fn verify_fictional_frame<'a>(
    raw: &'a [u8],
    nonce: &[u8; 16],
    secret: &[u8; 32],
) -> Result<&'a [u8], &'static str> {
    if raw.len() <= HEADER_LEN || raw.len() > 2048 {
        return Err("fictional_session_frame_bounds_refused");
    }
    if !raw.starts_with(SESSION_TAG) {
        return Err("fictional_session_domain_refused");
    }
    let observed_nonce = &raw[SESSION_TAG.len()..SESSION_TAG.len() + 16];
    // No early success even if a different earlier nonce has a valid MAC.
    let mut nonce_difference = 0u8;
    for (a, b) in observed_nonce.iter().zip(nonce.iter()) {
        nonce_difference |= a ^ b;
    }
    if nonce_difference != 0 {
        return Err("fictional_session_nonce_stale_or_foreign");
    }
    let tag_start = SESSION_TAG.len() + 16;
    let payload = &raw[HEADER_LEN..];
    let length =
        u32::try_from(payload.len()).map_err(|_| "fictional_session_payload_length_refused")?;
    let mut authenticated = Vec::with_capacity(SESSION_TAG.len() + 16 + 4 + payload.len());
    authenticated.extend_from_slice(SESSION_TAG);
    authenticated.extend_from_slice(nonce);
    authenticated.extend_from_slice(&length.to_be_bytes());
    authenticated.extend_from_slice(payload);
    let computed = hmac_sha256(secret, &authenticated);
    let expected = &raw[tag_start..HEADER_LEN];
    let mut difference = 0u8;
    for (a, b) in expected.iter().zip(computed.iter()) {
        difference |= a ^ b;
    }
    if difference != 0 {
        return Err("fictional_session_mac_refused");
    }
    Ok(payload)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn frame(payload: &[u8], nonce: &[u8; 16], key: &[u8; 32]) -> Vec<u8> {
        let mut signed = Vec::new();
        signed.extend_from_slice(SESSION_TAG);
        signed.extend_from_slice(nonce);
        signed.extend_from_slice(&(payload.len() as u32).to_be_bytes());
        signed.extend_from_slice(payload);
        let mac = hmac_sha256(key, &signed);
        let mut out = Vec::new();
        out.extend_from_slice(SESSION_TAG);
        out.extend_from_slice(nonce);
        out.extend_from_slice(&mac);
        out.extend_from_slice(payload);
        out
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
