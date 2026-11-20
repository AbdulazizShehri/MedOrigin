# macOS synthetic Core → D2 OS-sandboxed integration — 2026-11-04

**Nonclinical developer acceptance only. This does not convert D2 into an installed Python Core client or authorize patient records, clinical claims or a release.**

## Tested source and binaries

- MedOrigin Core independent QA checkout from private Draft PR #901, source commit `ad0c62b4366789f5c7e41fc601bb6d0f9d640873`. Do not mutate the concurrent Core agent's worktree.
- D2 based on private Draft PR #902, source commit `952a4d21bd4954b1d33161441325dd1944571302` before addition of the standalone QA-only reader.
- Real authorized Apple Silicon Mac running macOS 26.6.2, native Python 3.11.15 and offline-compiled Rust 1.97.1 D2 `examples/core_provenance_stdin.rs`.
- Observed local Python binary SHA-256 `e3938f2a272dafdc33f3dd12b093dfc85354629476cb97a7d7d4a7201b8482dd`; local Rust QA reader SHA-256 `18e360de40c7b9619225f49ea2772f1fdb221ab25fc1eb75e6b7e22162406023`. These are **locally measured pins**, not independent signed/software-supply-chain attestation.

## Source-controlled test procedure

1. In an **isolated disposable checkout** of Core at the pinned commit, admit only the tracked `src/medscale` modules and `examples/synthetic_fhir_developer_beta` fixtures. The runner compares every on-disk source/fixture file against `git ls-files` and refuses untracked or ignored `__pycache__`/bytecode, symlinks, missing files or changed tracked files, so an unchanged Git HEAD alone is not considered enough.
2. From this D2 checkout, run `cargo +1.97.1 build --locked --offline --example core_provenance_stdin` (using `CARGO_TARGET_DIR` when sharing a local incremental target) and compute the SHA-256 hashes of that executable and the exact approved Python 3.11 interpreter.
3. Run `python3 scripts/qualify_sandboxed_synthetic_core.py --core-source <disposable-core-checkout> --python <python3.11-absolute-path> --python-sha256 <approved-local-sha256> --d2-reader <absolute-core_provenance_stdin-binary> --d2-reader-sha256 <approved-local-sha256>` on an authorized interactive Apple Silicon Mac.
4. The script refuses all other host OSes, source commits, executable hashes or report inputs. It uses macOS `/usr/bin/sandbox-exec` Seatbelt with **deny default**, process/sysctl/Mach lookup/read allowances, **no network allowance**, and writes restricted to a newly created 0700 private temporary folder. A **real listening 127.0.0.1 positive control** connects unconfined; an identical sandboxed connection must fail with `EPERM`. An unconfined sibling-file write succeeds while a sandboxed write to that sibling must fail.
5. With these controls passing, the harness runs Core's **real pinned Python `medscale.cli.fhir.main`** via `-I -S -B` and an explicit local source path for exactly two approved synthetic fixtures. It requires CLI exit 2, canonical report `status=not_validated`, the exact warning, Core's persisted report byte-equivalent to CLI output and pinned input hashes. It streams that bounded report via stdin to the standalone offline Rust D2 reader under the same OS policy, requiring the exact `FHIR_R4_NOT_VALIDATED` receipt. A tampered `valid` report must be refused by Rust. All temporary bytes are removed; no report payload is logged.
6. Rehash the approved executables after the run. No remote service is contacted; no production config, running desktop, user files or clinical records are used.

### Observed 2026-11-04 results

- `CORE_D2_SANDBOXED_FIXED_CASE_PASS known`: **PASS**
- `CORE_D2_SANDBOXED_FIXED_CASE_PASS unknown`: **PASS**
- `SYNTHETIC_CORE_SOURCE_TO_D2_SANDBOXED_QA_PASS_NOT_RELEASE`: **PASS**
- POSIX file-write refusal and local TCP loopback refusal: **PASS**; explicit unconfined positive controls verified.
- Companion Python contract, malformed JSON, false validation and binary-provenance tests: **10/10 PASS on real Mac**.
- D2 Rust library **25/25 PASS**, source/browser-free guards **7/7 PASS**, Rust formatter and Clippy (`-D warnings`) pass with the QA example added.

## Limits and blockers (non-negotiable)

This runner is **not called by the GUI**, provides **no file import**, **no encrypted clinical workspace**, and is **not an installed Wheel/venv/console launcher validation**. The Python worker is still run from a Git-pinned source checkout. The macOS sandbox profile permits broad **file reads and Mach lookup** and should be regarded as *synthetic-test containment*, **not** a verified PHI confidentiality policy or process-descendant, DNS/UDP/packet-level non-egress proof. `sandbox-exec` is a deprecated macOS testing facility; no Windows WFP denial or native non-WSL Linux egress confinement is implied. Local binary SHA pins are self-attestation, not trust in the supply chain. A positive synthetic Core receipt **never validates FHIR R4**; it documents `not_validated`.

True product integration needs a reviewed installed Core Wheel/venv/interpreter and native runtime provenance chain, OS-native sandbox/packet denials and process supervision across all three OSes, approved key handling, encrypted storage, access controls, audit/recovery, clinical FHIR schema/profile/terminology validation, accessibility/clinical-risk/security review, explicit owner release authorization and separate signer/notarization. Existing #662/#673/#676/#603/#574 and default-branch advisories remain NO-GO. No protected-main merge, public package, app store distribution, PHI ingestion or medical deployment.
