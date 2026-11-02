# MedOrigin Beta — operator-expected Wheel digest binding

2026-11-02, Windows authorized device. This is a read-only synthetic Developer Beta source and artifact check; no publication or clinical authorization.

## Fixed gap

The existing Core-only Wheel integrity checker attested self-declared RECORD entries, ZIP file consistency, purity and metadata, but did not compare the entire archive to a **separately supplied expected digest**. Added the optional command-line argument `--expected-sha256` and the inspect_wheel expected_sha256 parameter. If supplied, a digest must be **exactly 64 lowercase hexadecimal characters**; invalid or mismatched values are blocking failures and CLI exit 2. The receipt's `expected_digest_matched` is true only when the externally supplied expectation matches the archive and all other checks pass; an absent reference always reports false. `publication_authorized` remains false. Historic metadata-only CLI behavior and strict Core-only opt-in behavior without an external digest remain backward-compatible.

An operator-supplied expected SHA-256 is not a cryptographic signature, is only as trustworthy as its source, and must never be called independent signoff. The script does not fetch trusted references, sign files, install wheels or mutate the frozen source/lock.

## Real authorized Windows read-only evidence

Reference was read from the existing local `D:\MedOrigin-Developer-Beta-e84d89ee-UNPUBLISHED\SOURCE_VERIFICATION_RECEIPT.json`, without editing that file. Its `wheel_sha256` is `f8b7f510e5269623ae98904a6928005ffdefae936db9f5843d2ccd8ceaaba471`. The private Wheel file is `dist\medscale-0.3.0-py3-none-any.whl`.

On native Python 3.11.15 and 3.12.13, the read-only CLI passed `--expected-version 0.3.0 --require-core-only --expected-sha256 <receipt wheel_sha256>`: both exit 0, `expected_digest_matched=true`, `core_only_verified=true`, no issues, and `publication_authorized=false`. Deliberately supplying 64 zeroes gave both exit 2, `status=BLOCKED`, `expected_digest_matched=false`, `core_only_verified=false`, and an explicit digest disagreement reason.

The same local receipt explicitly records `adr_0045_accepted=false`, `independent_review_complete=false`, and `publication_authorized=false`. Therefore this is consistency against an existing local receipt, **not independent artifact authenticity, approval, or release readiness**.

The Python 3.14 regression suite passed 43/43 locally; targeted Ruff and strict mypy passed. Hosted Windows Python 3.11/3.12 synthetic CI must be checked separately on the exact PR SHA.

## Remaining gates

Core verification does not resolve #622 optional extras/root lock advisories, #662 OS-level D1 network containment, #673 Linux dependency maintenance, #676 macOS VoiceOver, #603 independent security review, or #574 versioning and release authorization. No protected main merge, publication, tag, installer, PHI, firewall/ETW audit change, elevated privileges or research lock modifications.
