# D1 actual-Windows read-only attributed egress preflight — 2026-11-03

**Outcome:** 14/14 source-controlled mocked process/socket regressions **PASS** on authorized Windows PowerShell. This validates evidence attribution logic **only**. Runtime egress remains NO-GO, WebView2 #662 OPEN, no clinical/PHI/release authorization.

## Why this was needed

The older `windows-egress-snapshot.ps1` takes only a PID. It enumerates process descendants and TCP sockets, but an unrelated/reused PID can corrupt an observation's ownership claim. A PID alone cannot establish that the operator inspected the exact D1 image built from MedOrigin source. The original source correctly treats observed external TCP as NO-GO, but its absence in one snapshot is not network-isolation proof.

## Added source-controlled artifacts

- `experiments/desktop-d1-tauri/tests/windows-attributed-egress-preflight.ps1`: read-only, requires `-RootPid`, exact absolute `-ExpectedRootExecutable` named `medorigin-desktop-d1-preview.exe`, and independently pinned 64-hex `-ExpectedSha256`. Refuses a missing/wrong name/file/digest, wrong/unreadable root CIM executable image or creation timestamp, and changed root PID/birth/image during observation. Enumerates all rooted descendants through `Win32_Process` ancestry, including grandchildren; reads all TCP states and UDP endpoint count, then checks **each descendant PID + birth timestamp** again. Rehashes the executable file after socket observations to detect on-disk replacement during measurement. Never changes firewall, WebView2 global configuration, Edge updates or network policy. Always returns machine-readable `decision=NO_GO` and nonzero: observed external TCP exit 2, no TCP observed exit 3, evidence/identity failures exit 4. `release_authorized=false`, `os_packet_egress_denial_proven=false`, `dns_udp_egress_denial_proven=false`, `host_policy_modified=false` in all paths.
- `experiments/desktop-d1-tauri/tests/windows-attributed-egress-selftest.ps1`: fully executable, Windows PowerShell 5.1-compatible source-controlled regression. Creates **one inert local file fixture** with exact expected D1 basename and genuine SHA-256 (it is not a PE and is NEVER executed), plus synthetic CIM/socket mocks injected into each child PowerShell test process. Removes every scratch fixture afterward. No real sockets, DNS, network requests, policy modifications, child WebView2, or patient data.

## Actual Windows result

Two iterations of source-controlled QA ran on authorized Windows device `Abdulaziz`. First `12/12 PASS`, after descendant PID birth pin `13/13 PASS`, and after second on-disk hash check final **14/14 PASS** at commit `05fa4532a5e5359dadcb5b74dd440dc4c6fbc2b9`. Exact suite marker `D1_PINNED_ATTRIBUTION_14_OF_14_MOCK_PASS_NO_RELEASE`, runner exit 0.

Cases validated:
1. No visible sockets => **NO_GO** exit 3 (not PASS release).
2. External socket owned by unrelated PID => no false attribution, **NO_GO** exit 3.
3. Descendant `SynSent` TCP => **NO_GO** exit 2.
4. Grandchild `Established` TCP => **NO_GO** exit 2.
5. Wrong native image path for root => **NO_GO** exit 4.
6. Root PID birth changes between two CIM enumerations => **NO_GO** exit 4.
7. Descendant PID birth changes between enumerations => **NO_GO** exit 4.
8. Root PID absent => **NO_GO** exit 4.
9. Root creation timestamp missing => **NO_GO** exit 4.
10. CIM enumeration error => **NO_GO** exit 4.
11. TCP enumeration error => **NO_GO** exit 4.
12. UDP enumeration error => **NO_GO** exit 4.
13. Incorrect independently pinned image SHA => **NO_GO** exit 4.
14. Inert on-disk image mutated **during mock socket query** => second SHA mismatch, **NO_GO** exit 4.

No source-file mutation to Rust/React, package lock, or system config; source and tests retained in private Draft PR #661. Detailed usage instructions added to D1 README.

## Scope boundaries and next blocker

**The D1 native executable `D:\MedOrigin-D1-target\debug\medorigin-desktop-d1-preview.exe` was not present on the connected Windows test host when this experiment ran. Therefore NO new real D1/WebView2 network observation, real executable SHA, native app launch, packet-level capture, or OS-enforced egress-denial evidence is claimed for 2026-11-03.** Older observed WebView2 IPv6/TCP-443 established connections remain recorded in issue #662 and are **not remedied by this tool**.

A socket snapshot is inherently incomplete; even root/descendant birth + exact on-disk SHA does not attest process executable memory, kernel WFP confinement, DNS, short-lived UDP flows, external browser brokers or Windows services. Future acceptance requires an actual debug build on disposable authorized Windows host, source-to-binary pin, app-specific WFP-denial applied before process start, independently observed DNS/TCP/UDP negative controls across lifecycle, strict descendant accounting and independent security approval. Avoid shared global `msedgewebview2.exe` block rules and disabling global browser security updates.

**NO-GO:** no protected main merge, installer/tag/release, PHI, EHR integration or clinical-use assertion.
