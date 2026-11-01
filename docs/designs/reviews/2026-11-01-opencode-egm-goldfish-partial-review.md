# Google EGM via OpenCode — independently executed partial Goldfish review

**2026-11-01 • PARTIAL • NO APPROVAL • RELEASE NO-GO • #662 OPEN.**
This is an append-only, author-collected summary of **actual** OpenCode v2
native `subagent` tool sessions on an authorized Windows desktop.
It is **not** a complete five-stage EGM Goldfish review or independent
security approval. Do not merge, ship, handle PHI or claim zero egress.

## Frozen inputs, environment and independence

- MedOrigin checkout: `cf23239e59c7cf3e8e5966bb8723c05fe46d31b3`
  (Draft #809; this report itself is a subsequent docs-only commit).
- Google upstream complete EGM checkout:
  `403d8881d62022490637d740657b33f01e321ea8`,
  including real `agents/`, `skills/` and `resources/document_standards/`.
- OpenCode `v2.1.2` on Windows; verified built-in **subagent**
  child sessions with isolated contexts and documented native read tools,
  model `opencode/beam-free` (free model listed locally).
- Isolated source/EGM/review workspace on Windows `D:`; no changes to the
  original MedOrigin workspace, firewall or system security controls.
- Reviewer agents were configured `mode:subagent`, with
  edit/shell/web/subagent-redelegation disallowed. The parent Plan agent
  was instructed to call the real native `subagent` tool and not invent
  reviewer results.
- Receipt evidence was checked by exporting OpenCode top-level and child
  sessions with `opencode session export <id>`: a real tool entry
  `name=subagent`, `state.metadata.status=completed`, and actual
  child `read` tool results for the pinned EGM persona, standard and
  MedOrigin target file. Fresh context means **no parent transcript was
  supplied as a reviewer read list**. This was a source-review only.

## Stage 5 — Initial zoom-out — COMPLETE with findings (NOT approved)

- Parent session: `ses_e68034760ffe2hkCWjj6hyDiqV`.
- Actual child session: `ses_e680331fcffeD3CNDn6341ixHc`;
  native subagent tool metadata reported `completed`,
  `truncated:false`.
- Verified child `read` calls included
  `EGM/agents/zoom_out.md`,
  `EGM/resources/document_standards/zoom-out-standard.md`,
  `MedOrigin/docs/designs/D1_EGM_EXECUTION_PLAN_V2.md`,
  original D1 design, cold-review packet, native #807 receipt,
  `E_NOTIMPL` receipt, native launcher/token gate, source tests and
  other linked files. These are actual tool calls, not merely a list
  asserted by the reviewer.
- **Major:** T0 documentation-only file boundary contradicts the need
  to create/qualify the v2 contract-test file.
- **Major:** T2 prematurely freezes observer-specific receipt fields
  before T3 chooses architecture and observer.
- **Major:** T1 and T2 fail to explicitly reuse and distinguish
  `windows-mxc-capture-report-verdict.mjs` and existing readiness/drift
  tooling; risk duplicating source.
- **Major:** T6 cross-platform qualification is unnecessarily included
  inside the Windows-only D1 packet; move to a separate roadmap.
- **Minor:** distinguish illustrative, unapproved schema from normative
  implementation; document conflict resolution for shared design files.
- **Correctly retained:** SHA lineage #807 ≠ #808, unresolved UDP
  `SENT23`, no packet/WFP assertion and release NO-GO.

**Disposition:** findings are OPEN pending separate design revision. No
architecture approval has been granted by this reviewer.

## Stage 6 — Comprehension — COMPLETE with findings (NOT approved)

- Parent session: `ses_e67fef8e2ffekURg64inNEoyMT`.
- Actual child session: `ses_e67fea2f1ffexguHIrJuXQlWqT`;
  native subagent metadata `completed`, `truncated:false`.
- Child export: completed with **15 actual read calls**, including
  `EGM/agents/comprehension.md`,
  `EGM/resources/document_standards/feature-spec-standard.md`,
  the entire v2 design, original design, cold-review packet,
  native #807 and native capture/UDP negative receipts, source tests,
  Windows token guard, MXC runtime and endpoint audit.
- **Major:** define MXC, WFP, ETW, UIA, AppContainer, SID, PID, CSP
  and short negative-result codes so a fresh engineer can understand.
- **Major:** distinguish **existing** vs **proposed new** files
  with exact repo-relative paths.
- **Major:** T0 doc-only boundary is unclear about T3 future review
  artifacts; reviewers must not create fake `docs/designs/reviews/`
  approval receipts.
- **Major:** gates G0–G7 need responsible signers,
  an append-only storage path and explicit transition authority.
- **Major:** T2 evidence JSON is ambiguously normative vs illustrative;
  make it explicitly non-normative before owner/security decisions.
- **Major:** define what T1 may inspect as nonprivileged environment
  facts vs forbidden architecture or policy decisions.
- **Minor:** map 'Implementation readiness: PARTIAL' to each stage,
  and link the actual reviewer receipt schema.
- Remaining network security claims were explicitly **unverified**;
  #808 has no native replay at its newer source SHA.

**Disposition:** findings are OPEN pending a revision; no review
PASS, packet confinement or security approval follows.

## Stage 7 — Design Critic — ONE persona COMPLETE, others pending

- Parent: `ses_e67fcf85fffeYiIiNf1mYvt1Ma`.
- Genuine child: `ses_e67fcbed2ffeloq9hYMXSmoS3K`.
- Verified exported `subagent` tool metadata: `status=completed`,
  `truncated=false`, child finished successfully, **28 real read calls**,
  including `EGM/agents/design_critic.md`, EGM feature-spec standard,
  original target v2 plan, Rust token guard, Tauri app config,
  archived native #807 and MXC capture/UDP negative evidence.
- **Blocker:** current process token admission check cannot attest
  application-wide WFP, broker, DNS, UDP or packet containment.
- **Blocker:** native `captureDenials E_NOTIMPL` and `UDP SENT23`
  retain separate unsupported evidence boundaries; no G3–G5 PASS.
- **Major:** verify the `networkLoopback` SID derivation across
  supported Windows builds before treating the hardcoded capability SID
  check as a universal defense. This is a **reviewer-raised hypothesis**,
  not a reproduced fail-open security finding.
- **Major:** source digest checks do not yet provide a signed mandatory
  startup/immutable-handle proof; source-to-executable TOCTOU and launcher
  governance remain T5 HOLD.
- **Major:** no independent Windows broker/DNS ownership attribution
  or short-lived child packet observation. Existing PowerShell socket
  snapshots cannot prove the missing events.
- **Major:** no actual observer-specific T2 schema enforcement, tamper
  chain, independently witnessed positive/negative packet controls or
  OS packet claim. Need bounded source-only negative validator and T3
  architecture decision before such a claim.
- **Major:** WebView2 background TCP evidence remains issue #662 OPEN.
- **Correction of reviewer overreach, checked against actual GitHub
  source:** Reviewer F9 claimed no `src-tauri/capabilities/` folder.
  **False**: `src-tauri/capabilities/default.json` exists, limits
  capability to `main` with `core:default` and no network plugin.
  The remaining question is whether that *actual* grant suffices for
  `preview_status`/`hash_fixture` and content isolation, not an
  absent capability directory. Do not carry forward that false claim.
- **Correction of stale reviewer wording:** The old target draft said
  no real fresh review had happened; that was true when authored,
  but stages 5 and 6 actually ran in OpenCode and this stage-7 critic
  also ran. Full five-stage sign-off is still **INCOMPLETE**.

This is only the **design_critic** member of stage 7; structural and
style subagents must be independently verified, and stages 8 and 9
are not satisfied by it. Child findings are adversarial hypotheses
requiring triage and source confirmation, not security proof.

## Stage 7 — Structural and Style — TWO additional personas COMPLETE

**Structural independent reviewer:**
- Parent `ses_e67f9af31ffe6sCbpHTNUpxe5I`;
  child `ses_e67f98e54ffeq7PnNhM6o3VGmw`.
- Verified real native `subagent` metadata `completed`,
  `truncated=false`; child finished `succeeded` with **10 real
  read calls**, including `EGM/agents/structural.md`, the
  feature-spec and readiness standards, original v2 plan,
  original design, reviewer packet and existing contract tests.
- Verdict **PASS WITH NOTES** for formatting alone, with **4 Major**
  and **4 Nit** source-structure findings:
  missing separate **Proposed Architecture** and **Risks &
  Mitigations** sections, T5/T6 lacking even explicitly-deferred file
  and test boundaries, and reviewer reading list missing four
  required source paths. Clarify which requirements are deferred to
  owner ADR and do not let format PASS become readiness approval.
  Existing local links, fences and tables were acceptable.

**Style independent reviewer:**
- Parent `ses_e67f99a53ffenAZnSOYugg0cT8`;
  child `ses_e67f9795bffenLcUpnCIMp4P4p`.
- Verified `completed`, `truncated=false`, child `succeeded` with
  **3 actual reads**: `EGM/agents/style.md`, the full feature-spec
  standard, and the complete v2 target plan.
- Reviewer reported **15 readability defects**, including inconsistent
  state tokens `NOT_RUN` vs prose `NOT RUN`, synthetic/fictional
  fixture terminology, unexpanded MXC/WFP/ETW/UIA acronyms, mixed
  punctuation and slash-separated statuses.
- These are suggestions subject to author disposition; this review
  did not modify source, run code, or grant security approval.

**Stage 7 status: all three actual child personas invoked and
completed (design critic, structural, style), but their Major and
Blocker findings are OPEN; this does NOT mean design PASS.**
Reviewers evaluated the original v2 source
`cf23239e59c7cf3e8e5966bb8723c05fe46d31b3`.
An author-side v2 revision subsequently began resolving stage-5/6
findings on a later commit. Independent stage-8 and stage-9 checks
must explicitly name that newer source rather than carry forward
a design approval.

## Incomplete stages and evidence boundaries

- **Stage 7 Design critique: THREE personas COMPLETED, findings OPEN** (not design approval).
- **Stage 8 Second zoom-out: NOT RUN.**
- **Stage 9 Implementation readiness: NOT RUN.**
- Independent human security review, owner choice A/B, packet/WFP/DNS/
  IPv4/IPv6/UDP and Windows broker attribution: **NOT APPROVED /
  NOT VERIFIED**. `captureDenials` still returned `E_NOTIMPL`
  and `UDP SENT23` remains ambiguous.
- This receipt documents **actual partial reviewers**, but the
  entire Google EGM five-stage acceptance remains **INCOMPLETE**.
  The fresh child reviews also do not qualify runtime Tauri/MXC code
  or release readiness.
- Existing issues [#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662),
  [#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603),
  [#574](https://github.com/AbdulazizShehri/MedOrigin/issues/574)
  and [#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622)
  remain separate blockers. `publication_authorized=false`.

Source of truth for future continuation: actual OpenCode child session
exports + exact target source SHA above, **not** this author-written
summary alone. Never overwrite missing/failed reviewer steps with
hypothetical summaries.
