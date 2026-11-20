# D2 Windows socket observer — actual local source verification (2026-11-02)

**Status: qualified observation harness only / OS isolation NOT qualified / release NO-GO.** Source on the private, nonpublishing stacked Draft #858; no patient records, network requests, firewall rules, elevation, software installers, or distribution.

## Implementation

- `tests/windows-network-socket-observation.ps1` accepts **one exact root PID**, caller-supplied SHA-256, executable basename, a bounded sample count and spacing. It checks the accessible Win32_Process root identity/creation time and on-disk binary SHA **before sampling**.
- Every sample refreshes CIM process parent/descendant membership and filters Windows TCP connection and UDP endpoint metadata to the visible process-tree IDs. Output is machine-readable JSON with **counts only**, rather than collecting destinations, DNS queries, URLs, packet contents, or patient data.
- Any observed non-loopback TCP or any UDP endpoint yields `NO_GO` with a nonzero status. If all samples are empty the script **still** yields `NO_GO` and exit 3, precisely because polling cannot prove DNS, UDP transmissions, ephemeral TCP, prelaunch events, descendant escapes or OS-enforced packet denial.
- Missing root, renamed executable, wrong hash, process lifetime change, inaccessible OS cmdlets or exceptions yield `NO_GO` with a nonzero status. No policy is installed, no host configuration is changed. Hashing the executable on disk is not independent proof of the loaded in-memory image.
- `tests/test_windows_network_socket_observation.py` creates an ephemeral local sleeping PowerShell child *only*, requiring no external network. It verifies missing PID rejection, wrong SHA refusal, and two actual bounded process-tree samples from an exact-hash process.

## Actual authorized Windows execution

Source baseline commit `98ba5faa717fb4399d8abc96b7ccab3dc18e59ec` (all changes before this evidence file); Windows PowerShell 5.1 and Python 3.14.7. Source fetched from the exact branch into an isolated temporary QA directory; neither shipped application nor protected main was changed.

- Existing evidence validator Python suite, after correcting its accidental literal backslash-n/comment bug at `a72f1c23174e819500f5ba3f826915c655e5889d`: **11/11 PASS**. The all-self-attested `PASS` packet CLI now returns exit **3**, not success.
- Native Windows PowerShell observer, impossible root PID `2147483647`: returned JSON `decision=NO_GO`, `reason=ROOT_MISSING_OR_AMBIGUOUS` and nonzero exit.
- Native Windows PowerShell observer, exact SHA-256 of a disposable PowerShell process, two real non-elevated samples: non-loopback TCP **0**, UDP endpoints **0**, `reason=NO_SOCKET_OBSERVED_BUT_PACKET_AND_DNS_EGRESS_UNVERIFIED`, caller-observed exit **3**. This does **not** describe any MedOrigin process or prove offline behavior.
- Python `test_windows_network_socket_observation.py`: **3/3 PASS** on the real Windows OS, including independent missing-root, wrong-hash and exact-hash but explicit `NO_GO` cases.

## Unclosed mandatory work

The tool does **not** run/measure the MedOrigin D2 binary in this qualification, enforce a process-scoped firewall, capture DNS or packet-level egress, account for sockets between samples, prove child process identity against PID recycling, perform the NET-06 external-negative-control injection, or independently verify sample integrity. **No NET gate is marked PASS from this observation.** #662 still blocks D1/WebView2; D2 has its own unqualified OS isolation. #673 Linux dependency, #676 spoken accessibility, #603 review, #622 dependency alerts and #574 release/owner authority remain open.

Next: run an isolated actual D2 executable with independently pinned binary SHA and process-scoped OS deny *before launch*; record DNS/TCP/UDP packet metadata with a deliberately blocked external attempt on a disposable test host, then seek independent review. Never equate empty socket polls with enforced denial.
