# Native D2 actual Windows socket observation — 2026-11-02

**Status: OBSERVER ENGINEERING PASS; OFFLINE / NETWORK ISOLATION / RELEASE remain NO-GO.**

## Exact-source controlled setup

- Authorized Windows host `Abdulaziz`; disposable, **nonpublishing** detached worktree of `AbdulazizShehri/MedOrigin` at `f213b837261f5f5543b95a3333c4482ebc2a4a91` (Draft #858). Source-locked `experiments/desktop-d2-native-egui/Cargo.lock`.
- Actual browser-free D2 native GUI compiled **locally using `cargo build --offline --locked`**, Rust 1.97.1. Build completed successfully in 4m18s, with no dependency downloads required.
- Test-only executable SHA-256: **`784BFBD6BDC73B31C8E6CF69B7D2F3BB63F3DC470F9BE0F8BE650534C8B2B0D7`**. This hash applies only to this local debug executable; it is **not** a signed release artifact.
- `cargo test --offline --locked --all-targets`: 6 D2 app tests and 6 browser/network source-boundary tests **PASS** (12/12); bin/example targets contained no extra tests.
- No PHI, user file, EHR interface, model, external endpoint, installer, publication, or firewall policy was enabled.

## Actual D2 launch and source-controlled observer

The Windows `windows-network-socket-observation.ps1` first checked the running process identity, expected executable basename and exact SHA-256, then polled the visible parent/descendant Win32 process tree, non-loopback TCP connections and owned UDP endpoints. Test launched a genuine native D2 GUI; **the observed D2 root PID was 26912**, and the observer counted **two** visible tree processes.

For three sequential samples (UTC 19:50:32.397, 19:50:34.770, 19:50:36.896), each yielded **0 nonloopback TCP connections** and **0 UDP endpoints**, with two processes visible. The observer intentionally returned `decision=NO_GO`, `reason=NO_SOCKET_OBSERVED_BUT_PACKET_AND_DNS_EGRESS_UNVERIFIED`, and the caller recorded **observer exit 3**. The owned D2 process was explicitly stopped after observation. No remote packet capture was performed.

The additional repository `windows-native-d2-socket-smoke.ps1` (subsequent Draft #858 commit `d5ef41282bb216ebeb47ba2b1a219ecccaa1973f`) was then exercised against the **same exact compiled executable**:
- **Incorrect externally supplied all-zero SHA:** correctly refused prior to starting the app (`D2_SMOKE_NO_GO_PINNED_SHA_MISMATCH`).
- **Correct externally supplied SHA:** actual D2 GUI started and three process-tree samples ran (UTC 19:52:25.806, 19:52:27.579, 19:52:29.344). Each again observed **two visible processes, zero nonloopback TCP connections and zero UDP endpoints**.
- Structured output still reported `decision=NO_GO`, `os_packet_enforcement_proven=false`, `dns_and_udp_egress_covered=false`, `release_authorized=false`. The runner logged `D2_SMOKE_OWNED_PROCESS_CLEANUP_DONE`.

## Limits / release blockers

**This is neither OS-enforced network denial nor zero-egress proof.** Process-scoped endpoint polling may miss brief connections, DNS requests, UDP send events, attempts blocked before a socket is established, proxy traffic, child processes that exit between polls, and OS services. The smoke script does not yet drive all 12 fictional UI interactions during capture, test application-scoped firewall policy before launch, provide a bounded DNS/TCP/UDP negative control, or obtain independent review.

Keep #662 (D1/WebView2) open independently. Keep D2 offline decision **NO-GO** until all NET-01..NET-09 criteria are measured with real OS-level enforcement and negative controls, and keep #673, #676, #603, #622, #574 as separate unresolved release blockers. This packet does not change root science research or protected main.

The disposable local worktree and compiled artifacts are engineering scratch only. Source and evidence are retained in GitHub, not released.
