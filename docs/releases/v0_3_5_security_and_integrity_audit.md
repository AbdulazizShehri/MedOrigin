# MedOrigin v0.3.5 — Security, Persistence, Release Infrastructure & Desktop Integrity Audit

- **Audit Date:** 2026-11-26
- **Audited Release:** [`v0.3.5`](https://github.com/AbdulazizShehri/MedOrigin/releases/tag/v0.3.5) (`d0b82e6b18fc01a9f16b7cd3539320784fcf417f`)
- **Remediation PR:** [`#1018`](https://github.com/AbdulazizShehri/MedOrigin/pull/1018) (`feat/desktop-crypto-audit-governance-hardening`)
- **Governance Track:** Lane A (Synthetic-Only Developer Software) | Lane B `SCIENTIFIC_NOT_QUALIFIED` | Lane C `CLINICAL_NOT_AUTHORIZED`

---

## 1. Repository Access-Security & Collaborator Audit

### 1.1 Current Collaborators on `AbdulazizShehri/MedOrigin` (Verified 2026-11-26)
| GitHub Account | Role | Permissions | Founder-Authorized Maintainer? |
| :--- | :--- | :--- | :--- |
| `AbdulazizShehri` | `admin` | admin, maintain, push, pull, triage | Yes (Repository Owner / Founder) |
| `TheHalfMoon` | `write` | push, pull, triage | Existing repository collaborator |
| `wepld` | `write` | push, pull, triage | **NO — Unauthorized collaborator added during PR #1017** |

### 1.2 Recent Pull Request Approval Chain
| PR | Author | Last Pusher | Approved By | Merged By |
| :-: | :--- | :--- | :--- | :--- |
| `#1010` | `TheHalfMoon` | `TheHalfMoon` | `AbdulazizShehri` | `AbdulazizShehri` |
| `#1013` | `AbdulazizShehri` | `AbdulazizShehri` | `TheHalfMoon` | `AbdulazizShehri` |
| `#1014` | `AbdulazizShehri` | `AbdulazizShehri` | `TheHalfMoon` | `AbdulazizShehri` |
| `#1015` | `AbdulazizShehri` | `AbdulazizShehri` | `TheHalfMoon` | `AbdulazizShehri` |
| `#1016` | `AbdulazizShehri` | `AbdulazizShehri` | `TheHalfMoon` | `AbdulazizShehri` |
| `#1017` | `TheHalfMoon` | `AbdulazizShehri` (`3d0cd21c`) | **`wepld`** | `AbdulazizShehri` |
| `#1018` | `TheHalfMoon` | `TheHalfMoon` | *(Open — awaiting founder review)* | *(Unmerged)* |

### 1.3 Root Cause & Governance Boundary
- Ruleset `MedOrigin canonical main protection v1` (`id: 20172239`) enforces `required_approving_review_count: 1`, `require_last_push_approval: true`, and `bypass_actors: []`.
- Pushing commit `3d0cd21c` to PR #1017 prevented `AbdulazizShehri` from approving the PR; `wepld` was invited and granted WRITE access solely to satisfy GitHub's last-push approval check.
- `wepld` is **not** represented as an independent human reviewer. No additional collaborators were created, invited, or modified during this remediation, and PR #1018 remains open awaiting authorized founder review without bypassing branch protection.

### 1.4 Exact Founder Remediation Command
To revoke `wepld`'s write access on `AbdulazizShehri/MedOrigin`:
```bash
gh api -X DELETE /repos/AbdulazizShehri/MedOrigin/collaborators/wepld
```

---

## 2. Cryptographic Storage, Persistence & Restart Recovery (Screen 24)

Implemented in 100% safe Rust (`unsafe_code = "forbid"`) inside `experiments/desktop-d2-native-egui/src/screens_connected.rs`:
- **Password Key Derivation:** RFC 2898 PBKDF2-HMAC-SHA256 (`25,000` iterations, verified against official PBKDF2-HMAC-SHA256 test vectors) followed by RFC 5869 HKDF-SHA-256 domain separation (`mesc-clinical-workspace-backup-hkdf-sha256/1`).
- **Entropy & Nonce Uniqueness:** 16-byte salts and 96-bit nonces generated via `generate_random_bytes` combining 4 fresh OS-seeded `std::collections::hash_map::RandomState` instances, wall-clock nanoseconds, and a monotonic atomic counter hashed via SHA-256 (eliminates deterministic nonce reuse across restarts).
- **Authenticated Encryption:** RFC 8439 ChaCha20-Poly1305 AEAD verified against official RFC 8439 Section 2.5.2 (Poly1305) and Section 2.8.2 (AEAD) test vectors.
- **Envelope Format (`MSWSENV1`):** 8-byte magic (`MSWSENV1`) + 1-byte version (`0x01`) + 4-byte big-endian key version + 16-byte salt + 12-byte nonce (41-byte authenticated header) + 16-byte Poly1305 MAC tag + ciphertext.
- **Local Persistence & Restart Recovery:** Opt-in explicit-path functions `save_encrypted_backup_to_path`, `load_encrypted_backup_from_path`, and `decrypt_envelope_with_passphrase` reject symlinks/oversize files, verify the authenticated tag on reload, and fail closed on wrong passphrases, empty passphrases, truncated envelopes, or bit-flipped ciphertexts/tags.
- **Honest Memory-Hygiene Boundary:** `zeroize_bytes` overwrites key buffers with `0x00` followed by `compiler_fence(Ordering::SeqCst)` on lock, session clear (`clear_fictional_output`), and `Drop`. Documentation and UI explicitly state this is best-effort in safe Rust without OS memory locking (`mlock`) and does not claim guaranteed OS swap/compiler elimination.

---

## 3. Real Runtime Event Ledger & Trust-Boundary Disclosure (Screen 23)

- Replaced seeded 4-event fixtures with a clean 1-event genesis startup (`GENESIS_STARTUP`) and live runtime recording (`record_audit_event`) across bundle/readback admissions, note attestation, canvas snapshot digests, analytics verification, dataset verification, export quarantine passes and security refusals, blocked EHR write refusals, vault lock/unlock/backup/restore/refusal/wipe events, and session clear.
- Added opt-in explicit-path ledger persistence (`save_audit_ledger_to_path` / `load_audit_ledger_from_path`) that verifies schema, sequence continuity, parent hashes, and SHA-256 digests on load, rejecting any disk-level tampering with exact sequence diagnostics (`AUDIT_CHAIN_CORRUPTED`).
- **Trust Boundary Disclosure:** Both UI and docs explicitly disclose that a local SHA-256 hash chain is **not** externally anchored, independently authenticated, or immutable outside this application's trust boundary.

---

## 4. Release Infrastructure, SBOM & Checksum Verification (`v0.3.5`)

### 4.1 Why `GitHub Release` Was Skipped in Run `44863582726`
In `.github/workflows/release.yml` lines 211–214:
```yaml
if: >-
  github.event_name == 'push' &&
  startsWith(github.ref, 'refs/tags/v') &&
  vars.GITHUB_RELEASE_PUBLISH_ENABLED == 'true'
```
- All mandatory qualification jobs in run `44863582726` passed (`admit tag only at protected main HEAD`, `verify v-tag governance (read-only)`, `quality gate`, `build artifacts`, `clean installed-wheel smoke`).
- `GitHub Release` was skipped by design because repository variable `GITHUB_RELEASE_PUBLISH_ENABLED` is unset (an explicit operator opt-in gate ensuring a passing build is never equivalent to automatic publication). The v0.3.5 GitHub Release was published separately after all qualification gates succeeded.
- Immutable release tags (`v0.3.0`–`v0.3.5`) remain untouched under ADR-0010.

### 4.2 Published `v0.3.5` Checksum & SBOM Verification (Verified 2026-11-26)
All 5 published asset digests on GitHub Release `v0.3.5` match `SHA256SUMS.txt` identically:

| Asset | Size (bytes) | SHA-256 (GitHub Digest == `SHA256SUMS.txt`) | Status |
| :--- | ---: | :--- | :---: |
| `MedOrigin-Synthetic-D2-windows-x86_64-d0b82e6b.zip` | 3,745,761 | `331af2a3622e904470238e8a842475dfc53d0a8c04311d3c7f65ee8b550b137c` | MATCH |
| `MedOrigin-Synthetic-Private-Setup-windows-x86_64.exe` | 3,928,064 | `6e3f91ebf3adbc4f2a271e66ffc681ac5d8fd01aaa167f29c6f4d24b6e768c2c` | MATCH |
| `medscale-0.3.5-py3-none-any.whl` | 889,014 | `91e9bc789a6528500413c1b65200e5bb7d219eb57749ee00c77257a97ed3737b` | MATCH |
| `medscale-0.3.5.tar.gz` | 677,700 | `3ffcde2b127afda01b7614818051158d09adc07aa710001b80a0c4ed7b94b90a` | MATCH |
| `sbom-v0.3.5.cdx.json` | 172,659 | `2ba638663bcc3c678f21313d670208b1db596c07cec332c1ff8799a13411bf90` | MATCH |

- **SBOM Completeness Audit:**
  - `docs/releases/sbom-v0.3.5.cdx.json`: CycloneDX 1.5, **263 components** (`medorigin 0.3.5`), byte-identical to the GitHub Release attachment.
  - `experiments/desktop-d2-native-egui/medorigin-desktop-d2-native-egui.cdx.json`: CycloneDX 1.5, **160 Rust crate components**.
  - **Recommendation for next release:** Attach both the Python/workspace CycloneDX BOM and the Rust D2 crate CycloneDX BOM (or a merged BOM) to future GitHub Releases.

---

## 5. Actual Installed Windows Executable Acceptance Results (Commit `0801bd53`)

Built from commit `0801bd535b5076c874fe4e4508db8f7c939b801f` and qualified in an isolated user profile (`D:\private-installer-qa-20261126`):
- **Native PE Binary SHA-256:** `36259564b26a4da70336d381d4fc784d6a71b1fd60d9939572dc2afe81456fb5`
- **Canonical Portable ZIP SHA-256:** `ec39bce247e9123ac41184a5023013a53bc024978e26ff18ab1f60b4f424b1aa` (`verify_preview.py`: `SYNTHETIC_ARCHIVE_SOURCE_CONTRACT_VERIFIED_NOT_RELEASED`)
- **Single-EXE Setup Installer SHA-256:** `72b47dfd7adcd6477d0a37223cd38714d640c8e34324b8312eaf05030c77fe1b` (`PRIVATE_SYNTHETIC_UNSIGNED_WINDOWS_SETUP_BUILT_NOT_RELEASED`)
- **User-Scope Install & Start Menu Verify:** `PRIVATE_OWNER_WINDOWS_SETUP_EXE_INSTALLED_USER_SCOPE_PASS`, `PRIVATE_OWNER_WINDOWS_INSTALL_VERIFY_AND_START_MENU_PASS`
- **Installed Native UIA Qualifications:**
  - `windows-native-fhir-uia-qualification.ps1`: **PASS** (`D2_NATIVE_FHIR_UIA_8_OF_8_PASS_NONPUBLISHING`)
  - `windows-real-core963-file-batch-receipt-uia.ps1`: **PASS** (`D2_CORE_BATCH_REDACTED_SIDE_BY_SIDE_ACTUAL_WINDOWS_UIA_PASS_NONCLINICAL`)
  - Live 28-screen UIA acceptance pass (`MEDORIGIN_INSTALLED_WINDOWS_EXE_28_SCREEN_LIVE_UIA_PASS`): verified all 4 gated/deferred screens disabled (`IsEnabled == false`) and navigated live Class B/C screens (`Local search`, `Clinical evidence`, `Analytics`, `Export quarantine`, `Benchmark & evaluation`, `Integrations`, `Audit history`, `Storage & recovery`).
- **Tampered Binary Negative Control:** Flipping 1 byte of the installed executable caused `Install-MedOrigin-Private.ps1 -Action Verify` to fail closed (`MEDORIGIN_PRIVATE_WINDOWS_USER_SETUP_NO_GO: payload_sha256_refused`, exit 1); restoring original bytes passed (exit 0).
- **Clean Uninstallation:** `MEDORIGIN_PRIVATE_WINDOWS_USER_UNINSTALL_PASS_SYNTHETIC` (exit 0), installed directory removed (`False`), unrelated user sentinel preserved (`True`).
- **Interactive Desktop Limitation Noted:** Physical Win32 `mouse_event` OLE drag-and-drop test (`windows-native-local-fictional-ole-drop-uia.ps1`) verified the drop hint and reviewed source (`PHYSICAL_WINDOWS_NATIVE_DROP_HINT_AND_REVIEWED_SOURCE_PASS`) but reported `PHYSICAL_OLE_WINDOWS_SYNTHETIC_FILE_DRAG_EFFECT=NOT_INVOKED` under non-interactive background execution (requires an active, unoccluded interactive Windows desktop session).

---

## 6. Frozen Research & Clinical Governance Verification

- `pyproject.toml` SHA-256: `c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510` (unchanged)
- `uv.lock` SHA-256: `6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4` (unchanged)
- `experiments/desktop-d2-native-egui/src/` file count: **15 `.rs` files** (frozen invariant enforced by `browser_free_boundary.rs`)
- Lane B (`MRL-0809`, `MRL-0899`) remains `SCIENTIFIC_NOT_QUALIFIED`.
- Lane C (`CW-021`) remains `CLINICAL_NOT_AUTHORIZED` (zero PHI, zero EHR writes, zero live model execution).
