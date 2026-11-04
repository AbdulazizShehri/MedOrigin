# D2 native one-shot Core stdin deadline — synthetic-only

**2026-11-04; private Draft PR, no release or PHI.**

## Fixed real startup defect

Prior D2 `--synthetic-core-stdin` accepted only two exact, source-pinned, fictional Core reports, but performed a bounded **byte count** without a bounded **wait**. A parent that never closed stdin, or sent a complete canonical synthetic report without EOF, could hang D2 indefinitely before native GUI startup.

This change preserves the exact 2048-byte and two-source report allowlist, the ordinary no-stdin path and the no-subprocess/no-network/no-file-import architecture. The opt-in mode alone now reads stdin in one named Rust worker thread and waits for a result through a capacity-1 channel with a **5-second hard receive deadline**. Failure to receive an EOF, even after all correct bytes have arrived, returns `io::ErrorKind::TimedOut` with `synthetic_core_stdin_deadline_refused` before constructing any GUI. Read errors and truncated, malformed, extra-byte, forged status or wrong startup args still fail closed. The worker is not a server or background process; on startup failure the desktop process exits, taking its blocked read thread with it. This is a QA transport time bound, not cancellation-safe clinical IPC or secure memory erasure.

## Evidence

On an authorized Apple Silicon Mac, compiled the exact native D2 branch with pinned Rust 1.97.1 `cargo test --locked --offline --all-targets`, `cargo clippy --locked --offline --all-targets -- -D warnings`, `cargo fmt --all` pass. Rust binary SHA `f19c7ade88d1f473a823116daf522fdfcc574fbdced1f87f275958f71cf970e1`. The real native binary was launched twice by source-controlled `scripts/qualify_native_stdin_deadline.py` using a real OS pipe *kept open throughout* (1. no bytes, 2. **the full exact canonical known Core report without EOF**) and both terminated nonzero without ever displaying a GUI, instead of hanging:

```
NATIVE_SYNTHETIC_STDIN_DEADLINE_PASS idle exit=1
NATIVE_SYNTHETIC_STDIN_DEADLINE_PASS valid_bytes_without_eof exit=1
D2_NATIVE_SYNTHETIC_STDIN_DEADLINE_IDLE_AND_MISSING_EOF_PASS_NOT_RELEASE
```

New Rust tests simulate stalled stream, full bytes without EOF, denied stdin read and prior exact-source positive/invalid/normal launch; Python negative tests exercise wrong executable hash, missing and symlinked binary, exact source report SHA gate and the real probe contract. Hosted Windows/Ubuntu CI recompile D2, run real Rust unit tests and source-only Python tests; they are **not** claimed to have exercised OS-pipe timing unless separately executed on Windows/Linux. No new crate or Cargo.lock changes.

## Limits

This only protects the **synthetic input mode** from indefinitely stalled stdin. It does NOT launch/supervise real Python Core; authenticate the pipe sender or report freshness; protect patient data in memory, storage, network or OS descendants; provide bounded waiting for a clinical worker; prove full FHIR R4 validation; fix accessibility or transitive dependency notices; or authorize a release. All open release and medical/security gates remain NO-GO. No patient import, signing, publication or protected-main merge.
