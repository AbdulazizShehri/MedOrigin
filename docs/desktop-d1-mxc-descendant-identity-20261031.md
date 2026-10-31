# D1 MXC descendant process-identity continuity — 31 October 2026

**NONPUBLISHING / SYNTHETIC-ONLY / DRAFT #784.** This is a *source observer* hardening, not a new Tauri/WebView2 application, packet capture, network security proof, installer, package, or release. Exact review base is the immutable #783 head `6c1b325736e655e0603fb57fa089956714f060f9`. The previous #783 Git branch was unavailable as a live ref at PR creation, so a dedicated **unchanged** base ref `test/medorigin-d1-mxc-descendant-parent-20261031` was created at that exact SHA. No content of #783 or protected main was modified.

## Proven observation gap and fix

The real interactive D1-in-MXC UIAutomation observer already pinned the root process' PID, exact executable path, name and Windows CIM `CreationDate`. However its initial WebView2 child inventory and subsequent **12 × 250 ms** sampled process-tree traversals rebuilt descendants using only `ProcessId` and `ParentProcessId`. After a child exits, Windows may reuse its PID; without storing the previous child start identity, the sampler can wrongly attribute later owned TCP/UDP socket endpoints to the original tree, producing misleading observation evidence.

`windows-mxc-d1-descendant-continuity.ps1` now provides `Assert-MxcD1ProcessTreeContinuity`:
- Requires a nonempty real CIM process snapshot with exactly one record per PID. Calls the existing strict `Assert-MxcD1RootIdentity` and refuses changed root PID/name/path/start time.
- Traverses at most 16 parent levels from the original root and refuses unvisited connected children beyond that depth.
- For each *attributed* descendant, requires a valid CIM `CreationDate`, nonempty process name, consistent parent PID, and creation time no earlier than the currently observed parent.
- Retains **every previously observed descendant identity, including exited processes**, for the whole observation window. Same-PID changes in start time, parent, name or available executable path fail closed. A missing child is not automatically a failure, but its PID cannot later reappear with new creation time.
- Allows low-integrity WebView2 children to withhold `ExecutablePath` in one sample without discarding the previously known identity. If both the earlier and new paths are known, a mismatch fails. The root path is always mandatory and immutable.
- Returns a rooted identity-qualified PID set used by the real pre-window TCP/UDP inventory and **all** 12 temporal samples. Failed identity checks stop the observer before a positive no-egress sentinel. No firewall or network permissions are changed.

This is stricter attribution of **observed process snapshots only**. It cannot see a process that starts and ends entirely between samples, kernel broker traffic, short-lived UDP/DNS connections, network attempts denied before socket creation, or full packet contents. A zero TCP endpoint snapshot is not proof of zero egress. App/OS MXC WFP isolation cannot be inferred from these source checks.

## Reproducible test-first evidence

1. **RED:** [hosted Windows source-only CI #41228364573](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41228364573) at test-only head `11c9fd7ccfee0c5d2a8980cbacc2920d221259b4` completed FAILURE in the dedicated new regression with `RED: descendant continuity helper absent`. This was a deliberately missing observer contract, not an observed live WebView2 escape.
2. The actual 2026-10-31 fixed source at `732a31180cd3dd443aacc8cc496a172d841f0d9e` passed [source-only Windows CI #41228684048](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41228684048) (Pull Request) and [#41228679204](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41228679204) (push). The former baseline root unit test was updated to verify its root identity contract is **delegated through** the new helper in both call sites, rather than incorrectly looking for only direct calls. The new adversarial regression runs **13 checks**, covering changed/reused child PID, changed child name/path/parent creation order, missing timestamps, duplicate PIDs, changed root, disappearance and reappearance. Prior root identity regression runs **9 checks**. Existing Node lifecycle tests and PowerShell parser/AST also run in hosted CI.
3. On another **authorized native Windows host**, a task-only sparse checkout pinned to the exact `732a311...` source was run with ordinary unprivileged **Windows PowerShell 5.1** and real CIM date types. Output:
   ```text
   D1_MXC_ROOT_PID_REUSE_FAIL_CLOSED_SYNTHETIC_PASS checks=9
   D1_MXC_DESCENDANT_PID_REUSE_FAIL_CLOSED_PASS checks=13
   D1_DESCENDANT_IDENTITY_LOCAL_WINDOWS_SOURCE_PASS
   ```
   The tests did not launch the Tauri application or change network settings. Git contents were not modified.

**Final exact-head qualification:** After this documentation commit, the final immutable SHA and fresh source-only Windows CI conclusion must be recorded in PR #784; do not transfer earlier success to a later commit without verification.

## Remaining NO-GO

**Issue #662 remains OPEN**: real WebView2 child traffic was previously observed externally; environment-process flags do not eliminate it. The MXC V1 `captureDenials` route produced native `E_NOTIMPL (0x80004001)` on the authorized Windows build, so these tests provide **no packet-level or OS-enforced DNS/UDP/IPv4/IPv6 WebView2 egress attestation**. Earlier D1 UIA 4/4 and native eight-socket MXC protocol-denial tests are separate bounded evidence, not rerun by this PR. A future supported WFP capture mechanism or independent OS-enforced scoped audit plus real cold-start/interactive/shutdown/restart evidence is required. Do not weaken Windows firewall globally, allow shared-WebView2 runtime network accidentally, or claim an equivalent approval.

Also open: #574 owner/version/ADR authority, #603 genuinely independent security review, #622 frozen research optional extras, #673 Linux D2 AccessKit/zbus5 transitive maintenance, #676 VoiceOver spoken accessibility. **No PHI, EHR writing, clinical use, release artifact, package upload, protected-main merge, tag, signed installer or publication.**
