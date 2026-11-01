# MedOrigin D1 Network Confinement — EGM Design Draft

> **Status: DRAFT / NOT APPROVED. Goldfish review: NOT RUN. Release: NO-GO.**
> **2026-11-01.** Nonpublishing Windows D1 experimental preview, synthetic-only. This is a design artifact, not permission to execute privileged security changes, claim zero egress, merge into main, ship an installer, ingest PHI, or start a clinical workflow.

## 1. Problem, scope, and source of truth

The Windows D1 Tauri/React preview drives four static fictional SHA fixtures over React → Tauri IPC → Rust. On 2026-10-29, WebView2 child processes were actually observed with external IPv6 TCP/443 and TCP/80 endpoints, even though the app has only core Tauri permissions and an IPC-only content security policy. Issue [#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662) is OPEN. Source checks and sampled endpoint zeros do **not** establish that no packets or DNS requests escaped.

In [Draft #797](https://github.com/AbdulazizShehri/MedOrigin/pull/797), an unpublished, SHA-pinned D1 Windows app passed four synthetic UIAutomation journeys inside a native MXC ProcessContainer with deny/deny/host-loopback-deny policy. The primary-token admission gate now rejects four named capability classes, including the separately observed hashed networkLoopback SID. This is **token-based defense in depth**, not an authenticated MXC policy or full OS packet-level guarantee. [RED/GREEN evidence](../../experiments/desktop-d1-tauri/evidence/windows-d1-networkloopback-red-green-20261101.md).

The decision to make a credible offline, privacy-preserving developer preview requires **independent evidence that the entire owned runtime and relevant broker/service paths are denied network egress at the OS boundary**. It must not be inferred from documentation, CSP, WebView2 browser flags, all-green code tests, one snapshot, or absence of credentials.

## 2. Goals and explicit non-goals

**Goals:**
- Define a falsifiable, reproducible, free Windows test design for DNS, TCP, UDP, IPv4, IPv6 and the WebView2 process tree during cold start, use, shutdown, restart and recovery.
- Preserve functional Tauri IPC and exactly four synthetic fixtures while all disallowed application-scope network paths are denied.
- Record evidence with an exact app binary digest, source commit, Windows version, MXC backend/version, policy digest, observer identity, capture time window, per-flow ownership, and negative/positive controls.
- Fail closed when capture privileges, service/broker attribution, record continuity or cleanup cannot be proven. Exemptions need a separate security decision and documented ownership.
- Keep all review and evidence artifacts in this repository; delete disposable local test stages.

**Non-goals:** clinical decision support; PHI, real FHIR patient records, EHR writes, external telemetry; changing machine-wide firewall defaults; disabling or weakening OS/Edge/WebView2 security updates; making a distribution package; claiming non-Windows parity from Windows evidence; updating frozen research evidence; declaring release GO; rebranding the Google EGM plugin.

## 3. Threat model and trust boundaries

Actors and scope: (A) the local D1 Rust root process; (B) in-process React/Tauri IPC; (C) descendant WebView2 browser, renderer, utility and network processes; (D) native MXC launcher/ProcessContainer tokens and capabilities; (E) Windows DNS client, shared services, proxy/broker traffic and kernel WFP; (F) hostile or untrusted network endpoints; (G) synthetic-only fixture source.

Threats include: external TCP/UDP or DNS initiated outside the root PID; IPv4/IPv6 and loopback privilege differences; PID reuse or short-lived descendants; proxy/broker egress under another process identity; IPC impairment by sandboxing; policy not applied before WebView2 starts; launch fallback outside the sandbox; modified executable between digest verification and start; restart/upgrade changes; fail-open when ETW/WFP records are incomplete.

Trust rules:
1. A current-process AppContainer bit, four denied capability SIDs and a sampled socket inventory are **not** authenticated kernel confinement evidence.
2. CSP, browser flags and the absence of app HTTP plugins do not control all WebView2 background traffic.
3. Any unknown packet owner, broker involvement, missing observer privilege, dropped audit record, process ancestry discontinuity or unsupported Windows build is **NO-GO**, not an automatically acceptable exception.
4. Observe only synthetic metadata needed for qualification. Do not record real DNS names, packet payloads, patient data, personal app traffic or credentials. Host unrelated-process flows must be excluded by auditable identity, not by guessing a port.
5. Never create broad system-wide Edge/WebView2 firewall rules or disable Windows security updates.

## 4. Alternatives and decision boundary

| Candidate | Mechanism | Strength | Failure/risk | Status |
| --- | --- | --- | --- | --- |
| A: MXC ProcessContainer + verified application-scope Windows filtering | Keep the native fail-closed token gate; in an **authorized disposable Windows VM**, prove effective narrowly scoped OS/WFP policy for the app identity and relevant descendants, with independent flow audit. | Potential match for local developer app and fine-grained denial. | Requires OS privileges and careful identity/broker attribution; native policy may differ by Windows build; no verified implementation yet. | **Feasibility proposal, not approved** |
| B: Disposable Windows VM with network adapter disconnected / controlled deny boundary | Run a frozen, unsigned synthetic candidate entirely inside a disposable VM, with independent host-side observation and attack controls. | Stronger isolation boundary for testing and proof-of-concept. | VM availability/edition/privileges, GUI and IPC parity, and developer distribution story unresolved. Does not establish production launcher policy. | **Fallback experiment, not approved** |
| C: CSP / WebView2 disable-background-networking flags / TCP snapshot only | Restrict app content and sample sockets, without OS-enforced confinement. | Low operational cost. | **Already contradicted** by actual WebView2 external TCP observations in #662; cannot prove short-lived DNS or packets. | **Rejected as release evidence** |
| D: Machine-wide WebView2/Edge executable firewall deny | Block shared executables globally. | Broad denial under some conditions. | Breaks unrelated apps, updates and user security; violates project policy. | **Prohibited** |

**Design decision remains open:** A or B must be selected through documented security/owner review after a disposable-host feasibility study. This document intentionally does not choose an OS filter API, privileged service, installer, identity format or release authority without evidence. No implementation stage with unresolved security decisions may be marked implementation-ready.

## 5. Proposed proof architecture (not implemented)

- **Build boundary:** checkout exact approved source commit into a disposable stage; official Tauri build with no installer; record SHA-256 of the exact binary; prove no source drift after build.
- **Preflight boundary:** check supported Windows version and native MXC ProcessContainer; verify signed/trusted harness components if available; verify that the necessary independent OS network observer is installed and authorized in the disposable guest; reject on warnings, unknown WFP policy or insufficient privileges.
- **Confinement boundary:** run the **same exact binary** under pre-installed, app-scoped, deny-by-default policy before WebView2 creation. Keep the Rust AppContainer and networkLoopback token gate. No automatic uncontained launch fallback.
- **Observation boundary:** collect kernel-level blocked/allowed flow metadata and DNS events from a source separate from the application and its descendant processes, with monotonic window bounds. Cross-check a full process tree using PID + immutable start time + parent relationships and detect process reuse. Explicitly classify broker/service flows rather than silently excluding them.
- **Control boundary:** run a deliberate synthetic network-attempt probe inside an *equivalent* sandbox identity and under a contrasting permitted policy. A test that never tries to send a packet cannot prove packet denial. Require observed deny events and a working observer positive control. Never send PHI, credentials or DNS hostnames from real users.
- **Product boundary:** verify real 4/4 React/UIA → Tauri IPC → Rust SHA journeys. Preserve app startup, steady state, shutdown and cold restart; require cleanup of every owned descendant and ephemeral profile.
- **Evidence boundary:** attach a sanitized append-only manifest recording source SHA, binary SHA256, policy/test configuration, Windows/SDK versions, capture start/end times, relevant process identities, expected/observed blocked controls, missing event counts and exact exit codes. SHA or success-marker alone is insufficient.

## 5.5 Existing partial experiments vs the missing OS proof

The repository already contains related **experimental source**, which must
not be silently described as absent or as a completed security qualification:

- [`windows-mxc-capture-denials-experiment.mjs`](../../experiments/desktop-d1-tauri/tests/windows-mxc-capture-denials-experiment.mjs)
  requests an MXC `captureDenials` block-mode report while a synthetic native
  probe attempts localhost and TEST-NET connections. The paired
  [verdict](../../experiments/desktop-d1-tauri/tests/windows-mxc-capture-report-verdict.mjs)
  requires specific `WSA10013` output and a nonempty denial JSON, but itself
  labels the result **NOT_WFP_OR_PACKET_ATTESTED**. This probe is not
  the real Tauri/WebView2 process tree and does not cover independent
  DNS/IPv6/UDP and brokered-service packet attribution. Existing source
  cannot be promoted to a new full-product negative-flow receipt.
- [`windows-mxc-d1-cold-restart-qualification.mjs`](../../experiments/desktop-d1-tauri/tests/windows-mxc-d1-cold-restart-qualification.mjs)
  wraps two actual MXC GUI runs at an exact executable SHA and checks
  post-shutdown process identities using
  [`windows-mxc-d1-lifecycle-proof.mjs`](../../experiments/desktop-d1-tauri/tests/windows-mxc-d1-lifecycle-proof.mjs).
  This gives a bounded restart/cleanup *test mechanism*, not an OS packet
  capture, signed installer/upgrade audit, or release approval.
- [`windows-mxc-d1-real-uia-qualification.ps1`](../../experiments/desktop-d1-tauri/tests/windows-mxc-d1-real-uia-qualification.ps1)
  checks actual UIA and 12 process-identity-bracketed TCP/UDP endpoint
  samples; it cannot see attempts between samples or external
  Windows broker/service traffic.

**Remaining divergence from the target:** none of these existing mechanisms
supplies an independent and complete OS-enforced WebView2+broker DNS,
IPv4/IPv6 and TCP/UDP packet-level denial record tied to the exact signed
application and policy over the full lifecycle. An approved implementation
must **reuse or explicitly replace** these experimental sources after a
fresh review, rather than creating redundant tools or claiming their tests
are already sufficient.

### 2026-11-01 actual guarded two-cold-start lifecycle qualification

The [exact-source guarded D1 two-cold-start evidence](../../experiments/desktop-d1-tauri/evidence/windows-mxc-d1-two-guarded-cold-starts-20261101.md)
now includes **two genuine native Windows MXC restarts** of the
source-built D1 application with the **current** named networkLoopback
token guard, plus separate historical harness qualification.
The updated cold-restart harness reuses the strictly verified guarded
launcher instead of the older loose evidence parser. Current-source
exe SHA-256 is
`a36043a4028d9703e2cc29cc9e7e1b0a49476b74d5c02e0a17c8bb786aac8c6b`;
**8/8** WebView2 UIA synthetic fixture journeys passed across two
cold starts; after each actual MXC shutdown the exact root/WebView2
process PID+creation-time identities were not present. Current executable
also refused direct/plain or environment-spoofed Windows launches
**2/2 with exit 76**; current Rust unit tests **2/2 PASS**. Hosted
Windows source-only contracts **31/31 PASS**.

**Scope limit:** This is positive D1 GUI and bounded process-cleanup
evidence, **not** independent OS kernel WFP/packet/DNS/IPv4/IPv6
or WebView2 broker/service egress attestation; it also does not
address interrupted installer upgrade, crash-recovery, signed mandatory
startup or independently approved release. All #662 security NO-GO
gates remain unchanged.

### 2026-11-01 actual MXC capture compatibility finding

The [capture integrity and native failure report](../../experiments/desktop-d1-tauri/evidence/windows-mxc-capture-receipt-native-no-go-20261101.md)
records an additional real NO-GO on Windows build `10.0.26300`
using cached MXC SDK `1.0.1`: an exact-request `probe` returned
`base-container` and `nativeCaptureAvailable=true`, but the
subsequent `captureDenials.mode='block'` run failed before a receipt
could be generated:
`StartLearningModeTraceWithOptions: HRESULT 0x80004001 (E_NOTIMPL)`.
No native packet/denial capture exists from that attempted run.
The experiment deliberately refused an automatic UAC/guarded capture
fallback, did not turn on permissive Learning Mode and did not alter
machine-wide Windows firewall or auditing policy.

The receipt verifier now cross-checks SDK metadata against the
actionable JSON count, exit status and truncation indicators, requires
the per-run actionable+verbose pair, and prevents the workload from
writing its host-owned capture output. Offline Windows validation:
**30/30 source/negative cases PASS**. This is useful evidence-integrity
hardening, **not** a resolution of #662. The approved design must
account for a request probe succeeding while live capture fails.

### 2026-11-01 actual UDP socket-API ambiguity

The [native TCP/UDP matrix NO-GO report](../../experiments/desktop-d1-tauri/evidence/windows-mxc-udp-send-softaccept-no-go-20261101.md)
records a separate current Windows `26300.9818` MXC ProcessContainer
experiment using the **same synthetic Rust binary** for unrestricted
local-control and deny-by-default cases. IPv4/IPv6 TCP (loopback and
documentation destinations) returned `WSA10013`; all four UDP sends
returned `SENT23`. Both host-owned loopback listeners nevertheless
observed **zero contained datagrams** after the positive controls.
A UDP `send_to` success is **not proof of later network delivery**;
zero listener receipts are also **not proof of packet/WFP denial**,
especially for external/broker/DNS traffic. The test remains NO-GO.

The strict eight-protocol verifier now explicitly rejects this
ambiguous UDP soft-accept and treats source-only CI tests as validation
of error reporting, **not** native OS isolation proof. The required
independently observed UDP/WFP, IPv4/IPv6/DNS packet negative tests
remain unperformed; the separate current MXC native capture path still
fails `E_NOTIMPL`.

## 6. Test matrix and acceptance criteria

| Case | Expected result / required evidence |
| --- | --- |
| Uncontained direct startup and environment-variable spoofing | Exit 76 before WebView2; no network claim |
| Deny/deny/hostLoopback-deny MXC | App starts and passes four synthetic GUI/IPC SHA fixtures; no MXC warnings |
| Egress allow, ingress allow, both allow, hostLoopback allow | Existing exact-runtime native token gate refuses each; retain 5-policy matrix and separate app-level hostLoopback test |
| Real D1 descendants attempt IPv4 TCP, IPv6 TCP, UDP and DNS within an approved sandbox test | Independent OS observer records explicit **denial** with attributable application/descendant or classified broker identity; no successful disallowed flows |
| Deliberately permissive positive-control sandbox | Observer records permitted synthetic traffic, proving observer can see it |
| DNS and short-lived child process | Capture or trustworthy OS-enforcement evidence covers lifetime; any lost/unattributed event NO-GO |
| Cold start, UIA steady state, shutdown, crash/restart | Complete tree/flow evidence, no unbounded orphan; no user profile leakage |
| Observer unavailable, privilege denied, unsupported backend, lost audit record | Fail closed; never substitute sampled sockets |
| Installer / upgrading / signed launcher | **Out of this draft**; cannot be declared release-ready without separately accepted design and authority |

**Pass** requires *all* controls, an independently reviewable exact-source execution receipt, no unresolved new egress, and a separately recorded security approval. **No-GO** if just one necessary step lacks evidence. Source CI can enforce the document/review contract but cannot turn an OS experiment into a passed CI security gate.

## 7. Execution stages and file boundaries

**Stage 0 (this Draft PR):** write project-context packet, concept/design/index, explicit Goldfish review instructions and fail-closed documentation contract; no runtime/security behavior changes. Run offline text/index checks in CI. Status remains NO-GO.

**Stage 1 (approval and feasibility only):** obtain genuinely fresh Goldfish subagent reports (zoom-out, comprehension, design critique, zoom-out, readiness), human disposition of findings and signed architecture selection; confirm authorized disposable Windows test environment and privilege model. No execution on the user’s non-admin personal machine that requires modifying its global security controls.

**Stage 2 (future separate Draft PR):** implement one chosen, **scoped** capture and deny feasibility harness with exact-SHA pinned root + descendant attribution. Specify stable file paths after Stage 1 choice; do not silently change existing `experiments/desktop-d1-tauri/tests/windows-mxc-d1-real-app-qualification.mjs`, `windows-token-gate/src/lib.rs`, or the security source workflow without a reviewed test plan. Retain current fail-closed gate.

**Stage 3 (future separate Draft PR):** negative/positive OS evidence with synthetic traffic, DNS and broker attribution, all lifecycle trials, clean OS teardown, exact hashes and failure-case tests. Require independent reviewer sign-off and owner authorization before any security status changes.

**Stage 4 (separate release governance):** #603, #574 and #622 remain open until independently discharged. No protected-main merge/tag/installer/release/clinical permission from Stage 0–3 success alone.

## 8. Open questions and required reviewers

- Which Windows app-scoped WFP identity is stable across the entire WebView2 process tree, and can a verified native MXC ProcessContainer be bound to it before launch?
- What privilege model supplies actual, attributable blocked DNS/packet records without altering the developer host’s global firewall/auditing or collecting unrelated users’ traffic?
- How are Windows broker/service egress and DNS caching addressed when source PID is not an application descendant?
- How can a disposable VM reproduce the full GUI and network boundary while remaining free and retaining reviewer-verifiable evidence?
- What constitutes signing/bootstrap authorization and an immutable source-to-runtime policy assertion?
- Is the design feasible with no privileges on the current machine? If not, stop rather than simulate the missing evidence.

**Reviewer gate:** fresh-context EGM Goldfish subagents and an independently authorized human security reviewer have **not** reviewed this draft. Their absence is a blocker, not a green check.

## 9. EGM origin, fidelity, and references

This draft applies the design-document principles in Google's [elephant-goldfish-model](https://github.com/google/elephant-goldfish-model) repository, pinned source snapshot `403d8881d62022490637d740657b33f01e321ea8` (Apache-2.0). EGM is a spec/review plugin, **not** a medical model. No upstream code is vendored into MedOrigin and no Google endorsement is implied. The actual plugin and truly isolated reviewers have **not** been run in this session; review status is correctly **NOT RUN**.

Canonical evidence: [#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662), [#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603), [#574](https://github.com/AbdulazizShehri/MedOrigin/issues/574), [#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622); [real Red/Green and GUI evidence](../../experiments/desktop-d1-tauri/evidence/windows-d1-networkloopback-red-green-20261101.md); [native UIA source](../../experiments/desktop-d1-tauri/tests/windows-mxc-d1-real-app-qualification.mjs); [endpoint guard](../../experiments/desktop-d1-tauri/tests/windows-mxc-d1-network-endpoint-guard.ps1); [primary-token SID guard](../../experiments/desktop-d1-tauri/windows-token-gate/src/lib.rs).
