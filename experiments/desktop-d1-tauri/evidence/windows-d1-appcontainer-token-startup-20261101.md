# MedOrigin D1 Windows direct-launch gate vs native MXC — 2026-11-01

**NONPUBLISHING / SYNTHETIC-ONLY / NO PHI / RELEASE NO-GO.**
This is a source-level and native Windows **experimental D1 preview** safeguard;
not a security approval for all products, a signed bootloader, a WFP packet
attestation or a guarantee that all AppContainer policies deny network.

## Problem and design choice

Earlier MXC UIA QA launched D1 inside ProcessContainer, but **the raw
D1 executable could also be launched directly on Windows** without the
optional guarded developer harness. As a result, simply qualifying a
separate launcher did not enforce application-local containment.

A read-only standalone native probe, with no external dependencies,
queried the **current process primary token** through
`OpenProcessToken(TOKEN_QUERY)` and
`GetTokenInformation(TokenIsAppContainer=29)`; it separately queried
`IsProcessInJob` to test whether ordinary Job membership was sufficient.
The exact same SHA-256-pinned compiled probe was run normally and inside
native MXC ProcessContainer (SDK 1.0.1, supported local Node v24.22.1):

| Observation | Direct Windows host | Inside MXC |
| --- | --- | --- |
| `TokenIsAppContainer` | 0 | 1 |
| `IsProcessInJob` | 1 | 1 |
| Native probe exit | 0 | 0 |
| MXC warnings | n/a | [] |

Standalone probe SHA-256:
`ddad96799ce4b84d4091562dd26f2ec6fdd18d7143407dd37c51790a50d36e49`.
No remote address, PHI, event-log read, privilege elevation,
firewall/audit alteration or WFP configuration was involved.

**Conclusion:** Testing Job membership alone would produce a false
security signal on this Windows host. AppContainer primary-token identity
is necessary for the tested AppContainer-backed MXC tier, but **not
sufficient** to identify MXC, its policy, or deny-by-default networking.
MXC may choose a distinct BaseContainer tier on other Windows hosts;
the experimental guard deliberately rejects a non-AppContainer token
there until a separately qualified attestation model exists.

## Applied nonpublishing D1 startup change

A new, tiny local crate
`experiments/desktop-d1-tauri/windows-token-gate` implements a
read-only Windows primary-token query behind a safe Rust function.
Only this auditable helper contains the narrow `unsafe` Win32 FFI;
the Tauri application maintains `unsafe_code = "forbid"`.
No new crates.io dependencies were introduced.

The Windows D1 `src-tauri/src/lib.rs::run()` calls
`require_windows_appcontainer_primary_token()` **before
`tauri::Builder::default()` and before creating WebView2**.
All errors and missing AppContainer flags cause
`D1_WINDOWS_APPCONTAINER_REQUIRED_NO_GO` and process exit **76**,
without environment-based overrides. Non-Windows build behavior is
unchanged by the Windows-gated call. `Cargo.lock` was updated offline
with exactly one local path-package entry and one dependency entry
(5 new lines).

This is a **new preview binary only**: older binaries still exist and
remain executable without this check. A malicious third party could
also launch the binary inside a different AppContainer with weaker
network permissions. The helper does not authenticate the launcher,
MXC version, exact policy, signed executable or kernel packet denial.

## Windows build and real host-vs-MXC trial

Source: detached Git worktree at `184fbfec4af62d013a4e0d2c3cbbfd06c9175e6e`
with Cargo.lock reconciled to committed
`0f0ead5b622842bdf9561c6de7cf6cf97ca28248`.
Subsequent commits through the source CI head
`69926640d955d604839993a766d71ab031499279`
add tests and CI only, without changing the D1 application
runtime or token helper.

- Isolated Windows Rust token crate:
  `cargo test --offline` **1 PASS, 0 FAIL**.
- Tauri `cargo check --offline` **exit 0** after the local lock update.
- `npm ci --offline` and official
  `npm run tauri build -- --debug --no-bundle`
  **exit 0** (including TypeScript + Vite).
- Resulting **unpublished** native debug executable: 13,215,744 bytes,
  SHA-256
  `6e07124750a96a7c28e97747db8b151c82af9180b619df20b7f8637fd6d3374c`.
- **Direct execution negative:** the exact SHA-matched new executable
  launched as an ordinary Windows user process using the .NET process
  API with a bounded 10-second wait. It exited **76**, and stderr
  contained `D1_WINDOWS_APPCONTAINER_REQUIRED_NO_GO` — no GUI
  startup was accepted.
- **Native MXC positive:** the exact same SHA-matched new executable
  launched inside genuine ProcessContainer, with ingress and egress
  default deny and host-loopback deny, using supported local Node
  v24.22.1 and MXC SDK 1.0.1 installed offline.
  The real Windows UIAutomation test reported:
  four fictional Rust SHA-256 journeys **4/4 PASS**,
  process tree **8**, real WebView2 descendants **6**,
  initial owned/nonloopback TCP and UDP endpoints **0**,
  **12** descendant-identity-bracketed TCP/UDP samples with observed
  maxima **0/0** and final source-bound UIA PASS marker.
  MXC returned `warnings=[]`, the intended bounded
  `timedOut=true`; runner output
  `D1_MXC_REAL_TAURI_UIA_4_OF_4_PASS_NETWORK_STILL_NO_GO`
  and **launcher exit 0**.
- Exact-source Windows hosted CI:
  [Actions run 41302447508](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41302447508)
  **SUCCESS**, including 3/3 startup source contracts and the token
  crate's 1/1 Rust unit test, plus existing network/UIA source gates.
  Hosted CI itself did **not** execute native MXC or GUI.

The latest product Rust `cargo test --locked --offline` (Tauri
crate, distinct from the token crate) is separately checked after
this report and should not be marked PASS without its actual result.
Temporary build and QA files are to be removed from Windows once
all execution evidence is collected.

## Remaining NO-GO gates

1. A **signed, unbypassable, application-scoped** launch and attestation
   design proving the *actual MXC backend and network policy*, not merely
   AppContainer primary-token membership. Determine acceptable behavior
   for MXC BaseContainer tier and prohibit all downgrade paths.
2. Independently review and test Windows/WFP packet-level DNS,
   TCP, UDP, IPv4/IPv6 external egress and WebView2/OS broker
   paths over startup, interaction, shutdown, restart and upgrade;
   sampled zero endpoints are not conclusive.
3. Third-party independent security review, dependency/license,
   governance and owner release approval (#662, #603, #622, #574).

**NO main merge, tag, installer, public release, PHI use, clinical
deployment or host-wide firewall/security policy change.** This
entire change remains in stacked Draft PR #797.
