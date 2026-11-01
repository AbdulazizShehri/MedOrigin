# OpenCode v2 + Google EGM Goldfish — reproducible Windows review runbook

**Nonpublishing / synthetic only.** This documents the actually exercised
workflow from 2026-11-01. It is not a way to bypass Windows network isolation,
independent human security approval, protected-main rules or issue #662.
Author-side CI cannot approve a design.

## Exact reproducibility inputs

- OpenCode CLI `v2.1.2` on an authorized Windows desktop.
- Google [Elephant-Goldfish Model](https://github.com/google/elephant-goldfish-model)
  pinned to complete source `403d8881d62022490637d740657b33f01e321ea8`.
  The entire repository is needed: `agents/`, `resources/`,
  `skills/`, `docs/`; a copied prompt alone is not the plugin.
- MedOrigin plan source commits are recorded in the
  [actual partial-reviews report](reviews/2026-11-01-opencode-egm-goldfish-partial-review.md).
  Freeze the exact source commit *before* each review. A later docs edit
  does not inherit prior review approval.
- The actual 2026-11-01 experiments used `opencode/beam-free`, one of
  OpenCode's displayed free models. Provider availability, rate limits
  and costs can change; check `opencode models` before use, and never
  silently choose a paid model.

## Disposable workspace and safety

Use a disposable sibling checkout (prefer drive D: if it has free
space), never clobber a different branch's worktree. Example
PowerShell commands, with local paths adjusted to the authorized host:

```powershell
git clone https://github.com/google/elephant-goldfish-model.git D:\EGM-review\EGM
git -C D:\EGM-review\EGM checkout --detach 403d8881d62022490637d740657b33f01e321ea8
# Fetch the exact MedOrigin review commit into a separate detached worktree.
git -C C:\path\to\MedOrigin fetch --no-tags origin docs/medorigin-d1-egm-v2-readiness-20261101
git -C C:\path\to\MedOrigin worktree add --detach D:\EGM-review\MedOrigin FETCH_HEAD
opencode --version
opencode models
```

This is a plan/review harness, not runtime testing. No elevation,
WFP policy, global firewall, WebView2 update changes, patient data,
native capture or network probe is authorized.

## Native OpenCode subagents, not one-chat roleplay

OpenCode **v2** discovers `opencode.json` in the current review
workspace. Its schema uses `agents` (plural), `mode: "subagent"`
and ordered permission rules. Example **configuration fragment**:
do not copy user credentials or global config into the repository.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "default_agent": "plan",
  "model": "opencode/beam-free",
  "agents": {
    "egm-zoom": {
      "mode": "subagent",
      "model": "opencode/beam-free",
      "description": "Google EGM read-only zoom-out reviewer",
      "system": "Read full EGM/agents/zoom_out.md, full EGM/resources/document_standards/zoom-out-standard.md, full MedOrigin/docs/designs/D1_EGM_EXECUTION_PLAN_V2.md and referenced sources. Report exact read receipts, file/line findings, FAIL/PASS/INCOMPLETE. No edits, shell, web or approval.",
      "permissions": [
        {"action": "edit", "resource": "*", "effect": "deny"},
        {"action": "shell", "resource": "*", "effect": "deny"},
        {"action": "subagent", "resource": "*", "effect": "deny"},
        {"action": "websearch", "resource": "*", "effect": "deny"},
        {"action": "webfetch", "resource": "*", "effect": "deny"}
      ],
      "steps": 48
    }
  }
}
```

Define separate real subagent configurations for EGM personas:
`comprehension.md`, `design_critic.md`, `structural.md`,
`style.md`, `implementation_readiness.md`,
`codebase_details.md`; the parent orchestrator must invoke each
using OpenCode's real `subagent` tool. Every child reads the full
persona and applicable standard. Do not mix earlier reviewer findings
into a fresh child prompt.

From the disposable workspace, run a new OpenCode CLI session:
```powershell
opencode run --standalone --agent plan --model opencode/beam-free "Use the native subagent tool with agent=egm-zoom and background=false to review MedOrigin/docs/designs/D1_EGM_EXECUTION_PLAN_V2.md. Wait for child completion. Do not simulate."
```

Use `background=false`; a background child that did not complete
before a private-server process exits is **NOT RUN**. One actual attempt
returned a child session with only its user prompt and no reviewer tool
events, so it was explicitly rejected; re-invoking in the foreground
produced a separate completed child.

## Independent evidence audit and acceptance

OpenCode session CLI: `opencode session list --format table` and
`opencode session export <PARENT_SESSION_ID>`. Parse the JSON export
before describing a Goldfish as completed:

1. Parent assistant content actually has a `type:"tool"`,
   `name:"subagent"` entry and its `state.metadata.sessionID`.
2. `state.metadata.status` is `completed` with
   `truncated:false`; child last outcome is `succeeded`.
3. Independently export that exact **child** session and inspect
   real `read` tool calls for the pinned EGM persona, corresponding
   standard and complete target document. A model's self-reported
   "read receipts" are not a substitute for tool events.
4. Record actual findings and source paths; compare with repository
   files. Goldfish reviewers can be mistaken. During this run a
   reviewer falsely claimed that `.github/workflows/...` and
   `.agents/skills/...` were absent, although direct
   Windows `Test-Path -LiteralPath` verified both exist.
5. Distinguish **tool completion** from a **review PASS**. Stage 8
   returned a genuine completed subagent with explicit **FAIL**,
   while other stages returned PASS-with-findings or INCOMPLETE.
6. Never convert five executed stages to "approved" without
   resolving blocking findings, rerunning the relevant source-bound
   reviews and obtaining separately authorized human security/owner
   decisions.

The 2026-11-01 actual run and its specific parent/child session IDs,
provisional findings, conflicting reviewer dispositions and false-positive
corrections are in the
[append-only review report](reviews/2026-11-01-opencode-egm-goldfish-partial-review.md).
That report is evidence of review activity, **not** WFP/ETW,
DNS, TCP/UDP/IPv4/IPv6, WebView2 broker or release qualification.

Keep the D1 plan **Draft**, the EGM five-stage outcome **NOT APPROVED**,
#662 open, and `publication_authorized=false`.
