# MedOrigin D1 — primary-token network-capability denial (Windows, 2026-11-01)

**NONPUBLISHING, synthetic-only, no PHI. RELEASE NO-GO.** This evidence
applies to the experimental, unpublished D1 preview and the tested
Windows native MXC ProcessContainer backend. It does not qualify clinical
use, a package release, an installer, independently audited WFP packet
denial, brokered traffic, DNS or a signed/immutable launcher.

## Why the original gate was insufficient

The earlier D1 Rust startup gate required
`GetTokenInformation(TokenIsAppContainer=29)` on the current process's
**primary** token before starting Tauri/WebView2. But an AppContainer
can legitimately have network capabilities; merely being in one is
not a trustworthy assertion of the requested `deny/deny` policy.
Microsoft's published well-known network capability SIDs are:

- `S-1-15-3-1` — `internetClient`
- `S-1-15-3-2` — `internetClientServer`
- `S-1-15-3-3` — `privateNetworkClientServer`

The [Microsoft MXC ProcessContainer networking guidance](https://github.com/microsoft/mxc/blob/main/docs/backends/process-container/networking.md)
maps an ordinary `network.egress.default=deny` and
`network.ingress.default=deny` policy to **no internet/private-network
capabilities** (outside specialized tracing/proxy arrangements).

## Native read-only discovery — DO NOT require all capabilities absent

Source files:
`tests/windows-mxc-d1-self-capabilities-probe.rs` and
`tests/windows-mxc-d1-self-capabilities-differential.mjs`.
The standalone Rust native probe queries `TokenIsAppContainer=29`
and `TokenCapabilities=30` (a `TOKEN_GROUPS` structure) from the
same current-process primary token; Win32 `EqualSid` compares each
capability against the three well-known network capability SIDs.
Neither the host nor the MXC process performs any network operation.

The SHA-256 pinned probe, compiled with `rustc --edition 2024
-Dwarnings` on the authorized Windows machine, was
`2fe1def7d7e7092c90bd3cae913d9c7b421aa18579773b5d07b7582681519e0a`.

| Observation | Normal Windows host | Same binary in native MXC ProcessContainer |
| --- | ---: | ---: |
| `TokenIsAppContainer` | 0 | 1 |
| Token capability count | 0 | **1** |
| Known network capability mask | 0 | **0** |
| Probe exit | 0 | 0 |

The MXC native differential exited **0** and reported zero warnings.
The MXC token's single capability was **not one of the three known
network capability SIDs**. Thus, an assumption that all capability
groups must be absent would incorrectly reject this tested MXC
environment. The exact identity of this unrelated capability has
not been independently reviewed, and was not inferred from a count.

## Code change

`windows-token-gate/src/lib.rs`, still the only narrowly scoped
Windows FFI helper, now requires all of:

1. Current process **primary** token can be opened with `TOKEN_QUERY`.
2. `TokenIsAppContainer=29` returns an affirmative DWORD.
3. `TokenCapabilities=30` can be read using a bounded, aligned
   `TOKEN_GROUPS` allocation, sane count and buffer bounds. Errors,
   missing SIDs and malformed responses are **NO-GO**.
4. For each capability SID, native `EqualSid` comparisons against
   the well-known three network SIDs all return **false**. Any match
   returns `primary_token_has_network_capability`.
5. No environment variable or command-line parameter can bypass these
   checks. The app invokes this gate before `tauri::Builder::default()`
   / WebView2 creation and exits **76** on failure.

Other capabilities can remain; the test does not claim those are
independently security-reviewed. This is necessary defense in depth,
not authenticated MXC provenance or a cryptographic assertion of
the *exact* operating-system WFP policy. AppContainer services/brokers
may have their own networking identities.

## Source, Windows build and real differential

- Stack: Draft [PR #797](https://github.com/AbdulazizShehri/MedOrigin/pull/797).
  Exact runtime source is unchanged after the formatted
  `windows-token-gate/src/lib.rs` blob
  `f67f4a19c5c47d905be357bdf663183a4efa7b93`, committed in
  `4cc9d6da8147a6a34f44f8cf522215e504c01d6d`.
- Clean detached Windows source stage from branch commit
  `4358e700ff7b1e5fc6359bbedcafe89a56274e28`, with the
  identical formatted runtime helper verified against its
  **committed Git blob SHA** before compiling.
- `windows-d1-appcontainer-startup-source.test.mjs`: **4/4 PASS**
  locally, including static source assertions for no network
  capability grants and no environment/Job-based bypass.
- Isolated `windows-token-gate` crate `cargo test --offline`:
  **2/2 PASS**, including all seven nonzero bitmasks formed from
  the three network capability SIDs.
- `cargo fmt --check` passed after `rustfmt` normalization.
- `npm ci --offline`, TypeScript/Vite `npm run build`, and
  official `npm run tauri build -- --debug --no-bundle`
  all **PASS**; no external build dependency or app installer
  was published.
- **New native unsigned, unpublished executable**:
  13,235,712 bytes, SHA-256
  `d8c60e9e42db1d3eb997df591998c8cc2d817c4fdcaf644b9644f28752081c79`.
- The same exact executable failed closed when started as an ordinary
  Windows process in **three distinct direct-launch trials**:
  plain, environment `APP_CONTAINER=1 / MXC_CONTAINER=1` spoof,
  and environment `MEDORIGIN_SKIP_GATE=1 / MXC_NETWORK_DENY=1`
  spoof. Each exit code **76**, each logged
  `D1_WINDOWS_APPCONTAINER_REQUIRED_NO_GO`.
- **Same new exact SHA** under actual MXC ProcessContainer using
  supported local Node v24.22.1, MXC SDK 1.0.1 installed
  from an offline npm cache, ingress and egress default deny,
  host-loopback deny: **4/4 synthetic UIAutomation
  → React → Tauri IPC → Rust SHA fixture journeys PASS**.
  Actual process tree **8**, **6 WebView2** descendants;
  initial owned/nonloopback TCP/UDP **0**; **12**
  descendant-identity-bracketed temporal socket samples with
  observed max owned TCP **0**, UDP **0**.
  MXC warnings `[]`, intended bounded timeout, launcher **exit 0**,
  final marker `D1_MXC_REAL_TAURI_UIA_4_OF_4_PASS_NETWORK_STILL_NO_GO`.
- Product Tauri crate `cargo test --locked --offline`:
  **2/2 PASS**, 0 failed, final exit 0.
- [Exact-runtime-head Windows hosted CI
  #41304169181](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41304169181)
  **SUCCESS**, all job steps inspected, source test **4/4**,
  local Rust helper unit tests **2/2**. This hosted CI
  is source-only and **does not run native MXC or capture packets**.

## Limitations and explicit release blockers

This provides **actual native process-primary-token restrictions**
on the newly built D1 preview. The Microsoft well-known capability
SID set is not an exhaustive list of every possible broker or network
access route. Absence of the three SIDs does **not** establish complete
kernel packet/DNS/IPv4/IPv6 egress denial; no new packet/WFP
audit record was obtained. Other AppContainers, different MXC
backends, application lifecycle transitions and historical
binaries still require qualification. The helper does not bind
an immutable file-handle or signed binary to an authenticated
MXC policy. The previous real WebView2 external-TCP observations
remain relevant and must not be discounted by sampled zero
endpoint counts.

Keep **#662 OPEN, release NO-GO**, and require independent WFP
negative packet and DNS evidence, broker/service lifecycle checks,
artifact trust and signed mandatory bootstrap, dependency and
independent security review (#622, #603), and owner release
authorization (#574). No source merge to protected main,
installer, public tag, release, PHI, clinical data, paid service or
host-wide firewall/audit-policy change occurred. The Windows
worktree, compiled target and QA scratch are to be deleted after
all evidence is saved in the repository.
