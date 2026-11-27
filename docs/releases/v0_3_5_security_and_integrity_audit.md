# MedOrigin v0.3.5 -> v0.3.6-rc — Security, Persistence, Release Infrastructure & Desktop Integrity Audit

- **Audit Date:** 2026-11-27
- **Audited Published Release (Immutable):** [`v0.3.5`](https://github.com/AbdulazizShehri/MedOrigin/releases/tag/v0.3.5) (`d0b82e6b18fc01a9f16b7cd3539320784fcf417f`)
- **Remediation PR:** [`#1018`](https://github.com/AbdulazizShehri/MedOrigin/pull/1018) (`feat/desktop-crypto-audit-governance-hardening`)
- **Verified Desktop Code Commit:** `e2c6a621ee5ebd1a135ada7c335bbd3768a177a0`
- **Governance Track:** Lane A (Synthetic-Only Developer Software) | Lane B `SCIENTIFIC_NOT_QUALIFIED` | Lane C `CLINICAL_NOT_AUTHORIZED`

---

## 1. Repository Access-Security Incident Audit (Verified 2026-11-27)

### 1.1 Current Collaborators on `AbdulazizShehri/MedOrigin`
| GitHub Account | Role | Permissions | Commits in Repo | Releases Authored | Founder-Authorized Maintainer? |
| :--- | :--- | :--- | :-: | :-: | :--- |
| `AbdulazizShehri` | `admin` | admin, maintain, push, pull, triage | Active | Yes | Yes (Repository Owner / Founder) |
| `TheHalfMoon` | `write` | push, pull, triage | Active | No | Existing repository collaborator |
| `wepld` | `write` | push, pull, triage | **0** | **0** | **NO — Unauthorized collaborator added during PR #1017** |

### 1.2 Recent Pull Request Approval Chain & `wepld` Activity
| PR | Author | Last Pusher | Approved By | Merged By |
| :-: | :--- | :--- | :--- | :--- |
| `#1010` | `TheHalfMoon` | `TheHalfMoon` | `AbdulazizShehri` | `AbdulazizShehri` |
| `#1013` | `AbdulazizShehri` | `AbdulazizShehri` | `TheHalfMoon` | `AbdulazizShehri` |
| `#1014` | `AbdulazizShehri` | `AbdulazizShehri` | `TheHalfMoon` | `AbdulazizShehri` |
| `#1015` | `AbdulazizShehri` | `AbdulazizShehri` | `TheHalfMoon` | `AbdulazizShehri` |
| `#1016` | `AbdulazizShehri` | `AbdulazizShehri` | `TheHalfMoon` | `AbdulazizShehri` |
| `#1017` | `TheHalfMoon` | `AbdulazizShehri` (`3d0cd21c`) | **`wepld`** (2 reviews: `2026-11-21T03:53:09Z`, `03:55:11Z`) | `AbdulazizShehri` |
| `#1018` | `TheHalfMoon` | `TheHalfMoon` | *(Open — awaiting authorized founder review)* | *(Unmerged)* |

### 1.3 Forensic Verification & Admin-Scope Audit Boundary
- **Ruleset Status:** `MedOrigin canonical main protection v1` (`id: 20172239`) remains active with `required_approving_review_count: 1`, `require_last_push_approval: true`, and `bypass_actors: []`.
- **Root Cause of `wepld` Approval on PR #1017:** Pushing commit `3d0cd21c` to PR `#1017` caused `AbdulazizShehri`'s approval (`2026-11-21T03:52:07Z`) not to satisfy `require_last_push_approval: true`; `wepld` was invited and granted WRITE access solely to satisfy GitHub's last-push approval check. `wepld` is **not** represented as an independent human reviewer.
- **Git & Workflow Integrity (`v0.3.0..main`):** `wepld` authored **0 commits** across the entire Git history and **0 releases**. All `.github/workflows/` changes between `v0.3.0` and `main` consist exclusively of the 5 documented v0.3.1–v0.3.3 release-parity commits (`214d3c4c`, `34a98774`, `801557e8`, `eabc64e0`, `dad8ed6c`).
- **Admin-Only Endpoints (Verified Boundary):** Because the automation token operates with non-admin collaborator scope, GitHub returned HTTP `404` on `/repos/AbdulazizShehri/MedOrigin/keys` (deploy keys) and HTTP `403` on `/repos/AbdulazizShehri/MedOrigin/invitations` (pending invitations). No additional collaborators, tokens, or permissions were added or modified during this audit.

### 1.4 Exact Founder Remediation Commands
Run as repository owner (`AbdulazizShehri`):
```bash
# 1. Revoke unauthorized collaborator access
gh api -X DELETE /repos/AbdulazizShehri/MedOrigin/collaborators/wepld

# 2. Verify zero pending invitations and expected deploy keys (requires admin scope)
gh api /repos/AbdulazizShehri/MedOrigin/invitations
gh api /repos/AbdulazizShehri/MedOrigin/keys
```

---

## 2. Audited Cryptographic Storage, Persistence & Restart Recovery (Screen 24)

All handwritten cryptographic primitives (custom ChaCha20, Poly1305, HMAC, HKDF, PBKDF2, and custom `RandomState` PRNG) were removed and replaced with exact-pinned, audited RustCrypto + OS CSPRNG + volatile zeroize crates (`MIT OR Apache-2.0`, 100% safe Rust `unsafe_code = "forbid"`, zero network/browser dependencies, verified passing `cargo deny check`):

- `argon2 = "=0.6.0"` (`default-features = false`, `["alloc", "zeroize"]`)
- `chacha20poly1305 = "=0.11.0"` (`default-features = false`, `["alloc", "zeroize"]`)
- `getrandom = "=0.4.3"` (`default-features = false`)
- `hkdf = "=0.13.0"` (`default-features = false`)
- `hmac = "=0.13.0"` (`default-features = false`, `["zeroize"]`)
- `pbkdf2 = "=0.13.0"` (`default-features = false`, `["hmac"]`)
- `zeroize = "=1.9.2"` (`default-features = false`, `["alloc"]`)
- `sha2 = "=0.11.1"` (unified `digest 0.11` across the entire lockfile)

### 2.1 Cryptographic Design & Envelope Format (`MSWSENV1` v2 + Legacy v1 Migration)
- **OS CSPRNG:** `generate_os_random_bytes` calls `getrandom::fill` directly and fails closed (`OS_CSPRNG_UNAVAILABLE`) if the OS entropy source fails.
- **Memory-Hard KDF (v2):** RFC 9106 Argon2id (`DEFAULT_ARGON2_MEMORY_KIB = 19,456` KiB, `t = 2`, `p = 1`) followed by RFC 5869 HKDF-SHA-256 domain separation (`VAULT_KEY_LABEL_V2`).
- **DoS Bound Enforcement Before Allocation:** Envelope headers carry explicit Argon2id parameters `(m_cost_kib, t_cost, p_cost)` validated against hard limits (`8,192..=262,144` KiB, `t: 1..=10`, `p: 1..=4`) **before** any Argon2 memory allocation occurs (`ARGON2_KDF_PARAMS_OUT_OF_BOUNDS`).
- **AEAD Construction:** RFC 8439 ChaCha20-Poly1305 (`chacha20poly1305` `AeadInOut::encrypt_inout_detached` / `decrypt_inout_detached`), verified against official RFC 8439 Section 2.8.2 test vectors. The full 53-byte v2 header (magic, version `0x02`, key version, `m_cost`, `t_cost`, `p_cost`, 16-byte salt, 12-byte nonce) is authenticated as AAD.
- **Backward-Compatible Legacy Recovery:** `MSWSENV1` v1 (PBKDF2-HMAC-SHA256 + HKDF-SHA-256 + ChaCha20-Poly1305) remains decryptable via `decrypt_envelope_with_passphrase` and upgradable via `migrate_v1_envelope_to_v2`.
- **Secret Hygiene:** Raw vault and audit keys are stored exclusively in `Option<Zeroizing<[u8; 32]>>`; raw key hex strings were removed and replaced with a one-way truncated SHA-256 `key_fingerprint_hex`. Passphrases are scrubbed with `Zeroize::zeroize` on lock, session clear, and `Drop`. UI and docs transparently disclose that safe Rust volatile zeroization does not include OS `mlock` swap prevention.

### 2.2 Hardened Local Persistence Controls
- **Symlink & Windows Reparse-Point Guard (`validate_local_regular_path`):** Inspects target and every existing ancestor directory for Unix symlinks and Windows `FILE_ATTRIBUTE_REPARSE_POINT` (`0x0400`), failing closed (`SYMLINK_OR_NON_FILE_REFUSED`, `SYMLINK_OR_REPARSE_ANCESTOR_REFUSED`). Verified via live Windows NTFS directory junction test (`mklink /J`).
- **Atomic File Writes & Overwrite Protection (`atomic_write_local_file`):** Writes to a fresh OS-random sibling temporary file (`.medorigin.tmp.<rand>`), invokes `sync_all()`, refuses existing files by default (`FILE_ALREADY_EXISTS_REFUSED` when `allow_overwrite == false`), commits via atomic rename/safe swap, and cleans up stray temp files on error. Verified under multi-threaded concurrency and clean restart recovery.

---

## 3. Keyed HMAC-SHA-256 Authenticated Audit Ledger & Rollback Checkpoints (Screen 23)

- **Key Separation:** An independent 32-byte `audit_mac_key` is derived via HKDF-SHA-256 (`AUDIT_MAC_KEY_LABEL`), strictly separated from the vault encryption key (`vault_key != audit_mac_key != key_fingerprint`).
- **Per-Event Domain-Separated HMAC:** Each `AuditEvent` carries both its SHA-256 hash chain link and a keyed `HMAC-SHA-256` tag (`mac: Option<String>`), serialized under `medorigin-d2-local-audit-chain/v2`.
- **Rollback-Detecting Checkpoint (`medorigin-d2-audit-checkpoint/v1`):** `AuditCheckpoint` authenticates `(head_seq, head_hash, head_mac)` with a domain-separated `checkpoint_mac` stored in a separate protected checkpoint file (`save_authenticated_audit_ledger_to_path` / `load_authenticated_audit_ledger_from_path`).
- **Adversarial Verification (`test_authenticated_audit_ledger_adversarial_matrix`):** Proven to defeat all 8 attack classes:
  1. Complete offline SHA-256 chain reconstruction without the HMAC key (`AUDIT_HMAC_VERIFICATION_FAILED`).
  2. Middle-event deletion.
  3. Event reordering.
  4. Duplicate/forged event insertion.
  5. Tail truncation (`AUDIT_ROLLBACK_OR_TRUNCATION_DETECTED`).
  6. Ledger rollback to an earlier valid snapshot (`AUDIT_ROLLBACK_OR_TRUNCATION_DETECTED`).
  7. Partial/truncated disk JSON write (`AUDIT_LEDGER_JSON_INVALID`).
  8. Wrong verification key rejection.
- **Trust Boundary Disclosure:** UI and documentation explicitly disclose that local keyed HMAC checkpoints defeat local tampering and rollback without the secret key, while **not** claiming external third-party timestamping or remote transparency-log anchoring.

---

## 4. Class C -> Class B Research Backends & Class D Governance Boundary

### 4.1 All 4 Former Class C Screens Upgraded to Verified Independent Rust Backends (Class B)
- **Screen 12 (`Literature screening`):** Real local JSON import (`import_literature_records_json`, `load_literature_records_from_path`) with prohibited-marker and schema rejection, deterministic DOI/PMID/normalized-title deduplication (`deduplicate_literature_records`), strict PRISMA state machine (`advance_screening_stage` mirroring `src/medscale/litdb/screening.py` with mandatory non-empty exclusion reasons and terminal `Excluded` state), live PRISMA counts, and reproducible atomic JSON export (`export_literature_screening_json`).
- **Screen 19 (`Research explorer`):** Real indexer over all 6 committed research/workspace fixtures (`load_committed_research_artifacts`) plus local JSON artifact loading (`load_local_research_artifact_file`) with runtime SHA-256 digests, live substring/digest filtering (`filter_research_artifacts`), and atomic manifest export (`export_research_manifest_json`).
- **Screen 20 (`Benchmark & evaluation`):** Real executable local deterministic structural benchmark (`run_local_structural_benchmark`, 5 positive and negative-control test cases with wall-clock timing, dataset SHA-256, platform, command, denominator, limitations, and explicit `SCIENTIFIC_NOT_QUALIFIED`) PLUS external receipt verifier (`verify_external_benchmark_receipt_json` for `medorigin-bench-result-receipt/v1`, rejecting missing/zero denominators, `numerator > denominator`, digest mismatches, and unauthorized `scientific_qualified: true` claims). Never fabricates LLM accuracy (`benchmark_measured_results_available() == false`).
- **Screen 22 (`Integrations`):** Real offline FHIR interoperability validator (`execute_offline_fhir_interop_check`): Endpoint 0 validates active bundle DAG topology and quarantine compliance; Endpoint 1 validates offline read-only FHIR JSON while rejecting malformed JSON, HTTP write verbs (`POST`/`PUT`/`PATCH`/`DELETE`), external URLs (`http://`/`https://`), and unsupported resource types; Endpoint 2 permanently refuses live EHR writes (`SECURITY_REFUSAL_EHR_WRITE_BLOCKED`).

### 4.2 Class D Governance Evaluation (Screens 4, 6, 7, 21)
All 4 Class D screens remain visibly disabled (`IsEnabled=False`, non-clickable) in `src/screens.rs`, verified by both `test_all_four_gated_screens_are_disabled` and live Windows AccessKit/UIA inspection:
- **Screen 4 (`Audio & transcript`, `Tag::Gated`):** Live microphone capture and clinical transcription remain unqualified under Lane C; future non-clinical enablement requires an explicit offline synthetic-audio-only contract and privacy gate.
- **Screen 6 (`Orders & tasks`, `Tag::Gated`):** External clinical order/task creation and EHR writeback are permanently prohibited under Lane C (`CW-021`).
- **Screen 7 (`Coding suggestions`, `Tag::Deferred`):** Clinical billing/coding suggestions and submission remain permanently deferred and disabled.
- **Screen 21 (`Model catalog & runtime`, `Tag::Gated`):** Local LLM execution and model weight management remain gated under Lane B (`SCIENTIFIC_NOT_QUALIFIED`) until independent model provenance, hardware qualification, and evaluation gates pass.

---

## 5. Scientific Qualification Status (`MRL-0809` / `MRL-0899`)

- **Current Status:** `SCIENTIFIC_NOT_QUALIFIED` (preserved without exception).
- **Frozen Research Roots Verified Byte-Identical:**
  - `pyproject.toml`: `c36c33208236dafb136a147dfff0060d592e23daab4b4240521d4747d23ea510`
  - `uv.lock`: `6fa0e0b49d19e305032ecd04940db0b9e252dd23b6fbec588b224f739048efc4`
- **External Blockers (Cannot Be Automated or Fabricated):** Per `docs/releases/mrl0809_drift_portability_20261023.md` and `docs/execution/mrl_0809_evidence_recovery_3_activation_runbook.md`, advancing `MRL-0809` / `MRL-0899` requires (1) explicit human Founder `MESC_RECOVERY_3_FINAL_SHA_APPROVAL_V1` sign-off in Issue `#450` (under `TheHalfMoon`) and (2) an authentic Google Colab Free T4 GPU execution producing signed benchmark receipts.

---

## 6. Release Infrastructure, Immutable `v0.3.5` Verification & New Installed Windows EXE Acceptance (`e2c6a621`)

### 6.1 Published `v0.3.5` Checksum Verification (Immutable Baseline)
All 5 published asset digests on GitHub Release `v0.3.5` match `SHA256SUMS.txt` identically:

| Asset | Size (bytes) | SHA-256 (GitHub Digest == `SHA256SUMS.txt`) | Status |
| :--- | ---: | :--- | :---: |
| `MedOrigin-Synthetic-D2-windows-x86_64-d0b82e6b.zip` | 3,745,761 | `331af2a3622e904470238e8a842475dfc53d0a8c04311d3c7f65ee8b550b137c` | MATCH |
| `MedOrigin-Synthetic-Private-Setup-windows-x86_64.exe` | 3,928,064 | `6e3f91ebf3adbc4f2a271e66ffc681ac5d8fd01aaa167f29c6f4d24b6e768c2c` | MATCH |
| `medscale-0.3.5-py3-none-any.whl` | 889,014 | `91e9bc789a6528500413c1b65200e5bb7d219eb57749ee00c77257a97ed3737b` | MATCH |
| `medscale-0.3.5.tar.gz` | 677,700 | `3ffcde2b127afda01b7614818051158d09adc07aa710001b80a0c4ed7b94b90a` | MATCH |
| `sbom-v0.3.5.cdx.json` | 172,659 | `2ba638663bcc3c678f21313d670208b1db596c07cec332c1ff8799a13411bf90` | MATCH |

- `GitHub Release` job in run `44863582726` was skipped by design because repository variable `GITHUB_RELEASE_PUBLISH_ENABLED` is unset (operator opt-in gate in `.github/workflows/release.yml` lines 211–214). Immutable release tags `v0.3.0`–`v0.3.5` remain untouched under ADR-0010.

### 6.2 Actual Installed Windows Executable Acceptance Results (Commit `e2c6a621ee5ebd1a135ada7c335bbd3768a177a0`)
Built with `cargo build --release --locked --bin medorigin-desktop-d2-native-egui` and qualified in disposable task-owned directories (`D:\medorigin-qa-dist-20261127`, `D:\private-installer-qa-20261127`, `D:\private-installer-qa-20261127-lifecycle`, all cleaned after QA):

- **Native PE Binary (`medorigin-desktop-d2-native-egui.exe`):** `9,204,224` bytes, SHA-256 `3ed0c13899e7fd6eef2cb017028041bb424ad20c27f30d6913e5aec32ba719a4`
- **Canonical Portable ZIP (`MedOrigin-Synthetic-D2-windows-x86_64-e2c6a621.zip`):** `3,782,633` bytes, SHA-256 `8c50067ceb969d125101ae9b8e0d31a9090bb66de3b778b24b4822e98957ceab` (`verify_preview.py`: `SYNTHETIC_ARCHIVE_SOURCE_CONTRACT_VERIFIED_NOT_RELEASED`)
- **Single-EXE Setup Installer (`MedOrigin-Synthetic-Private-Setup-e2c6a621.exe`):** `3,969,024` bytes, SHA-256 `693ec1af22ed479cc4a929bc3dacdcbe94f8a68cd59688f1a5fe2f1599ea043c` (`PRIVATE_SYNTHETIC_UNSIGNED_WINDOWS_SETUP_BUILT_NOT_RELEASED`)
- **Full Installer Lifecycle Verification (`qualify_windows_private_user_setup.py`):**
  - `PRIVATE_OWNER_WINDOWS_SETUP_EXE_INSTALLED_USER_SCOPE_PASS`
  - `PRIVATE_OWNER_WINDOWS_INSTALL_VERIFY_AND_START_MENU_PASS`
  - `PRIVATE_OWNER_WINDOWS_TAMPERED_PINNED_PAYLOAD_VERIFY_REFUSED`
  - `MEDORIGIN_PRIVATE_OWNER_WINDOWS_SETUP_INSTALL_GUI_UNINSTALL_PASS_SYNTHETIC_NOT_RELEASED`
- **Live Installed Windows UIA Qualifications:**
  - `PRIVATE_OWNER_WINDOWS_INSTALLED_NATIVE_UIA_PASS=windows-native-fhir-uia-qualification.ps1`
  - `PRIVATE_OWNER_WINDOWS_INSTALLED_NATIVE_UIA_PASS=windows-real-core963-file-batch-receipt-uia.ps1`
  - Live AccessKit/UIA 28-screen verification (`LIVE_UIA_SUMMARY foundGated=4 foundClassB=6 stillAlive=True`): confirmed all 4 Class D screens (`Audio & transcript`, `Orders & tasks`, `Coding suggestions`, `Model catalog & runtime`) report `IsEnabled=False`, and all 6 newly hardened/implemented Class B screens (`Literature screening`, `Research explorer`, `Benchmark & evaluation`, `Integrations`, `Audit history`, `Storage & recovery`) report `IsEnabled=True`.
- **Honest External Desktop-Session Caveat (Physical Win32 OLE Drag-and-Drop):**
  - Direct run of `windows-native-local-fictional-ole-drop-uia.ps1` against the release binary verified `PHYSICAL_WINDOWS_NATIVE_DROP_HINT_AND_REVIEWED_SOURCE_PASS`, then reported `PHYSICAL_OLE_WINDOWS_SYNTHETIC_FILE_DRAG_EFFECT=NOT_INVOKED` (exit code 2: `real_windows_ole_drop_was_not_admitted_by_native_app`).
  - Under automated background/occluded desktop execution, Win32 `mouse_event` cannot complete an interactive OLE drag across windows. Full physical OLE drag acceptance requires an unlocked, unoccluded interactive Windows foreground desktop session.
- **Updated CycloneDX 1.5 SBOMs:**
  - Rust D2 crate SBOM (`experiments/desktop-d2-native-egui/medorigin-desktop-d2-native-egui.cdx.json`): **179 components** (includes audited `argon2 0.6.0`, `chacha20poly1305 0.11.0`, `getrandom 0.4.3`, `hkdf 0.13.0`, `hmac 0.13.0`, `pbkdf2 0.13.0`, `zeroize 1.9.2`).
  - Unified candidate SBOM (`docs/releases/sbom-v0.3.6-rc.cdx.json`): **282 components** (Python `uv.lock` + 179 Rust D2 crates), SHA-256 `6bdc87d778b57289cd69d0b5294369c2633676022f1c08fafddc1de10ec916a4`.
