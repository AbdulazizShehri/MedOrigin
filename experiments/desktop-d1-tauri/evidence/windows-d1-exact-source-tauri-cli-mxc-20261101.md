# MedOrigin Desktop D1 — exact-source Windows Tauri CLI build and MXC UIA qualification

Date: 2026-11-01. **UNPUBLISHED, SYNTHETIC ONLY, NO PHI, NO RELEASE.**
This report records actual code/build/GUI test results; it is **not** a
packet-denial attestation, a release approval, or independent security review.

## Source identity and host constraints

- Clean, detached Git worktree at exact PR #797 commit
  `6a9ec8c9b9df2b48b8ccdd7f3d574f8ca1e7af99`, built from source.
  Before this report was added, a read-only `git diff --name-only` from that
  commit to `df05b56710d95fb2c884fcbd9655a5b0ff0701ee` across
  `experiments/desktop-d1-tauri/src`,
  `experiments/desktop-d1-tauri/src-tauri` and
  `experiments/desktop-d0-rust` returned **zero changed production source
  files**; subsequent PR #797 edits were tests and CI only.
- Authorized interactive Windows host, D: temporary source worktree and
  isolated Cargo target; no changes to existing working branches,
  protected main, machine-wide firewall or Node installation.
- Offline package sources: existing local npm/Cargo caches, exact committed
  `package-lock.json` and Rust `Cargo.lock`. These results do not imply
  independent review of dependency advisories or license posture.
- MXC used supported existing Node `v24.22.1`, SDK
  `@microsoft/mxc-sdk@1.0.1` installed offline in a temporary QA
  workspace, and `getPlatformSupport()` indicated `processcontainer`
  available.
- Real D1 GUI test used fictional built-in SHA-256 fixtures; no patient
  records, clinical payloads, real EHR writes, network endpoints or
  remote inference were supplied.

## Reproducible build/test outcomes

| Step | Outcome |
| --- | --- |
| `npm ci --offline --no-audit --no-fund` with local cache | PASS |
| `npm run build` (TypeScript + Vite 8.3.5) | PASS |
| `cargo fmt --all -- --check` | PASS |
| `cargo check --locked --offline` | PASS, exit 0 |
| `cargo build --locked --offline` | PASS, exit 0, **but not GUI qualified** |
| `npm run tauri build -- --debug --no-bundle` (Tauri CLI) | PASS, exit 0 |
| `cargo test --locked --offline` on Tauri crate | PASS, 2 tests / 0 failures |
| Real MXC ProcessContainer + source-built Tauri CLI executable | PASS, 4/4 synthetic UIA, exit 0 |
| GitHub Actions source contracts at `df05b567` | SUCCESS — [run #41297290834](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41297290834) |

**Important negative finding:** Direct `cargo build --locked --offline`
produced a 13,140,480-byte executable with SHA-256
`75e7c6853e2acc5eceac589d3f23bcdcc032675570e89c6eb82069ebbb2109ea`.
When launched in the same native MXC test harness, the D1 window was
located but UIAutomation failed to find the `Minimal Patient` button.
The native qualification returned **exit 1 / NO-GO**. This observation
alone does not prove the technical cause of the missing UI elements.
A direct `cargo build` exit 0 therefore MUST NOT be treated as
successful desktop UI qualification.

**Validated CLI artifact:** Rebuilt using the officially configured Tauri
CLI command `npm run tauri build -- --debug --no-bundle`, which ran
`beforeBuildCommand: npm run build` and reported successful native
application build. The resulting **unpublished** 13,214,720-byte
`medorigin-desktop-d1-preview.exe` has SHA-256:

`94c0aa3a5d647fb107c50b10d192e00ba646d55fd5b78f3ea0f944bab38eec61`

The first real MXC run of that artifact displayed and verified all
four UIAutomation fixtures, and enumerated zero owned TCP/UDP sockets
during the initial census, but failed the **harness** because the
PowerShell child observation timed out after 26 seconds before the
12-sample report marker appeared. It correctly returned **NO-GO**.
No product-side network policy was weakened.

The runner was repaired in `001d06dc8b0022e57a3d8be734d23b063b529a61`:
PowerShell UIA observation timeout **70 seconds**, total MXC
containment **90 seconds**, retaining the existing four-second
observation start delay and 15-second cleanup grace. A source-only
test `windows-mxc-d1-real-app-timeout-contract.test.mjs`, commit
`96b503d192a8ff0466ae48c6e2f234d3c35609ca`, requires the
PowerShell + startup window to fit strictly within MXC containment and
keeps both finite. This passed Windows local Node and exact-head hosted
Windows CI [run #41297290834](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41297290834)
after workflow change `df05b56710d95fb2c884fcbd9655a5b0ff0701ee`.

**Final real GUI rerun of the identical CLI-built SHA:**

- Four source-defined synthetic React → Tauri IPC → Rust SHA journeys:
  **4/4 PASS** (minimal, invalid-UTF8, oversize, exact limit).
- Real process-tree count: **8**, including **6 WebView2** descendants.
- Initial owned TCP, nonloopback TCP and UDP endpoint counts:
  **0 / 0 / 0**.
- **12** initial-and-after-identity-bracketed temporal socket samples:
  max owned TCP **0** and max owned UDP endpoints **0**.
- MXC runtime reported `warnings=[]`; bounded interactive process
  `timedOut=true` as expected; launcher **exit 0** with marker
  `D1_MXC_REAL_TAURI_UIA_4_OF_4_PASS_NETWORK_STILL_NO_GO`.
- After the run: exact-path D1 root processes **0**, and owned MXC
  temporary per-run directories **0**.

The built exe and locally staged dependencies were not published or
attached to a public release. Source/workflow changes stay in stacked
Draft PR #797.

## Security conclusion — still NO-GO

The successful run **does not prove** full network isolation: 12
socket snapshots are not WFP/kernel packet-denial evidence. Short-lived
TCP/UDP, DNS, IPv6, proxy/broker/OS-service traffic, and flows entirely
between snapshot censuses may escape observation; older uncontained
WebView2 processes had observed external traffic. The Windows host
session remained non-admin and could not access required WFP Security
audit records; the qualifying MXC setup was a controlled testing
environment, not an approved product-wide isolation mechanism.

Keep #662 open and all distribution, installer, clinical and PHI
activity blocked pending independent OS-enforced packet-level proof,
threat-model acceptance, software supply-chain #622 qualification,
release governance #574 and independent review #603. No tag,
protected-main merge, installer, public release or production EHR
integration was performed.
