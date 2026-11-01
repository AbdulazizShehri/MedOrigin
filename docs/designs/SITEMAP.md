# MedOrigin design index

Designs are **proposals**, not implemented product claims or permissions to release.
Designs that lack genuine independent reviews must remain **DRAFT**.

| Document | Purpose | State |
| --- | --- | --- |
| [D1 Network Confinement EGM](D1_NETWORK_CONFINEMENT_EGM.md) | EGM-style threat model, alternatives, scope and falsifiable OS-level network acceptance design for issue #662 | **DRAFT — Goldfish NOT RUN — NO-GO** |
| [D1 EGM v2 Execution Plan](D1_EGM_EXECUTION_PLAN_V2.md) | Source/SHA-bound readiness split, T0–T2 zero-decision tasks, G0–G7 acceptance gates and T3–T6 security HOLD requirements; incorporates PR #807 native evidence and PR #808 source-only limits | **DRAFT — Goldfish NOT RUN — RELEASE NO-GO** |
| [D1 EGM Cold Review Packet](D1_EGM_COLD_REVIEW_PACKET.md) | Self-contained reviewer reading list, actual fresh-subagent requirements, open issues, no-approval boundary | **Prepared; reviewers NOT RUN** |

**Supporting materials:** [concepts brief](D1_NETWORK_CONFINEMENT_CONCEPTS_BRIEF.md) (proposal);
[source-to-design drift report](2026-11-01_DRIFT_REPORT.md) (source-only
findings); [actual OpenCode Goldfish partial receipts](reviews/2026-11-01-opencode-egm-goldfish-partial-review.md)
(stages 5–7 completed with open findings, stage 8 reported FAIL on
a later revision, full five-stage review incomplete). None is
security approval or a packet-capture receipt.

**Evidence:** [2026-11-01 source↔design drift report](2026-11-01_DRIFT_REPORT.md) records outstanding OS packet, broker, signed-launch and review gaps. Its lexical test suite is not a Goldfish review or an OS capture. All statuses remain NO-GO.

The preliminary [concept brief](D1_NETWORK_CONFINEMENT_CONCEPTS_BRIEF.md) motivates the design. The issue [#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662) remains the security source of truth; the author-side plan cannot replace independent review or OS/network packet capture.
