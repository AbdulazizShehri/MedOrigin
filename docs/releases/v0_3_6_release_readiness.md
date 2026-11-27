# MedOrigin `v0.3.6` — Release Readiness Dossier (Candidate — NOT Tagged or Published)

- **Prepared Date:** 2026-11-27
- **Immutable Current Public Release:** [`v0.3.5`](https://github.com/AbdulazizShehri/MedOrigin/releases/tag/v0.3.5) (`d0b82e6b18fc01a9f16b7cd3539320784fcf417f`)
- **Candidate Branch / PR:** [`#1018`](https://github.com/AbdulazizShehri/MedOrigin/pull/1018) (`feat/desktop-crypto-audit-governance-hardening`)
- **Verified Desktop Build Commit:** `e2c6a621ee5ebd1a135ada7c335bbd3768a177a0`
- **Publication Status:** **NOT TAGGED AND NOT PUBLISHED** — requires founder review/merge of PR `#1018`, revocation of unauthorized collaborator `wepld`, and explicit founder release authorization.

---

## 1. Honest Separate Completion Statuses

| Status Flag | Current Value | Basis & Caveats |
| :--- | :--- | :--- |
| `DESKTOP_ENGINEERING_COMPLETE` | **YES (Synthetic Non-Clinical Scope)** | All 28 screens accounted for (`8 Class A + 16 Class B + 0 Class C + 4 Class D`); `178/178` Rust tests pass; `cargo clippy --locked --all-targets -- -D warnings`, `cargo fmt --check`, and `cargo deny check` pass; installed Windows EXE lifecycle & live UIA verified. Physical Win32 `mouse_event` OLE drag requires an unlocked foreground interactive desktop session (`NOT_INVOKED` under background automation). |
| `SECURITY_ENGINEERING_COMPLETE` | **YES (Local Code Hardened; Pending Founder Repo-Access Action)** | Handwritten crypto & custom PRNG completely replaced with exact-pinned RustCrypto (`argon2 0.6.0`, `chacha20poly1305 0.11.0`, `getrandom 0.4.3`, `hkdf 0.13.0`, `hmac 0.13.0`, `pbkdf2 0.13.0`, `zeroize 1.9.2`); bounded Argon2id DoS guard, keyed HMAC-SHA-256 + rollback-checkpoint audit ledger, atomic writes, and live NTFS junction refusal verified. **External founder action still required:** remove `wepld` collaborator (`gh api -X DELETE /repos/AbdulazizShehri/MedOrigin/collaborators/wepld`) and verify admin-only `/invitations` and `/keys`. |
| `SCIENTIFIC_QUALIFIED` | **NO (`SCIENTIFIC_NOT_QUALIFIED`)** | `pyproject.toml` and `uv.lock` remain byte-frozen. Externally blocked on human Founder `MESC_RECOVERY_3_FINAL_SHA_APPROVAL_V1` in Issue `#450` (`TheHalfMoon`) + authentic Google Colab Free T4 GPU execution. |
| `RELEASE_CANDIDATE_QUALIFIED` | **PENDING FOUNDER REVIEW & MERGE OF PR #1018** | Local Windows release build, packaging, tamper check, live UIA, and unified CycloneDX 1.5 SBOM verified; hosted cross-OS CI verification required on final pushed PR `#1018` head; merge requires authorized founder approval under ruleset `20172239`. |
| `PUBLIC_RELEASED` | **NO** | `v0.3.6` tag has **not** been created and no GitHub Release has been published. `v0.3.5` remains the latest immutable public release. |
| `CLINICAL_USE_AUTHORIZED` | **NO (`CLINICAL_NOT_AUTHORIZED`)** | Lane C permanently enforced: zero PHI, zero live EHR writes, zero billing/order execution, all 4 Class D screens visibly disabled. |

---

## 2. Engineering Changes Since `v0.3.5`

1. **Audited RustCrypto & OS CSPRNG Upgrade (Screen 24):**
   - Replaced handwritten ChaCha20, Poly1305, HMAC, HKDF, PBKDF2, and `RandomState` PRNG with audited RustCrypto crates + `getrandom` + `zeroize`.
   - Upgraded `MSWSENV1` to v2 Argon2id with pre-allocation DoS bounds (`8,192..=262,144` KiB, `t: 1..=10`, `p: 1..=4`) while preserving v1 PBKDF2 decryption and migration (`migrate_v1_envelope_to_v2`).
   - Removed raw key hex strings (`storage_derived_key` -> one-way `storage_key_fingerprint`) and isolated raw keys in `Zeroizing<[u8; 32]>`.
   - Added atomic OS-random sibling writes, default overwrite refusal (`FILE_ALREADY_EXISTS_REFUSED`), and symlink/Windows reparse-point guards verified against live NTFS directory junctions (`mklink /J`).
2. **Keyed HMAC-SHA-256 Authenticated Audit Ledger & Rollback Checkpoints (Screen 23):**
   - Added HKDF-separated `audit_mac_key`, per-event keyed HMAC-SHA-256 (`medorigin-d2-local-audit-chain/v2`), and protected `AuditCheckpoint` (`medorigin-d2-audit-checkpoint/v1`).
   - Verified against all 8 adversarial attack classes (full-chain reconstruction without key, deletion, reordering, insertion, truncation, rollback, partial disk write, wrong key).
3. **Eliminated All Remaining Class C Placeholders (Screens 12, 19, 20, 22 -> Class B):**
   - Screen 12 (`Literature screening`): local JSON import, DOI/PMID/title dedupe, strict PRISMA state machine with mandatory exclusion reasons, atomic JSON export.
   - Screen 19 (`Research explorer`): indexes all 6 committed fixtures + local JSON files with SHA-256 digests, filtering, and atomic manifest export.
   - Screen 20 (`Benchmark & evaluation`): real 5-case executable local structural benchmark + external `medorigin-bench-result-receipt/v1` verifier (rejecting forged `scientific_qualified: true` claims).
   - Screen 22 (`Integrations`): real offline FHIR validator rejecting malformed JSON, HTTP write verbs, external URLs, and unsupported resource types; Endpoint 2 permanently blocked (`SECURITY_REFUSAL_EHR_WRITE_BLOCKED`).

---

## 3. Candidate Artifact & SBOM SHA-256 Inventory (Pre-Release QA Build `e2c6a621`)

> [!IMPORTANT]
> The Windows artifacts below were built and verified locally from commit `e2c6a621ee5ebd1a135ada7c335bbd3768a177a0` in disposable QA directories (subsequently cleaned). Official `v0.3.6` release artifacts must be built from the final merged `main` commit after PR `#1018` merges.

| Artifact | Size (bytes) | SHA-256 | Verification |
| :--- | ---: | :--- | :--- |
| `medorigin-desktop-d2-native-egui.exe` (PE binary) | 9,204,224 | `3ed0c13899e7fd6eef2cb017028041bb424ad20c27f30d6913e5aec32ba719a4` | `cargo build --release --locked`, live UIA |
| `MedOrigin-Synthetic-D2-windows-x86_64-e2c6a621.zip` | 3,782,633 | `8c50067ceb969d125101ae9b8e0d31a9090bb66de3b778b24b4822e98957ceab` | `verify_preview.py` PASS |
| `MedOrigin-Synthetic-Private-Setup-e2c6a621.exe` | 3,969,024 | `693ec1af22ed479cc4a929bc3dacdcbe94f8a68cd59688f1a5fe2f1599ea043c` | Install + Verify + Tamper + Uninstall PASS |
| `docs/releases/sbom-v0.3.6-rc.cdx.json` (Unified Python + Rust CycloneDX 1.5, 282 components) | — | `6bdc87d778b57289cd69d0b5294369c2633676022f1c08fafddc1de10ec916a4` | Generated via `generate_release_sbom.py` + `cargo-cyclonedx` |
| `experiments/desktop-d2-native-egui/medorigin-desktop-d2-native-egui.cdx.json` (Rust D2 CycloneDX 1.5, 179 components) | — | *(tracked in git)* | `cargo cyclonedx --format json --spec-version 1.5` |

---

## 4. Platform Qualification Matrix

| Platform | Automated Build & Test | Packaging & Install Verification | Live GUI / UIA | Caveats |
| :--- | :--- | :--- | :--- | :--- |
| **Windows x86_64** | `178/178` Rust tests, `clippy -D warnings`, `cargo deny check` (local + hosted CI) | ZIP + IExpress single-EXE install, tamper refusal, clean uninstall PASS (local) | FHIR UIA, Core #963 batch UIA, 28-screen Class D/B live UIA PASS | Unsigned private setup; physical Win32 `mouse_event` OLE drag requires unlocked interactive foreground session (`NOT_INVOKED` in background automation). |
| **Ubuntu Linux x86_64** | Hosted CI (`Experimental Native Rust D2`, `native-offline`, `CI`) | Hosted CI tar.gz packaging & contract check | Xvfb smoke in CI | No local Linux hardware sign-off in this session. |
| **macOS arm64** | Hosted CI (`Experimental Native Rust D2`, `native-offline`) | Hosted CI unsigned `.app` ZIP check | Hosted CI | Unsigned/unnotarized developer archive only. |

---

## 5. Founder Pre-Release Checklist (External Actions Required Before `v0.3.6`)

1. Revoke `wepld` collaborator access: `gh api -X DELETE /repos/AbdulazizShehri/MedOrigin/collaborators/wepld`
2. Inspect admin-only endpoints (`/invitations`, `/keys`) on `AbdulazizShehri/MedOrigin`.
3. Review and approve PR `#1018` as authorized founder (`AbdulazizShehri`), then merge into `main`.
4. (Optional for full physical OLE drag attestation) Run `windows-native-local-fictional-ole-drop-uia.ps1` once in an unlocked interactive foreground Windows desktop session.
5. Tag and publish `v0.3.6` ONLY after founder authorization, attaching Python wheel/sdist, Windows ZIP/setup, unified CycloneDX 1.5 SBOM (Python + Rust), and matching `SHA256SUMS.txt`.
