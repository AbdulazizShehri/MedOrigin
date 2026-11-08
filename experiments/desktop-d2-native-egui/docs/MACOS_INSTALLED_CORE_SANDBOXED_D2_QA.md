# Real installed Python Core Wheel → macOS sandbox → D2 Rust QA — 2026-11-04

**PRIVATE NONCLINICAL QUALIFICATION ONLY. This is NOT a GUI-triggered Core process, clinical application, production installer/venv contract, independent signer trust or permission to use patient information.**

## What changed versus previous source-only Core QA

The previous private D2 #904 ran Python directly from a source checkout. This new self-contained source-controlled QA harness **builds and runs an actual installed Python Wheel**, and binds every installed module byte to the reviewed Core Git SHA and deterministic Wheel ZIP. The GUI still never spawns a process; this test establishes a separate Core packaging and sandbox execution prerequisite rather than weakening D2's browserless/process-denial source guard.

- Reviewed Core QA Git commit: `ad0c62b4366789f5c7e41fc601bb6d0f9d640873` (separate read-only isolated checkout at that exact SHA). Core agents' current #911/#912/#914 work remains untouched; **these pins do not imply the newest Core implementation is qualified**.
- CPython 3.11.15 Apple Silicon locally sourced executable SHA-256: `e3938f2a272dafdc33f3dd12b093dfc85354629476cb97a7d7d4a7201b8482dd`.
- Offline `uv 0.11.20`, `hatchling 1.33.0`, Python `medscale==0.3.0` Wheel built independently **twice** with identical Wheel SHA-256 `4f3a66c9657c8040832970fdffcaa0d2bf15c74c79ae76b17566fe573c9536c2`; package file `medscale-0.3.0-py3-none-any.whl`, approximately 795 KiB. Wheel is NOT committed, uploaded, distributed or published.
- Wheel has **250 files** under `medscale/`, **exactly identical** to 250 Git-tracked `src/medscale/` source files in both inventory and raw bytes. Five additional reviewed wheel metadata files; no `.so`, `.dylib`, `.pth`, `.pyc` or unexpected wheel members.
- Installed into a disposable 0700 `uv venv` using `uv pip install --offline --no-deps`. The harness independently checks exact source-tracked bytes against Wheel and installed `site-packages/medscale/` files, Python package and distribution metadata, RECORD hash/size entries, duplicate/untracked Python files, startup-hook/site-package inventory and package/venv executable identity. `-I -S -B` prohibits executing automatic `.pth`/site/user hooks, while `sys.path` is manually set to this one verified installed package directory. The generated console entrypoint remains unused and never trusted.
- Native Rust QA binary `examples/core_provenance_stdin.rs` (D2 source) was built with offline pinned Rust 1.97.1; local binary SHA-256 `8d1f130b02c326ce0ab6a8765ee2aa094e3ace1815ed9c5497da59f225c4b972`.
- macOS Apple Silicon 26.6.2 local Seatbelt test policy: deny-default network operations, writes allowed only under a freshly created 0700 private temporary directory, process/limited sysctl/Mach lookups and broadly permitted file reads. **Real local 127.0.0.1 unconfined positive connect + sandbox EPERM refusal**, plus unconfined sibling-write positive and sandbox sibling-write refusal, verified before starting the Core process.

## Actual executed full installed-package run

The script `scripts/qualify_installed_synthetic_core.py` runs the installed Core's exact `medscale.cli.fhir.main`, not source modules, for **two fixed, source-pinned fictional-only cases** with one pinned timestamp. Every Core invocation occurs under the actual local OS sandbox, returns **exit 2** and a canonical `status=not_validated` source report. The saved report is byte-equal to stdout; D2's standalone Rust binary consumes and independently validates the report from stdin, returns its exact `FHIR_R4_NOT_VALIDATED` receipt. A tampered report claiming `valid` must be refused. Executable and installed package inventories are rechecked after execution. All ephemeral input/output/venv evidence is nonclinical and local only.

Observed:
```
INSTALLED_WHEEL_TO_D2_SANDBOXED_FICTIONAL_CASE_PASS known
INSTALLED_WHEEL_TO_D2_SANDBOXED_FICTIONAL_CASE_PASS unknown
D2_MAC_INSTALLED_WHEEL_SANDBOXED_CORE_TO_RUST_2_OF_2_PASS_NOT_RELEASE
```

New Python negative tests **7/7 PASS** on Mac (unapproved Wheel hash/name, symlinks, unexpected startup hooks, malformed/duplicate/traversing RECORD, wrong packages/version, source-only host refusal). Prior original sandboxed Core-source tests **10/10 PASS**; D2 native Rust unit tests **34/34 PASS**, browserless/process/network guards **7/7 PASS**, Rust Clippy `-D warnings` PASS. Hosted Windows/Ubuntu CI runs only Python negative **source tests**; the above actual macOS sandbox/Wheel execution is not claimed to occur there.

## Local reproduction — only in disposable private QA paths

```sh
# 1. Make a FULL (not sparse) isolated checkout of the exact Core Git SHA:
git worktree add --detach /tmp/medorigin-d2-installed-core-qa/core-src ad0c62b4366789f5c7e41fc601bb6d0f9d640873
git -C /tmp/medorigin-d2-installed-core-qa/core-src sparse-checkout disable
uv build --offline --wheel --out-dir /tmp/medorigin-d2-installed-core-qa/wheel /tmp/medorigin-d2-installed-core-qa/core-src
uv venv --offline --python /absolute/path/to/pinned/Python3.11 /tmp/medorigin-d2-installed-core-qa/venv
chmod 700 /tmp/medorigin-d2-installed-core-qa/venv
uv pip install --offline --no-deps --python /tmp/medorigin-d2-installed-core-qa/venv/bin/python3.11 /tmp/medorigin-d2-installed-core-qa/wheel/medscale-0.3.0-py3-none-any.whl
# 2. Build the source-bound D2 Rust QA reader without networking:
cargo +1.97.1 build --locked --offline --example core_provenance_stdin
# 3. Run the explicit host/source/wheel/interpreter/reader hash-bound tester:
python3 scripts/qualify_installed_synthetic_core.py \
  --core-source /tmp/medorigin-d2-installed-core-qa/core-src \
  --wheel /tmp/medorigin-d2-installed-core-qa/wheel/medscale-0.3.0-py3-none-any.whl \
  --venv /tmp/medorigin-d2-installed-core-qa/venv \
  --venv-python /tmp/medorigin-d2-installed-core-qa/venv/bin/python3.11 \
  --python-sha256 e3938f2a272dafdc33f3dd12b093dfc85354629476cb97a7d7d4a7201b8482dd \
  --d2-reader /absolute/path/to/compiled/core_provenance_stdin \
  --d2-reader-sha256 8d1f130b02c326ce0ab6a8765ee2aa094e3ace1815ed9c5497da59f225c4b972
```

The script does **not** install or build dependencies itself; it validates inputs and runs only two approved synthetic examples. A different interpreter or Rust build SHA must **not** be admitted without a fresh source/supply-chain review.

## Non-negotiable product/release limits

This Mac test does NOT establish a GUI-to-worker runtime contract, controlled process lifetime on Windows/Linux, code-signing/root of trust, OS-enforced packet/DNS/UDP and descendants confinement, immutable installed runtime or Windows DLL/loader safety, confidentiality of real patient data (macOS `sandbox-exec` is deprecated and currently allows broad reads), clinic-grade encrypted storage, OS key escrow, user authorization, patient consent, or medical FHIR R4 terminology/profile conformance. The newest Core source can differ from this pinned proven version and requires requalification. Therefore NO-GO for PHI, clinical use or publication remains. Retain open #574/#603/#622/#662/#673/#676 and repository Dependabot security debt.
