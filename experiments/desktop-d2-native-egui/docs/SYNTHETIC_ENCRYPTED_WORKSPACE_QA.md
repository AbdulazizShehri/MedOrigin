# Synthetic D2 encrypted workspace admission — 2026-11-04

**Nonclinical local security prototype only. No production patient storage, clinical Workspace, actual user authentication, Keychain/TPM backing, or package/release approval.**

## What is source-implemented

`scripts/qualify_age_synthetic_workspace.py` uses locally installed open-source `age` v1.3.1 and `age-keygen` v1.3.1, with explicit executable SHA-256 pins, to encrypt **one exact allowlisted synthetic `StructureDefinition` fixture**. The fixture hash matches Core's independent synthetic source: `d1f1167a352bbce42e851336d33d0e292902463c1656860bd7cce3ec67598faf`. The script refuses all other payloads, all roles other than `synthetic_test_owner`, missing/false consent or any alternate declared purpose. This is a fixed test-intent guard, **not** real RBAC, session authorization or legal patient consent.

A disposable 0700 test root contains **separate** 0700 `ciphertext-only-vault`, `key-outside-vault` and `encrypted-backup` directories. `age-keygen -o` generates a disposable X25519 recipient identity with 0600 secret-file mode. The script sends the fictional fixture directly via stdin to `age --encrypt`, receives ciphertext in memory, and atomically publishes only ciphertext using an O_EXCL/no-follow 0600 staging file plus no-overwrite hardlink, with file and directory fsync. Neither plaintext nor secret key enters the vault/backup; no cloud service is used.

For acceptance it reads the encrypted file, decrypts **only in memory** with the correct identity, verifies a separately stored encrypted backup's recovery, requires decryption failure for an independently generated wrong private key and for a tampered ciphertext, verifies non-overwrite/path-traversal/symlink/permissions rejection, rehashes both cryptographic binaries and deletes the disposable key, ciphertext and directories.

### Real test host and evidence

- Real Apple Silicon Mac, macOS 26.6.2.
- Local `age` binary SHA-256: `f52e5ee772e1c0e3c6be5bf837b469a40346df3515db9a1b41230376fdff6a76`.
- Local `age-keygen` binary SHA-256: `4a0de88e9365ee19910d2cc067b6f2f3f7895cd9917493b15173ddf31a96a9fe`.
- Real CLI crypto returned `SYNTHETIC_WORKSPACE_ENCRYPT_AT_REST_PASS`, `SYNTHETIC_WORKSPACE_CORRECT_KEY_AND_BACKUP_RECOVERY_PASS`, `SYNTHETIC_WORKSPACE_WRONG_KEY_TAMPER_AND_OVERWRITE_REFUSED`, `MEDORIGIN_SYNTHETIC_AGE_ENCRYPTED_WORKSPACE_PASS_NOT_CLINICAL` with exit 0.
- **9/9** standalone Python negative/source tests PASS on Mac, plus preceding sandboxed Core fixture tests **10/10** PASS. CI may run static/negative Python tests on Windows and Linux, **but must not claim** actual `age` encryption on hosted runners without installing/verifying the pinned CLI and executing it.
- The exact input is fictional and cannot be changed using a CLI flag or file path; user-supplied or clinical files are not accepted.

## Reproduction on an authorized Mac (no cloud, no PHI)

```sh
cd experiments/desktop-d2-native-egui
python3 -m unittest discover -s scripts -p test_age_synthetic_workspace.py -v
python3 scripts/qualify_age_synthetic_workspace.py \
  --age /opt/homebrew/bin/age \
  --age-sha256 f52e5ee772e1c0e3c6be5bf837b469a40346df3515db9a1b41230376fdff6a76 \
  --age-keygen /opt/homebrew/bin/age-keygen \
  --age-keygen-sha256 4a0de88e9365ee19910d2cc067b6f2f3f7895cd9917493b15173ddf31a96a9fe
```

## Blockers before ANY actual patient record

This proves a local cryptographic **mechanism on a synthetic fixture**, not a production clinical workspace or an independently reviewed encryption design. The private identity is temporarily stored unencrypted on disk in the same OS user account (albeit separately from the vault). Before real records, implement and qualify OS-native **Keychain/TPM/libsecret** custody, authenticated user and device sessions, key unlock/revocation/rotation, crash-safe atomic multi-record transactions, encrypted indexes/metadata and backup manifests, secure recovery and authenticated audit trails, retention/delete and consent policies, migration and locked/vault-corruption UX, installation/updater safety, cross-OS negative proofs, adversarial fuzzing, independent cryptography/security review and clinical-risk approval.

D2's native app does **not** import this test tool or read/write these vault files. No actual patient data, FHIR validation, EHR import/export, application integration, signing, publication or protected main merge was enabled. All outstanding release blockers remain NO-GO.
