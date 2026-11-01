# D1 EGM fresh-context reviewer packet

**Review state: NOT RUN. Approval: NONE. Issue #662: OPEN. Release: NO-GO.**

This packet is designed so a reviewer with **no prior chat context** can
evaluate the proposed [D1 network confinement design](D1_NETWORK_CONFINEMENT_EGM.md).
It is not a review receipt, fresh-agent transcript or finding.

## Review inputs — read completely before reviewing
1. The full [design draft](D1_NETWORK_CONFINEMENT_EGM.md) and its
   [concept brief](D1_NETWORK_CONFINEMENT_CONCEPTS_BRIEF.md).
2. Issue [#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662)
   with real external WebView2 IPv6 evidence and acceptance requirements.
3. Source:
   [real native MXC GUI qualification](../../experiments/desktop-d1-tauri/tests/windows-mxc-d1-real-app-qualification.mjs),
   [primary-token guard](../../experiments/desktop-d1-tauri/windows-token-gate/src/lib.rs),
   [socket observation guard](../../experiments/desktop-d1-tauri/tests/windows-mxc-d1-network-endpoint-guard.ps1),
   and [RED/GREEN loopback report](../../experiments/desktop-d1-tauri/evidence/windows-d1-networkloopback-red-green-20261101.md).
4. [#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603)
   (independent security review), [#574](https://github.com/AbdulazizShehri/MedOrigin/issues/574)
   (release authorization), [#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622)
   (dependency alerts).
5. Use *the installed* Google EGM plugin source for actual personas and
   standards: [egm-review](https://github.com/google/elephant-goldfish-model/blob/main/skills/egm-review/SKILL.md),
   [feature standard](https://github.com/google/elephant-goldfish-model/blob/main/resources/document_standards/feature-spec-standard.md),
   [readiness standard](https://github.com/google/elephant-goldfish-model/blob/main/resources/document_standards/implementation-readiness-standard.md),
   and [Codex integration](https://github.com/google/elephant-goldfish-model/blob/main/docs/codex.md).
   Pin the actual plugin ref for reproducibility. **Do not invent a reviewer
   persona path** or copy only skills without the plugin's agents/resources.

## Reviewer independence
- Launch a real fresh-context agent through the agent harness using its
  documented native spawn tool. For Codex, use its actual fork_context=false
  or fork_turns=none equivalent. No conversation transcript or parent-only
  conclusions may be passed to reviewers. Verify that isolation and file
  reads actually happened; report any unavailable tools.
- Follow the upstream five-stage method: initial zoom-out, comprehension,
  design critique, second zoom-out, implementation readiness. The reviewer
  must read the specified persona, target and complete standard, and return
  actual specific findings, not a simulated multi-persona essay.
- If no fresh-subagent tools are available: **STOP the Goldfish review**,
  report NOT RUN, and do not substitute a same-context self-review.
- Do not label a design approved because source lint or CI is green.

## Questions that should challenge the design
- Can a scoped ProcessContainer identity guarantee no egress by WebView2
  network-service/broker processes outside its tree?
- Are a 12-sample zero endpoint result and a token-capability deny proof
  mistakenly treated as packet denial? Find every such statement.
- Can the proposed positive control demonstrate that the independent
  OS observer actually reports permitted traffic and denied attempts?
- What happens when privileges, Windows policy, DNS correlation or
  observation completeness are absent?
- Are alternatives fairly rejected, or is an undocumented architecture
  choice hidden in the implementation steps?
- Does the design dangerously require altering global host firewall settings
  or disabling updates?
- Are source-to-binary checks, restart behavior, and actual cleanup
  independently verifiable?
- Can an engineer implement the next step without resolving open choices?
  If not, implementation readiness must remain NO-GO.

## Receipt schema for a future *actual* review

Write a separate append-only report under docs/designs/reviews/ only after
running independent agents. It must record:
- reviewed document SHA, exact source commit, actual installed EGM version/ref
- each separate agent identifier, phase/persona, complete read receipts,
  completion status and bounded timestamps (sanitized, no private data)
- findings linked to design sections or source, severity and proposed changes
- author resolution / explicit owner dispositions; leave contested risks open
- explicit failed or missing reviewer phases, not invented approvals
- post-review replay of affected native tests and exact SHA evidence
- human reviewer and owner approval recorded **separately** when granted.

**Current receipt:** none. **Owner authorization for privileged WFP work:** none.
**Production/security approval:** none. **Release status:** NO-GO.
