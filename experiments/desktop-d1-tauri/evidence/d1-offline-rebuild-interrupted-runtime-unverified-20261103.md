# D1 offline native rebuild and attributed WebView2 lifecycle — 2026-11-03

**Decision: STILL NO-GO.** This document records only directly observed outputs, including an execution access interruption. It does NOT assert a finished D1 Rust build, executed native runtime, zero network egress, clinical suitability, or release approval.

## Local rebuild facts observed on authorized Windows device

The MedOrigin D1 **private GitHub branch** was checked out as an isolated detached disposable worktree at `D:\MedOrigin-D1-RealEgress-20261103`, exact source commit `2063fadfdef7b126b88cd4c1a606793f61ea977a`, leaving the original clone `D:\MedOrigin-D1-MXC-20261030` clean at preflight. Preliminary host state: 128.7 GB free on D:, Node v24.19.0, Rust/Cargo 1.97.1, original D1 debug `D:\MedOrigin-D1-target\debug\medorigin-desktop-d1-preview.exe` **absent**, D1 `node_modules` **absent**.

Inside `experiments/desktop-d1-tauri`, **`npm ci --offline --no-audit --no-fund` PASS** with 26 packages installed from npm cache, then **`npm run build` PASS**: TypeScript and Vite 8.3.5 compiled 18 modules and wrote `dist/index.html`, CSS, JavaScript. This proves only frontend toolchain success on this exact checkout. No network downloads were required during either command.

An isolated native Rust build was started with `CARGO_NET_OFFLINE=true`, `CARGO_BUILD_JOBS=3`, `CARGO_INCREMENTAL=0`, target directory `D:\MedOrigin-D1-RealEgress-CargoTarget-20261103`, commands `cargo test --offline --locked --lib` followed by `cargo build --offline --locked`. Tool output confirmed translation of many crates including `wry 0.57.1`, `webview2-com-sys 0.39.1`, `tauri-runtime 2.12.2` and `tauri 2.12.5` but **NO completed Rust test result, final build exit status, native executable path/hash, runtime process PID, or WebView2 network observation was available when remote device access paused**. Do not infer compilation completion from partial `Compiling` lines.

## New source-controlled test harness

`experiments/desktop-d1-tauri/tests/windows-attributed-egress-lifecycle.ps1` (GitHub commit `188ef05fe3b108fd99631e63941b5b3b0e348cdc`) defines a read-only **future runnable** five-sample native Windows D1 test. It requires exact executable basename `medorigin-desktop-d1-preview.exe` and caller-pinned SHA-256. It launches that exact test image, gathers multiple child-process and all-state TCP/UDP endpoint count observations through the previously **14/14 mocked-test-verified** `windows-attributed-egress-preflight.ps1`, produces JSON with only counts and nonrelease risk reasons (not network destinations or payloads), and attempts to stop its own root process. Even zero observed external TCP **still produces `NO_GO` with nonzero exit** because a socket snapshot does not prove DNS/UDP packet enforcement, broker descendants, cold-start updates, or Windows WFP isolation.

Important **verification limit**: the lifecycle harness was source-authored and copied to the disposable Windows worktree, but **was not executed against a live D1 binary** during this turn. Do not claim it passed or detected real outbound traffic. Its documentation in `experiments/desktop-d1-tauri/README.md` was added (commit `85f4b3b319b25e7702d866c23e0832db932986c3`). Microsoft WebView2 `WebResourceRequested` intercepts website resource requests and is not a substitute for OS-level packet/process confinement (https://learn.microsoft.com/en-us/microsoft-edge/webview2/how-to/webresourcerequested).

## Remote access interruption and cleanup limitation

Desktop Commander reported: **monthly device usage reached; further tool calls paused**. Therefore the remote Cargo process's final status and temporary worktree/target cleanup **are NOT independently verified**; no post-interruption tool call should be attempted to bypass the limit. Disposable paths are `D:\MedOrigin-D1-RealEgress-20261103`, `D:\MedOrigin-D1-RealEgress-CargoTarget-20261103`, `D:\MedOrigin-D1-Preflight-20261103.ps1`, and `D:\MedOrigin-D1-Rebuild-20261103.ps1`, `D:\MedOrigin-D1-Rust-Build-20261103.ps1`. They contain test build files only. The source repository is committed in GitHub; scratch cleanup has not yet been confirmed.

## Hard release blockers unchanged

Issue #662 (observed external IPv6 TCP/443 from WebView2), dependency risk #673, macOS spoken accessibility #676, optional dependency governance #622, independent review #603 and release authorization #574 remain open. D1 is still strictly synthetic-only, local test, no PHI, and no real EHR. No main merge, signing, installer, release, public publication or production usage may be implied. A genuinely separate controlled and authorized Windows OS/WFP packet-denial setup is required to qualify offline behavior; simply disabling WebView2 background flags or intercepting webpage resource requests does not establish runtime-wide zero egress.
