# 2026-11-01 Design ↔ source drift report

**Author-side audit informed by** Google's
[egm-drift-report skill](https://github.com/google/elephant-goldfish-model/blob/main/skills/egm-drift-report/SKILL.md).
**Not an execution of the installed EGM plugin or a Goldfish review.**
Source: stacked Draft PR #801 on #797; synthetic-only; RELEASE NO-GO.
Scope is the **four MedOrigin D1 design documents** currently indexed in
`docs/designs/SITEMAP.md`, not every document across the repository.
Differences below are *pending target-vs-implementation* gaps; the
unapproved design does not authorize filling them on the owner host.

## D1_NETWORK_CONFINEMENT_EGM.md

- **Absent independent packet evidence:** Current
  `windows-mxc-d1-real-uia-qualification.ps1` samples owned TCP/UDP
  endpoints and records WebView2 descendants, but does not collect
  OS-enforced WFP/ETW DNS/IPv4/IPv6 packet-level deny/allow receipts
  for the exact D1 binary. The original external WebView2 egress
  observation in [#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662)
  remains unresolved; zero sampled sockets cannot close it.
- **Partial test-source overlap:** `windows-mxc-capture-denials-experiment.mjs`
  already attempts a synthetic native localhost/TEST-NET negative control
  and writes MXC `captureDenials` JSON; the paired verifier explicitly
  classifies the result `NOT_WFP_OR_PACKET_ATTESTED`. Neither source
  covers the D1 GUI process tree, independent DNS/UDP, or broker
  attribution. The living design now links these sources so future
  implementation cannot assume the mechanisms are missing or sufficient.
- **Partial lifecycle source only:** `windows-mxc-d1-cold-restart-qualification.mjs`
  already runs two exact-SHA MXC GUI sessions and checks process identity
  cleanup. It does not establish installer/upgrade, crash-recovery or
  independently verified broker/network packet continuity.
- **No immutable launch-policy identity:** The current primary-token
  AppContainer/SID helper rejects known Internet/private/hostLoopback
  capabilities but cannot prove authentic MXC source, OS policy or signed
  product binary. Trusted signed bootstrap and identity-based
  confinement remain design choices, not implemented artifacts.
- **No independent security approval:** OS network/WFP negative testing,
  reviewer disposition, security issue #603, and publisher decisions
  #574/#622 are incomplete. This document remains DRAFT / NO-GO.

## D1_NETWORK_CONFINEMENT_CONCEPTS_BRIEF.md

No drift detected in the **author-side concept's documented current scope**.
Its proposed OS boundary and reviewer approvals are future acceptance gates,
not existing functionality.

## D1_EGM_COLD_REVIEW_PACKET.md

- **Reviewer execution absent:** The document requires actual fresh-context
  Goldfish subagents, evidence of isolated reads, completed multi-stage
  review and independent human disposition. This chat session exposes no
  verified fresh-agent tool, so no reviewer reports, receipts or approvals
  exist. Its explicit state remains NOT RUN.

## SITEMAP.md

No drift detected in its current links to the three primary D1 design
artifacts or their DRAFT / Goldfish NOT RUN status.

## Verification boundary

The separately checked-in
`experiments/desktop-d1-tauri/tests/windows-d1-egm-source-drift.mjs`
and test file compare documented guardrails against actual runtime/source
symbols, with **17 in-memory negative mutations** and **20 source-drift
tests**. These are conservative lexical contracts, not a Rust parser,
semantic code review, native MXC run, traffic capture or independent
Goldfish. [Hosted Windows-independent CI run #41315483080](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41315483080)
returned **SUCCESS** for 5 document checks + 20 source-drift tests.
All mutation input exists only in Node memory; no product sources
were rewritten by the tests. No local user files or security policies
were changed.

**Action status:** pending independently approved architecture and
authorized disposable Windows OS observer. **Keep #662 OPEN / NO-GO.**
