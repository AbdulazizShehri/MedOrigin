---
name: medorigin-elephant
description: Project context loader for MedOrigin synthetic-only Windows D1 security designs.
---

# MedOrigin elephant — source-first project context

This is a **project context skill**, not a copy, fork or installation
of Google's Elephant-Goldfish Model plugin. Read the actual EGM plugin
skills/personas/standards from its installed bundle before invoking
EGM workflows. Do not call a same-session self-review "Goldfish".

## Read and trust these repository sources in order

1. `README.md` and `docs/README.md`: product and clinical boundaries.
2. `docs/designs/SITEMAP.md`: status of living design drafts.
3. `docs/designs/D1_NETWORK_CONFINEMENT_CONCEPTS_BRIEF.md`.
4. `docs/designs/D1_NETWORK_CONFINEMENT_EGM.md`.
5. `docs/designs/D1_EGM_COLD_REVIEW_PACKET.md`.
6. GitHub issue #662: real WebView2 egress and open acceptance criteria.
7. `experiments/desktop-d1-tauri/README.md`, `src-tauri/`,
   `windows-token-gate/src/lib.rs`.
8. `experiments/desktop-d1-tauri/tests/windows-mxc-d1-real-app-qualification.mjs`
   and `windows-mxc-d1-network-endpoint-guard.ps1`.
9. `experiments/desktop-d1-tauri/evidence/windows-d1-networkloopback-red-green-20261101.md`.
10. GitHub issues #603, #574, #622 for independent review and release gates.

## Hard limits

- Nonpublishing, no PHI, synthetic fixtures only, zero cost.
- No protected-main merge, signed release, installer, clinical use,
  outbound patient/workspace data, cloud paid inference or global
  firewall/Edge update changes.
- Source snapshots do not establish OS-enforced no-egress.
- Token AppContainer + SID checks do not establish WFP packet/DNS
  denial or cryptographic launch-policy authenticity.
- Do not overwrite historical evidence, Git tags or frozen research
  records. Store durable findings and designs in the GitHub repository.
- Do not run privileged OS experiments on the owner's non-admin
  Windows host; require a separately authorized disposable test host.
- Every new security design must consider alternatives and have
  genuinely independent EGM reviewers before architectural approval.

## Handoff

**EGM doc status: DRAFT. Goldfish review: NOT RUN. Security #662: OPEN.
Release: NO-GO.**

Run the real upstream EGM plugin in a harness with fresh-context
subagents when available. Use the cold review packet's read list.
Do not assume any earlier chat was given to a fresh Goldfish.
