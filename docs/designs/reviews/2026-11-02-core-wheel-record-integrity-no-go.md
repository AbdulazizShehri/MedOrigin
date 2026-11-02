# Developer Beta: Core Wheel RECORD integrity — 2026-11-02

Status: SOURCE AND ONE PRIVATE SYNTHETIC-ONLY WHEEL QUALIFIED NARROWLY; RELEASE NO-GO.

## Purpose

The earlier Core-only branch validated METADATA and pre/post archive SHA-256. It did not check whether installed payload files agree with their Wheel RECORD digests and sizes. A Wheel may advertise zero dependencies while carrying altered source bytes.

The read-only strict Core integrity checker (scripts/verify_core_wheel_archive.py), invoked only by the require-core-only option, now:

- Requires canonical distribution/version metadata path and a WHEEL file declaring pure py3-none-any.
- Limits members to 10,000, each expanded member to 16 MiB, and total expanded size to 256 MiB.
- Rejects absolute/traversal/backslash/drive-like names, duplicate/case-fold-colliding members and UNIX symlinks.
- Explicitly blocks native code and installer-trigger payload types (.pyd/.so/.dll/.dylib/.exe/.pth/.pyc and shell/PowerShell scripts, plus Wheel .data scripts) in the Core-only payload while allowing normal Python sources; this is a narrowly scoped defense-in-depth check, not a claim that Python source is inherently safe.
- Requires RECORD to cover all files once. Each non-RECORD payload must have a canonical SHA-256 and exact declared size, and RECORD's own digest/size must be blank.
- Rejects duplicated Name/Version METADATA headers and any declared Requires-Dist or Provides-Extra in strict Core-only mode.
- Uses a single open archive file descriptor and never extracts, installs, or executes archive members.

Legacy metadata-only mode remains available but is not a Core integrity qualification.

## Actual Windows evidence

Source branch: security/medorigin-core-wheel-record-integrity-20261102, stacked on unpublished Draft PR #831.

Python 3.14 synthetic regression: 33/33 PASS including same-size RECORD tampering, path traversal, case collision, symlink, metadata-directory spoof, rejection of native/installer payloads, and malformed ZIP. Targeted Ruff lint/format and mypy (two Python sources) PASS. Native Python 3.11.15 and 3.12.13 independently inspected the same unpublished local MedOrigin v0.3.0 Developer Beta Wheel read-only with strict Core flag, both exit 0, issues=[], publication_authorized=false, core_only_verified=true. Observed SHA-256: f8b7f510e5269623ae98904a6928005ffdefae936db9f5843d2ccd8ceaaba471.

Hosted Windows CI 3.11/3.12 on exact PR SHA remains to be verified separately; it exercises synthetic artifacts only, not private Wheel bytes.

## Explicit limitations / NO-GO

RECORD is self-declared. An attacker may change both payload and RECORD. This is not an external signature, independent provenance verification, proof of code safety or proof of network isolation. The canonical frozen research pyproject.toml and uv.lock are unchanged; optional security alerts (#622) remain. Desktop network isolation (#662), macOS VoiceOver (#676), Linux accessibility maintenance (#673), independent review (#603) and owner publication authorization (#574) all remain blocked or incomplete.

No main merge, tag, installer, public release, PHI, policy changes or dependency upgrades are permitted by this bounded source-only check.
