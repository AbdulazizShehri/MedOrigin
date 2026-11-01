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

**Frozen D1 runtime code baseline:** `a7cdbdf4d498f1a75017333a20f6ae1db4a476b1` (#808).
Subsequent Draft #809 commits are documentation/source-contract edits;
source-drift does **not** qualify new native MXC executable behavior.
Goldfish stages 5–7 reviewed original planning document commit
`cf23239e59c7cf3e8e5966bb8723c05fe46d31b3`.
Stage-8 reviewed a later documentation revision
`df18a3858ebf73933d8bffe5f29ca261af3f6ef0` and returned
**INCOMPLETE** due to step limits. The updated plan requires re-review,
not automatic transfer of old approvals.
Later source changes require a **new**, exact-SHA evidence record; never reuse #807's
native receipt to qualify #808 or this documentation branch. This plan is based on
[the original D1 EGM concept and design](D1_NETWORK_CONFINEMENT_EGM.md) and
[the existing cold-review packet](D1_EGM_COLD_REVIEW_PACKET.md).

### Fresh-engineer glossary (EGM Step 6 finding)

- **D1:** unpublished Windows developer preview of MedOrigin, not a clinical product.
- **MXC:** Windows ProcessContainer/containment SDK used for this experimental guarded launch; a requested deny policy is **not** an independently audited kernel denial.
- **WFP / ETW:** Windows Filtering Platform policy/flow observability and Event Tracing for Windows telemetry; neither is proven available merely because its API is discoverable.
- **UIA:** Windows UI Automation; checks real graphical journeys and Tauri IPC, not network packets.
- **WebView2:** Microsoft embedded browser runtime; its utility/network workers may involve brokers or services outside the obvious app process.
- **AppContainer / SID:** Windows restricted application security identity and security identifier. Token-capability denial is defense-in-depth, not packet-level confinement.
- **PID / process creation time:** process identifier paired with a start timestamp to avoid mistaking a recycled PID for a persistent descendant.
- **CSP:** content-security policy for app web content, not a universal WebView2 network firewall.
- **`E_NOTIMPL` / `WSA10013`:** reported not-implemented native capture mechanism / socket access denied; neither alone proves complete DNS, UDP, broker or packet isolation.
- **`TEST-NET`:** reserved documentation IP ranges used only in controlled synthetic probes, not a real internet allowlist.

This glossary is informational. The approved observer and OS enforcement backend are still **UNDECIDED**.
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

## Proposed Architecture (unapproved concept)

Already implemented: synthetic D1 Tauri/Rust app, guarded MXC test launcher,
primary-token admission check and sampled UIA/socket/process monitors.
**Not implemented:** an authorized independently verified OS deny policy,
WFP/ETW capture that works on this host, DNS/broker attribution, a mandatory
signed launcher or a release decision. The conceptual component flow is
exact-source binary → guarded contained process → WebView2 descendants →
future approved OS denial policy + independent observer and controls →
sanitized evidence → independent security review. An app-side token check
or CSP is never the independent OS observer.

## Risks & Mitigations (unapproved)

| Risk | Mitigation and decision owner | Gate |
| --- | --- | --- |
| Native MXC capture `E_NOTIMPL` after positive SDK probe | T1 read-only inventory; owner-approved disposable observer, independent security reviewer | G3 BLOCKED |
| UDP `SENT23` and zero local delivery | Independent positive-control and explicit denied-flow packet record, security reviewer | G5 NOT_RUN |
| DNS cache, shared broker/proxy egress, unknown PID | Cross-process, time-bound owner classification; unknown → NO-GO, security reviewer | G4 NOT_RUN |
| PID reuse, short-lived children, dropped trace events | Immutable process start ID and observer event counters; incomplete → STOP | G4/G6 NOT_RUN |
| Hardcoded `networkLoopback` SID may differ by Windows build | Read-only supported-host derivation check before relying on the gate, Windows security engineer | G2 UNVERIFIED hypothesis |
| Binary TOCTOU, unsigned launcher, capability bypass | Immutable file/policy binding, signed mandatory launcher and review, owner/security | T5 HOLD |

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

### Gate evidence location, state authority and transitions

For this D1 experiment, sanitized **append-only factual** evidence belongs under
`experiments/desktop-d1-tauri/evidence/`; independently executed EGM
read receipts and findings belong under `docs/designs/reviews/`. The
[real OpenCode stages 5–6 partial review](reviews/2026-11-01-opencode-egm-goldfish-partial-review.md)
is a **partial finding report**, not a final stage-9 readiness receipt.

A source engineer may only record `NOT_RUN`, `BLOCKED`, or verified
source-only observations for G0–G2. Source CI can check format/lineage but
**cannot mark G3–G7 PASS**. A transition to network-security PASS requires an
independent observer with a verified positive control and complete denied-flow
evidence, followed by independent human security reviewer approval; release
status requires the separately documented owner/governance authorization for
#603/#574/#622. No single author-side signature or OpenCode subagent grants
release approval. Each gate transition must record exact source SHA,
artifact digest, policy/observer identity where applicable, actual verifier,
time window, result and unresolved exceptions; prior receipts are immutable.

### Zero-decision boundary and current readiness

| Stage | Present state | Permitted without architectural choice |
| --- | --- | --- |
| T0 | **READY, documentation-only** | Reconcile exact evidence and enforce existing tests |
| T1 | **READY, read-only inventory** | Read Windows facts and already documented SDK probe fields; never choose or activate an audit backend |
| T2 | **READY only for backend-neutral source schema** | Pure syntax/negative tests; defer observer-specific fields and live verdict until T3 |
| T3–T6 | **HOLD** | No privileged capture, security policy, packaging, cross-platform approval or release |

**Existing paths** are below under `docs/designs/` and
`experiments/desktop-d1-tauri/tests/`. Every path explicitly marked
**new (proposed)** is to be created in a separate Draft after review.
Reading existing Windows edition/privilege metadata is fact gathering,
**not** permission to choose WFP API, ETW provider, VM design, broker
exemption, policy identity or release authority.


The upstream EGM
[implementation-readiness standard](https://github.com/google/elephant-goldfish-model/blob/403d8881d62022490637d740657b33f01e321ea8/resources/document_standards/implementation-readiness-standard.md)
requires a zero-decision plan: exact files, steps, tests and stable checkpoints.
**T0–T2 below are ready as source-only tasks. T3–T6 are intentionally
NOT implementation-ready until the decision and review are accepted.**

### T0 — Evidence reconciliation (source-only; READY)

**EGM Step 5 correction:** this work is source-only, not strictly
documentation-only: the v2 plan-contract test and its Windows CI workflow
are **already existing on Draft #809** at
`experiments/desktop-d1-tauri/tests/windows-d1-egm-v2-plan-contract.test.mjs`
and
`.github/workflows/medorigin-d1-egm-v2-plan-contract.yml`.
T0 may update those exact two existing author-side files as needed, in the
same atomic Draft PR. It may not alter Tauri/Rust runtime, SDK, token gate,
installer or OS policy. Existing `docs/designs/reviews/` reports remain
separate append-only factual evidence (Stage T3 review process), never
fabricated or deleted. If a shared doc has moved since branch cut, stop,
reconcile the diff, and re-run the exact-head checks.


**Files:** update this plan, `D1_NETWORK_CONFINEMENT_EGM.md`,
`D1_EGM_COLD_REVIEW_PACKET.md`, and `SITEMAP.md`, plus the
already existing `experiments/desktop-d1-tauri/tests/windows-d1-egm-v2-plan-contract.test.mjs`
and `.github/workflows/medorigin-d1-egm-v2-plan-contract.yml` for
source-only plan-contract corrections. These are the exact T0 mutation paths;
all runtime/security files remain out of scope.
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

**Reuse requirement:** before writing the proposed inventory, read the
**existing** `experiments/desktop-d1-tauri/tests/windows-mxc-capture-report-verdict.mjs`,
`windows-mxc-capture-denials-experiment.mjs`, existing source-only
`windows-d1-egm-design-contract.test.mjs`, and
`docs/designs/2026-11-01_DRIFT_REPORT.md`. Reuse exact provenance,
source SHA and fail-closed metadata checks; do **not** rerun the native
capture experiment as part of read-only inventory. Changes to those
existing files require a separately reviewed minimal diff.


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

**EGM Step 5 correction:** T2 is limited to a **backend-neutral**
source-verdict for immutable identity, internal consistency, and negative
mutations. The following observer-specific fields are **provisional
examples**, not a frozen API, packet capture format or selected WFP
identity. T2 must NOT hard-code any OS backend, privilege model, broker
ownership heuristic or expected network observations; schema approval
belongs to T3 after architecture selection. Reuse the existing
`experiments/desktop-d1-tauri/tests/windows-mxc-capture-report-verdict.mjs`
and `windows-mxc-protocol-matrix-verdict.mjs` error classifications
where their behavior already applies; add a new parser only for the
missing abstract proof/lineage boundary.


**Files (new, separate next Draft):**
`experiments/desktop-d1-tauri/tests/windows-d1-egm-evidence-verdict.mjs`
and `experiments/desktop-d1-tauri/tests/windows-d1-egm-evidence-verdict.test.mjs`. Keep this free of native OS probes.
**Work:** implement a pure, backend-neutral source validator for
`sourceSha`, `exeSha256`, unique `receiptId`, schema version,
`status` and `scope`. Reject missing or invalid SHA, conflicting
source or binary identity, malformed/replayed receipt IDs, unknown state,
nonzero child exit, and invented security/release PASS. The only possible
positive classification is **SOURCE_SCHEMA_VALID_ONLY**, never an OS
enforcement or release PASS. **Do not freeze an observer API before T3.**
Candidate observer fields `policySha256`, `osBuild`, `observerIdentity`,
`observationStart`, `observationEnd`, `eventCount`,
`droppedEvents`, `positiveControls`, `deniedControls`,
`unknownOwnershipCount`, `brokerClassification`,
`protocolCoverage` and `lifecycleCoverage` remain
**NON-NORMATIVE**, deferred to the approved backend/ADR at T3/T4.
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

**Target files:** not specified or authorized until owner-approved T3/T4
backend selection; this is NOT implementation-ready.
**Required tests once approved:** mandatory entrypoint, no uncontained
fallback, changed EXE/policy hash refusal, restart/upgrade/crash/cleanup,
unknown broker refusal and no global firewall changes. Do not execute now.

Define how policy identity, immutable executable file handle, effective
token, descendants, brokers, errors, recovery and signing are bound
**only after** T4 produces accepted evidence and a new architecture ADR.
No uncontained fallback; installer/update changes need separate review.

### T6 — Cross-platform and release governance (HOLD)

**Target files:** none in the Windows-only D1 experiment. macOS/Linux
qualification is a separate future roadmap, not this implementation.
**Required review once approved:** independently close #603, #574, #622
and re-qualify relevant platform artifacts. No D1 release action now.

**Scope correction (EGM Zoom Out):** Windows D1 work **does not**
include implementing macOS/Linux qualification. That is a separate
platform roadmap with its own owner authorization and evidence.
This stage only tracks release blockers and hands off platform plans
without executing them inside D1. No new cross-platform code is
authorized by this document.


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

The envelope in this section is a **NON-NORMATIVE PLACEHOLDER**.
It is not a receipt from OpenCode, MXC, WFP, DNS or a source test. Any
event schema or observer-specific field becomes normative only through
a separately reviewed, owner-approved T3 architecture decision and T4
observed controls. T2 may validate abstract consistency and fail closed
without asserting OS packet denial.


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

### Verified partial Goldfish invocation, not a completed EGM approval

Two actual native OpenCode `subagent` reviews were completed on the
original v2 document source at `cf23239e59c7cf3e8e5966bb8723c05fe46d31b3`.
The [append-only partial read receipt](reviews/2026-11-01-opencode-egm-goldfish-partial-review.md)
records observed tool sessions, upstream persona/standard reads and
stage-5 zoom-out plus stage-6 comprehension findings. These prompted
this **author-side revision**. Stage-7 design critique, stage-8 second
zoom-out and stage-9 implementation readiness are **NOT PASS**; if a
stage fails or does not complete, the full five-stage Goldfish review
remains **NOT RUN / INCOMPLETE**. A changed plan requires a new
source-bound review of changed sections; no carry-forward approval.

The full review remains NO-GO. This partial receipt does not override
the original `Review state: NOT RUN` marker used for complete five-stage
acceptance, and never substitutes independently approved OS packet
proof or owner/security release decisions.


Upstream source: Google
[Elephant-Goldfish Model](https://github.com/google/elephant-goldfish-model)
pinned to `403d8881d62022490637d740657b33f01e321ea8` (Apache-2.0).
It is a design/review plugin, not a medical model. Read the full plugin,
its persona files and standards; do not claim upstream Google approval.

**Goldfish review: NOT RUN as a complete five-stage acceptance.**
Native OpenCode fresh subagents did execute stages 5, 6 and the three
Stage-7 personas. The initial Stage-8 pass was INCOMPLETE due to tool
step limits; Stage 9 is not complete. Parent-context critique and CI
do not constitute Goldfish or security approval. If a harness lacks actual fresh subagents, stop
review dispatch with **BLOCKED / NOT RUN**, rather than fabricate personas.

Independent reviewers must also read the actual
[native MXC app source](../../experiments/desktop-d1-tauri/tests/windows-mxc-d1-real-app-qualification.mjs),
[Windows token guard](../../experiments/desktop-d1-tauri/windows-token-gate/src/lib.rs),
[socket observer](../../experiments/desktop-d1-tauri/tests/windows-mxc-d1-network-endpoint-guard.ps1),
and [concepts brief](D1_NETWORK_CONFINEMENT_CONCEPTS_BRIEF.md).
Missing a required read is an incomplete stage.

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
