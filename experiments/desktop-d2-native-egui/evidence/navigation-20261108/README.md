# Navigation rail, Home and Records — real-application capture (2026-11-08)

- Source: the commit that adds this file on `integration/medorigin-product-20261108`. Its parent is `e56893e6`.
- Build: `cargo build --release` on Windows 11 x64 with rustc 1.97.1. EXE SHA-256: `915f59e1d73bfc5ecf7e241dbe9401a7ecd37c26b31507aea4090d4abaa5ccd1`. This hash identifies the local QA binary only; the build is not reproducible.
- `home-dark.png`: a plain launch, which opens Home.
- `records-sample-dark.png`: after invoking "Open built-in two-patient fictional demo (NO PHI)" through Windows UI Automation. The app switched to Records automatically.
- `tests/windows-native-uia-smoke.ps1` on this EXE: `D2_NATIVE_UIA_4_OF_4_PASS`. The script opens Developer evidence first.
- `cargo fmt --check` and `clippy -D warnings` are clean. `cargo test`: 124 + 15 + 7 passed.
- Scope: fictional data only. This is not evidence of clinical, PHI or network-isolation readiness.
