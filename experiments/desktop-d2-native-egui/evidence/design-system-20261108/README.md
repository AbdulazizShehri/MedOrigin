# Design system + Settings & help — real-application capture (2026-11-08)

- Source: the commit that adds this file on `integration/medorigin-product-20261108`. Its parent merge is `b8f8e643` (Core `14e214a` + Desktop `bc48904`).
- Build: `cargo build --release` on Windows 11 (x64) with rustc 1.97.1.
- EXE SHA-256: `479cba658486eee0592987089aec0d531df82fa36d50ad17d259f7aca5110f08`. The release build is not reproducible across hosts, so this hash only identifies the local QA binary.
- Procedure: launch the EXE with no arguments, press **F1**, then capture the window (`settings-dark.png`). Click **Light** and capture again (`settings-light.png`).
- Local checks on this tree: `cargo fmt --check`, `cargo clippy --all-targets -D warnings` and `cargo test` (121 lib + 15 + 7 tests). D2 Python evidence unittests: 36 OK.
- Scope: fictional data only. This capture is not evidence of clinical, PHI or network-isolation readiness.
