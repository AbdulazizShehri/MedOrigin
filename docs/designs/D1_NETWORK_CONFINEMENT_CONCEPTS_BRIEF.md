# D1 network isolation — EGM concept brief

**State: preliminary author-side concept. No fresh Goldfish review conducted.**
**Date: 2026-11-01. Synthetic-only, nonpublishing, NO-GO.**

## Need
A developer preview that is described as offline cannot rely on React CSP
or local Tauri commands when its embedded WebView2 descendants have already
shown external IPv6 connections. Earlier observed traffic is documented in
[#662](https://github.com/AbdulazizShehri/MedOrigin/issues/662).
Recent native MXC token-policy and four synthetic GUI tests are positive
engineering evidence, not OS-enforced whole-process network proof.

## Desired outcome
A reviewer can independently answer, with verifiable exact-binary and
OS-side evidence, whether network attempts from all app-owned processes
and relevant brokers are **blocked by the operating system**, and whether
local Tauri IPC continues to work, through the entire app lifecycle.

## Non-negotiable constraints
No real patient information, no PHI, no clinical permissions; no publication
or main merge; no paid services; no background host-global Edge/WebView2
blocking; no weakening Windows/Edge security updates; no unattended
privilege escalation or global firewall/audit modifications; retain
repository-only long-term evidence and delete temporary Windows build files.

## Largest uncertainties
What process/broker identity can actually be confined? Which scoped OS
instrumentation has reliable DNS/IPv4/IPv6 records? Is a disposable
authorized Windows VM essential? Can the standalone root-only security
checks be tied to exact signed artifacts without a loophole at restart?
How do we distinguish absent network attempts from proved OS denial?

## Candidate directions
- Native ProcessContainer plus independently verified scoped Windows filtering
  in a disposable machine, **not yet qualified**.
- Disposable Windows VM with externally observed egress denial, as a feasibility
  fallback, **not yet qualified for end-user distribution**.
- CSP/flags/sampled sockets alone fail the stated requirement and must not
  be used to declare a release gate green.

The [design draft](D1_NETWORK_CONFINEMENT_EGM.md) records precise acceptance,
test controls and alternatives. Architectural trade-offs and human
acceptance remain open. This concept is not an EGM brainstorm outcome
validated by Goldfish subagents.
