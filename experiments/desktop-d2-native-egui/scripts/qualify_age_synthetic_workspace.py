#!/usr/bin/env python3
"""Synthetic-only encrypted local workspace QA with age v1.3.1.

NOT production key management, patient data storage, or MedOrigin GUI access.
Uses real age X25519 recipient encryption and never persists fixture plaintext.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory

VERSION = "v1.3.1"
FIXTURE = b'{"id":"medorigin-synthetic-demo","resourceType":"StructureDefinition"}\n'
FIXTURE_SHA256 = "d1f1167a352bbce42e851336d33d0e292902463c1656860bd7cce3ec67598faf"
MAX_CIPHERTEXT = 8192
SUCCESS = "MEDORIGIN_SYNTHETIC_AGE_ENCRYPTED_WORKSPACE_PASS_NOT_CLINICAL"
RECIPIENT_RE = re.compile(r"^Public key: (age1[a-z0-9]{50,100})$", re.MULTILINE)


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prove_binary(path: Path, expected_sha256: str, name: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise ValueError(name + "_unapproved_sha256")
    binary = path.resolve(strict=True)
    if not binary.is_file() or binary.is_symlink() or not os.access(binary, os.X_OK):
        raise ValueError(name + "_not_regular_executable")
    if hash_bytes(binary.read_bytes()) != expected_sha256:
        raise ValueError(name + "_binary_hash_changed")
    version = subprocess.run(
        [str(binary), "--version"], capture_output=True, timeout=6, check=False,
    )
    if version.returncode != 0 or version.stdout.strip().decode("ascii") != VERSION:
        raise ValueError(name + "_version_unqualified")
    return binary


def ensure_private_directory(folder: Path) -> None:
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("workspace_directory_not_regular")
    mode = folder.stat().st_mode
    if os.name == "posix":
        if mode & 0o077 or folder.stat().st_uid != os.getuid():
            raise ValueError("workspace_directory_not_owner_private")


def authorize_fixed_synthetic_only(
    raw: bytes, *, role: str, consent: bool, purpose: str
) -> None:
    # This is a *test intent guard*, not real user authentication or RBAC.
    if role != "synthetic_test_owner" or consent is not True or purpose != "synthetic_workspace_qa":
        raise ValueError("workspace_test_intent_not_authorized")
    if raw != FIXTURE or hash_bytes(raw.rstrip(b"\n")) != FIXTURE_SHA256:
        raise ValueError("workspace_noncanonical_or_patient_payload_refused")


def run_age(binary: Path, args: list[str], *, raw: bytes = b"") -> bytes:
    result = subprocess.run(
        [str(binary), *args],
        input=raw, capture_output=True, timeout=15, check=False,
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": os.environ.get("TMPDIR", "/tmp"),
            "LANG": "C.UTF-8",
        },
    )
    if result.returncode != 0:
        raise ValueError("age_crypto_operation_refused")
    if len(result.stdout) > MAX_CIPHERTEXT:
        raise ValueError("age_output_above_bound")
    return result.stdout


def generate_keypair(keygen: Path, keydir: Path, filename: str) -> tuple[Path, str]:
    ensure_private_directory(keydir)
    key = keydir / filename
    if key.exists() or key.is_symlink():
        raise ValueError("refuse_existing_workspace_identity")
    generated = subprocess.run(
        [str(keygen), "-o", str(key)],
        capture_output=True, timeout=10, check=False,
        env={"PATH": "/usr/bin:/bin", "HOME": str(keydir)},
    )
    if generated.returncode != 0 or generated.stdout:
        raise ValueError("age_key_generation_failed")
    if key.is_symlink() or not key.is_file() or key.stat().st_size > 2048:
        raise ValueError("identity_file_invalid")
    if os.name == "posix" and key.stat().st_mode & 0o077:
        raise ValueError("identity_permissions_insecure")
    matched = RECIPIENT_RE.search(generated.stderr.decode("utf-8"))
    if matched is None:
        raise ValueError("identity_public_recipient_invalid")
    if b"AGE-SECRET-KEY-" not in key.read_bytes():
        raise ValueError("identity_private_key_missing")
    return key, matched.group(1)


def stage_ciphertext_exclusively(vault: Path, name: str, ciphertext: bytes) -> Path:
    ensure_private_directory(vault)
    if not (256 <= len(ciphertext) <= MAX_CIPHERTEXT):
        raise ValueError("workspace_ciphertext_size_refused")
    if not name.isascii() or not re.fullmatch(r"[a-z0-9-]{1,80}\.age", name):
        raise ValueError("workspace_filename_unapproved")
    target = vault / name
    if target.exists() or target.is_symlink():
        raise ValueError("workspace_refuse_replace_existing_ciphertext")
    staged = vault / (name + ".staging")
    if staged.exists() or staged.is_symlink():
        raise ValueError("workspace_staging_conflict")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(staged, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(ciphertext)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name == "posix":
            staged.chmod(0o600)
        # Hard-link on the same volume is atomic and *refuses overwrites*;
        # os.replace would silently clobber a concurrently created target.
        os.link(staged, target, follow_symlinks=False)
        os.unlink(staged)
        if os.name == "posix":
            dir_fd = os.open(vault, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    finally:
        if staged.exists() and not staged.is_symlink():
            staged.unlink()
    return target


def decrypt_memory_only(age: Path, ciphertext: bytes, identity: Path) -> bytes:
    if identity.is_symlink() or not identity.is_file():
        raise ValueError("workspace_identity_not_regular")
    return run_age(age, ["--decrypt", "--identity", str(identity)], raw=ciphertext)


def qualify(age: Path, age_sha: str, keygen: Path, keygen_sha: str) -> None:
    if sys.platform != "darwin" or os.name != "posix":
        raise ValueError("real_macos_local_crypto_qa_required")
    age = prove_binary(age, age_sha, "age")
    keygen = prove_binary(keygen, keygen_sha, "age_keygen")
    authorize_fixed_synthetic_only(
        FIXTURE, role="synthetic_test_owner", consent=True, purpose="synthetic_workspace_qa"
    )
    with TemporaryDirectory(prefix="medorigin-d2-age-workspace-") as temp:
        root = Path(temp)
        root.chmod(0o700)
        vault = root / "ciphertext-only-vault"
        keydir = root / "key-outside-vault"
        backup = root / "encrypted-backup"
        for directory in (vault, keydir, backup):
            directory.mkdir(mode=0o700)
            directory.chmod(0o700)
        key, recipient = generate_keypair(keygen, keydir, "local-synthetic-identity.txt")
        ciphertext = run_age(age, ["--encrypt", "--recipient", recipient], raw=FIXTURE)
        if not ciphertext.startswith(b"age-encryption.org/v1") or FIXTURE in ciphertext:
            raise ValueError("workspace_plaintext_or_unrecognized_crypto")
        target = stage_ciphertext_exclusively(vault, "synthetic-record.age", ciphertext)
        if target.read_bytes() != ciphertext or target.stat().st_mode & 0o077:
            raise ValueError("workspace_at_rest_integrity_or_permissions_refused")
        if b"AGE-SECRET-KEY-" in target.read_bytes():
            raise ValueError("workspace_embedded_private_key")
        if decrypt_memory_only(age, ciphertext, key) != FIXTURE:
            raise ValueError("workspace_correct_key_recovery_failed")
        # Simulate independent backup/recovery by moving ciphertext only;
        # the private key is never copied to the vault or backup.
        recovered = stage_ciphertext_exclusively(backup, "synthetic-backup.age", ciphertext)
        if decrypt_memory_only(age, recovered.read_bytes(), key) != FIXTURE:
            raise ValueError("workspace_encrypted_backup_recovery_failed")
        with_replacement = False
        try:
            stage_ciphertext_exclusively(vault, "synthetic-record.age", ciphertext)
        except ValueError:
            with_replacement = True
        if not with_replacement:
            raise ValueError("workspace_unauthorized_overwrite_accepted")
        wrong_key, _ = generate_keypair(keygen, keydir, "wrong-identity.txt")
        wrong = subprocess.run(
            [str(age), "--decrypt", "--identity", str(wrong_key)],
            input=ciphertext, capture_output=True, timeout=10, check=False,
        )
        if wrong.returncode == 0 or wrong.stdout:
            raise ValueError("workspace_wrong_key_accepted")
        modified = bytearray(ciphertext)
        modified[-1] ^= 0x01
        tampered = subprocess.run(
            [str(age), "--decrypt", "--identity", str(key)],
            input=bytes(modified), capture_output=True, timeout=10, check=False,
        )
        if tampered.returncode == 0 or tampered.stdout:
            raise ValueError("workspace_modified_ciphertext_accepted")
        prove_binary(age, age_sha, "age")
        prove_binary(keygen, keygen_sha, "age_keygen")
        print("SYNTHETIC_WORKSPACE_ENCRYPT_AT_REST_PASS")
        print("SYNTHETIC_WORKSPACE_CORRECT_KEY_AND_BACKUP_RECOVERY_PASS")
        print("SYNTHETIC_WORKSPACE_WRONG_KEY_TAMPER_AND_OVERWRITE_REFUSED")
        print(SUCCESS)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--age", type=Path, required=True)
    p.add_argument("--age-sha256", required=True)
    p.add_argument("--age-keygen", type=Path, required=True)
    p.add_argument("--age-keygen-sha256", required=True)
    args = p.parse_args()
    try:
        qualify(args.age, args.age_sha256, args.age_keygen, args.age_keygen_sha256)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("SYNTHETIC_WORKSPACE_AGE_NO_GO: " + str(exc), file=sys.stderr)
        sys.exit(2)
