# MedOrigin D1 network isolation — EGM v2 design and execution plan

> **DRAFT / NOT APPROVED. Goldfish review: NOT RUN. Implementation readiness: PARTIAL. Release: NO-GO.**
>
> 2026-11-01, synthetic-only / nonpublishing. No patient data, clinical use, installer,
> privileged experiment, broad OS firewall changes, security approval or release is
> authorized by this document. This is a proposed execution plan, not an EGM
> independent review receipt or proof of complete network isolation.

## 1. Problem and verified baseline

MedOrigin's React/Tauri/Rust D1 preview computes SHA-256 for four fictional
fixtures. WebView2 owned external TCP connections were observed on Windows in
[#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662), despite a
local Tauri IPC content-security policy and application-level network restrictions.
A successful GUI or a zero-socket snapshot does not demonstrate zero packets.

**Use these exact evidence lineages; do not combine them into a fictional run:**

| Evidence | Source / scope | Verified result | Does NOT prove |
| --- | --- | --- | --- |
| [#807 native receipt](../../experiments/desktop-d1-tauri/evidence/windows-d1-pr807-native-guarded-two-cold-starts-20261101.md) | Native executable from commit `03498d7856cf15e32e3a5f627a778000365a08cc`, executable SHA-256 `ed4a30167c4a8a6bb8b4af30ce86dee0607f3494ee6e5d84eeed13f7da2a9381` | Two guarded MXC GUI starts, 8/8 synthetic UIA journeys, clean identity-based shutdown, two direct-launch refusals (exit 76) | WFP, DNS, external UDP, OS brokers or any later code |
| [#807 final source CI](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41324982544) | Evidence-only HEAD `a07693d997c57ba48843adf2aee7bdd515acd326` | 34/34 source tests | A native build of this later docs commit or packet capture |
| [#808 source tests](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41325895634) | `a7cdbdf4d498f1a75017333a20f6ae1db4a476b1` | 25/25 source-only UIA stdout/stderr tests; closes a receipt-integrity gap | **Any native Tauri/MXC test at #808 HEAD** |
| [MXC capture native NO-GO](../../experiments/desktop-d1-tauri/evidence/windows-mxc-capture-receipt-native-no-go-20261101.md) | Windows 26300 / SDK 1.0.1 | `captureDenials` failed with `E_NOTIMPL` | Native packet/audit availability |
| [UDP matrix native NO-GO](../../experiments/desktop-d1-tauri/evidence/windows-mxc-udp-send-softaccept-no-go-20261101.md) | Synthetic Rust probe, separate from WebView2 product | TCP `WSA10013`; UDP `SENT23` with no local listener delivery | Either UDP packet-level denial or UDP external delivery |

**Source freeze for this planning delta:** `a7cdbdf4d498f1a75017333a20f6ae1db4a476b1` (#808).
Later source changes require a **new**, exact-SHA evidence record; never reuse #807's
native receipt to qualify #808 or this documentation branch. This plan is based on
[the original D1 EGM concept and design](D1_NETWORK_CONFINEMENT_EGM.md) and
[the existing cold-review packet](D1_EGM_COLD_REVIEW_PACKET.md).

## 2. Goal, non-goals and observer scope

**Goal:** make a defensible, falsifiable, zero-cost *experiment* demonstrating
whether a specifically built, contained D1 Windows preview and its attributable
WebView2/background paths have all unapproved network activity denied
**before** execution, while retaining Tauri IPC and four synthetic fixtures.

**Out of scope for this work:** automatic clinical clearance, PHI or real EHR
data, internet-based inference, signing/installer engineering, unrelated OS
traffic collection, retroactive claims about earlier builds, production-wide
configuration changes, disabling Edge/WebView2 security updates, Linux/macOS
parity or changing frozen research and package metadata.

**Proposed boundary diagram (not an implemented WFP architecture):**

```text
Exact source -> no-bundle EXE + SHA -> guarded launcher -> D1 root -> WebView2 tree
                                         |                   |
                                    OS policy?         Windows brokers?
                                         \                   /
                                   independent OS observer
                                         |
                             controls + lifecycle + attribution
                                         |
                              fail-closed evidence verdict
```

No observer can declare a pass unless it demonstrates visibility to its
own deliberately allowed and deliberately denied synthetic controls.
The OS boundary must be assessed independently from MXC's requested
configuration or a process's self-reported token flags. Windows DNS
caching, proxies, shared service workers and PID reuse must be classified.
Do not log real user destinations or packet contents.

## 3. Architectural alternatives and STOP decision

| Alternative | Value | Known failure | Decision |
| --- | --- | --- | --- |
| **A.** App-scoped OS policy plus independent WFP/ETW capture, on an authorized disposable Windows guest | Potentially matches end-user on-host isolation | Privileges, stable per-app identity, transient broker attribution, `E_NOTIMPL` backend, host variation | **UNDECIDED; gate HOLD-A** |
| **B.** Disposable offline/network-denied VM with host-side independent observer and synthetic allowed-control comparator | Clearer external test boundary | Hypervisor and Windows edition support, virtual NIC and GUI parity, not portable production app policy | **UNDECIDED; gate HOLD-B** |
| **C.** SDK configuration, token/capability checks, UIA and endpoint polling alone | Preserves current passing local fixtures | Missing short-lived, DNS, broker, IPv6/UDP and packet evidence | **REJECTED as security proof** |
| **D.** Machine-wide Edge/WebView2 executable firewall deny or disabled OS updates | Broad but coarse blocking | Impairs unrelated applications and security updates | **PROHIBITED** |

**Owner/security decision record required before implementation:** Choose
A or B **only after** a read-only feasibility inventory documents privileges,
supported SDK/capture backend, controlled guest disposal and independent
observer accuracy. Decision receipt must name the exact guest, mechanism,
scope, effective process identity, rollback, reviewer(s), unresolved broker
risk and reasons for rejecting the other option. Until then, do not implement
or run privileged WFP/ETW policies. Any engineer asked to choose an identity,
network interception API, privileged agent, installer mechanism or test
endpoint must **STOP**: these are unapproved architecture choices, not
open-ended implementation tasks.

## 4. Eight evidence gates (all are independent)

| Gate | Required verifiable artifact | STOP / fail-closed case |
| --- | --- | --- |
| **G0 Source and build identity** | Exact Git SHA, clean worktree, locked toolchain/deps, no-bundle native EXE digest, post-run digest | Diff, mutable binary path, changed digest, untracked executable source |
| **G1 Real app function** | 4/4 source-bound GUI/UIA → Tauri IPC → Rust fictional fixture hashes on exact executable | Marker-only success, failed hash, inconsistent UIA receipt or stderr |
| **G2 Runtime admission and lifecycle** | Native token gate, refused ordinary and env-spoofed direct launch, MXC warnings empty, PID+creation-time chain, two cold starts, complete cleanup | Launcher bypass, stale PID, unknown descendant, orphan process, incomplete stderr |
| **G3 Independent observer sensitivity** | On approved disposable guest: allowed-control packet is actually observed; denied-control event is visible independently with observer drop counters | Unavailable observer, `E_NOTIMPL`, insufficient privilege, no positive control, counter overflow |
| **G4 Ownership and broker attribution** | Full descendant and classified Windows service/broker crosswalk with bounded creation and termination window | Unowned event, PID reuse, missing ancestry, proxy/DNS attribution unknown |
| **G5 Protocol and policy completeness** | TCP/UDP, IPv4/IPv6, DNS and relevant loopback/proxy paths have positive and negative controls tied to exact policy and observer | UDP `SENT23` counted as denial, absence-of-packet used as sole result, unseen DNS/short-lived flow |
| **G6 Crash/restart/upgrade regression** | Source-bound cold start, steady UIA, abrupt crash, clean shutdown, restart and update/rollback *when designed* with unbroken observer window | Any gap, auto-uncontained fallback, orphan profile, branch/source mismatch |
| **G7 Independent review and release** | Real five-stage isolated Goldfish reports, owner resolution of findings, independent human security approval and separate #574/#603/#622 release decisions | Source CI treated as Goldfish, author self-approval, unreviewed policy, open dependency alerts |

Gate states must be **PASS / FAIL / NOT_RUN / BLOCKED** for each exact SHA,
and one NOT_RUN or BLOCKED release-critical gate keeps **RELEASE NO-GO**.
The earlier native #807 success is valid G1/G2 evidence for its **older**
source only; it is not a G3–G7 pass. #808 remains G1/G2 **NOT_RUN** until
real native replay is completed and recorded.

## 5. Implementation plan: permitted zero-decision work vs HOLD work

The upstream EGM
[implementation-readiness standard](https://github.com/google/elephant-goldfish-model/blob/403d8881d62022490637d740657b33f01e321ea8/resources/document_standards/implementation-readiness-standard.md)
requires a zero-decision plan: exact files, steps, tests and stable checkpoints.
**T0–T2 below are ready as source-only tasks. T3–T6 are intentionally
NOT implementation-ready until the decision and review are accepted.**

### T0 — Evidence reconciliation (source-only; READY)

**Files:** update this plan, `D1_NETWORK_CONFINEMENT_EGM.md`,
`D1_EGM_COLD_REVIEW_PACKET.md`, and `SITEMAP.md` only.
**Work:** preserve immutable source-to-binary receipt linkage from #807,
mark #808 native **NOT_RUN**, and keep EGM and release states **NOT RUN / NO-GO**.
**Tests:** run existing
`experiments/desktop-d1-tauri/tests/windows-d1-egm-design-contract.test.mjs`
and a separate v2 plan-contract test. Reject incorrect source SHAs,
claim drift, missing local documentation links, hidden approvals or lost
negative-capture evidence.
**Done when:** source-only tests pass on exact planning commit; no code or
dependency graph changes. This documentation PR remains Draft.

### T1 — Observer capability inventory (nonprivileged read-only; READY after T0)

**Files (new, proposed next Draft):**
`experiments/desktop-d1-tauri/tests/windows-d1-observer-capability-inventory.mjs`
and
`experiments/desktop-d1-tauri/tests/windows-d1-observer-capability-inventory.test.mjs`;
append-only evidence under
`experiments/desktop-d1-tauri/evidence/`.
**Work:** inspect **only documented capabilities** of Windows edition/build,
effective privileges, MXC SDK version and the supported request-specific
`probe` path; record read-only availability and known `captureDenials`
`E_NOTIMPL`. This is not a request to start WFP capture, enable audit,
run a new privileged service or probe external addresses.
**Result contract:** bounded JSON with `sourceSha`, `osBuild`,
`sdkVersion`, `observerAvailable`, `captureProbeOnly`, `reason`,
`privilegeRequired` and `status: "READ_ONLY_FEASIBILITY"`.
Treat unavailable, error and ambiguous as **BLOCKED**; do not synthesize
a compatible backend. Never log identifying host configuration or secrets.
**Negative tests:** missing/duplicate fields, forged capability,
reported privileges inconsistent with actual probe, stale SHA, unsupported
OS version, partial result and nonzero subprocess exit.
**Done when:** source tests pass and an attributable *read-only*
feasibility receipt is filed, clearly NOT G3 observer proof. No system settings changed.

### T2 — Offline evidence-schema/adversarial verdict (source-only; READY after T0)

**Files (new, separate next Draft):**
`experiments/desktop-d1-tauri/tests/windows-d1-egm-evidence-verdict.mjs`
and `experiments/desktop-d1-tauri/tests/windows-d1-egm-evidence-verdict.test.mjs`. Keep this free of native OS probes.
**Work:** implement a pure parser that **fails closed** for the following
fields in an eventual independent observer receipt: `sourceSha`,
`exeSha256`, `policySha256`, `osBuild`, `observerIdentity`,
`observationStart`, `observationEnd`, `eventCount`,
`droppedEvents`, `positiveControls`, `deniedControls`,
`unknownOwnershipCount`, `brokerClassification`, `protocolCoverage`,
`lifecycleCoverage`, `status`, and `scope`.
The parser may return **SOURCE_SCHEMA_VALID_ONLY** for complete synthetic
fixtures, never an OS enforcement or release PASS.
**Negative tests:** missing/mismatched SHA, duplicate process identity,
stale or reversed timestamps, zero positive-control detection, lost
events, `SENT23` misclassified as a block, missing IPv6/DNS, unknown broker,
observer error, replayed/duplicate sample, truncated receipt, nonzero exit,
or an asserted `RELEASE_GO`.
**Done when:** mutation cases reject fabricated evidence; no packet,
MXC, clinical or release claim.

### T3 — Independent Goldfish and owner architecture decision (HOLD)

**Files:** new append-only actual review reports under
`docs/designs/reviews/`; an approved, versioned ADR (path assigned only
after explicit decision). **Do not create fake review reports.**
**Start condition:** whole EGM plugin installed in an eligible harness
with verified fresh-context subagent spawning; authors and reviewers have
access to this complete design plus source read list. Follow
[the reviewer packet](D1_EGM_COLD_REVIEW_PACKET.md), the five stages:
zoom-out → comprehension → design critique → second zoom-out → readiness.
Owner resolves each finding and chooses A or B by signed decision.
**Not ready while:** no independent Goldfish, no owner decision, no
disposable-host privilege/scoping approval.

### T4 — Approved disposable-host packet/OS experiment (HOLD)

**Files:** new, namespaced native harness and WFP/OS observer files only
after T3 chooses a documented backend; no mutation to the primary host
firewall or existing production Tauri entrypoint.
**Required trial order:** observer positive control → explicit denied
control → same source-bound real GUI → IPv4/IPv6 TCP/UDP and DNS cases →
tracked descendant/broker inventory → cold restart → crash/cleanup →
observer completeness audit → independent replay.
**STOP:** backend `E_NOTIMPL`, unable to observe allowed controls, unknown
broker, dropped records, incomplete privileges, lack of guest rollback.
**Never** convert no local UDP delivery into proof of OS packet denial.

### T5 — Verified policy bound to mandatory launcher (HOLD)

Define how policy identity, immutable executable file handle, effective
token, descendants, brokers, errors, recovery and signing are bound
**only after** T4 produces accepted evidence and a new architecture ADR.
No uncontained fallback; installer/update changes need separate review.

### T6 — Cross-platform and release governance (HOLD)

Independently qualify macOS/Linux native APIs; Windows evidence does
not transfer. Resolve #603, #574 and #622 through their own review
track, including optional extras, supply chain, signatures and
versioning. No release or protected-main merge from this D1 packet.

## 6. Required controls and threat-focused cases for T4

When and only when T4 is authorized, test each case with a **synthetic**
workload, actual independent observer, exact source digest and policy:

- Blocked and deliberately allowed local TCP/UDP on `127.0.0.1` and `::1`,
  with host-owned listener packet counters **and** OS denial/allow records.
- Approved inert destinations for IPv4 and IPv6; no unapproved real endpoint
  contacted. External network controls use an approved isolated network
  fixture, not a public internet service.
- Explicit DNS queries against an isolated, controlled test name/server,
  cache-hit/cache-miss differential, service/broker attribution and resolver
  path. Avoid logging actual personal DNS destinations.
- Proxy and shared network services: classify every flow as in-scope,
  out-of-scope with reviewed reason, or unknown. Unknown is NO-GO.
- Process creation, nested WebView2 utilities, PID reuse and surprise child,
  before first IPC, during four fixtures, on shutdown, crash and restart.
- Negative observer failures: lose permission, missing capture file, dropped
  event, false positive control, unexpected SDK warnings and trace gaps.
- Keep an unrelated host-owned **synthetic** process distinct and show policy
  neither blocks nor silently includes unrelated user activity.

At every step, a deliberately observed allowed-control packet establishes
sensitivity; an explicit attributed blocked-control record establishes
visibility into denial. Both are necessary, neither alone sufficient.

## 7. Machine-readable evidence discipline

Suggested **future** sanitized envelope (example fields, not observed values):

```json
{
  "status": "NOT_RUN",
  "scope": "synthetic-disposable-windows-only",
  "sourceSha": null,
  "exeSha256": null,
  "policySha256": null,
  "osBuild": null,
  "observerIdentity": null,
  "observationStart": null,
  "observationEnd": null,
  "eventCount": null,
  "droppedEvents": null,
  "positiveControls": [],
  "deniedControls": [],
  "unknownOwnershipCount": null,
  "brokerClassification": "UNVERIFIED",
  "protocolCoverage": [],
  "lifecycleCoverage": [],
  "gates": {"G0":"NOT_RUN","G1":"NOT_RUN","G2":"NOT_RUN",
    "G3":"NOT_RUN","G4":"NOT_RUN","G5":"NOT_RUN",
    "G6":"NOT_RUN","G7":"NOT_RUN"}
}
```

A source-only validator must **never** populate observational fields
from hard-coded expectations or transform these placeholders into PASS.
Any later live evidence must include its capture tool and source versions,
bounded timing, drop counters, control destinations/ownership without PHI,
and independent review decisions. Keep raw privacy-sensitive captures
out of the repository; commit only sanitized reproducible metadata.

## 8. Fresh-context EGM Goldfish handoff and drift policy

Upstream source: Google
[Elephant-Goldfish Model](https://github.com/google/elephant-goldfish-model)
pinned to `403d8881d62022490637d740657b33f01e321ea8` (Apache-2.0).
It is a design/review plugin, not a medical model. Read the full plugin,
its persona files and standards; do not claim upstream Google approval.

**Goldfish review: NOT RUN.** This session does not expose native isolated
subagent tools. A parent-context critique or passing CI must not be relabelled
as a Goldfish review. If a harness lacks actual fresh subagents, stop
review dispatch with **BLOCKED / NOT RUN**, rather than fabricate personas.

The independent fresh reviewer must read this entire document, the
[original design](D1_NETWORK_CONFINEMENT_EGM.md),
[cold review packet](D1_EGM_COLD_REVIEW_PACKET.md), issues
[#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662),
[#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603),
[#574](https://github.com/AbdulazizShehri/MedOrigin/issues/574),
[#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622),
and code files referenced by sections 1 and 5. The reviewer must
challenge every inference from socket observation to packet denial,
every unexplained privilege assumption, every proposed broker exemption,
and whether **T0–T2** truly require zero architectural decisions.
Report exact paths/lines and blocking findings; owner decisions and
independent human sign-off are separate gates.

**Source drift triggers:** any new Tauri/Rust app source, MXC SDK version,
`windows-mxc-d1-guarded-preview-launch.mjs`,
`windows-mxc-d1-guarded-uia-observer.mjs`, token gate, capture backend,
observer policy, or security requirement invalidates the affected
qualification lineage. Produce a fresh drift report and re-run native
experiments on the resulting exact SHA; do not copy success markers.

## 9. Final decision

**This document improves the plan, not the security status.**
T0–T2 may proceed in nonpublishing draft branches. T3–T6 remain
**BLOCKED / NOT APPROVED** until reviewed decisions and real evidence
permit them. Maintain #662 **OPEN** and **RELEASE NO-GO**.
