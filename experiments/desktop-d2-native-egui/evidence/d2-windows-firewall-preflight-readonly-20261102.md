# D2 Windows Defender Firewall read-only preflight — 2026-11-02

**Qualified scope: only read-only policy introspection tooling. MedOrigin release, network containment and NET-02 remain NO-GO.**

## Why this exists

The source-fixed Windows D2 GUI passed local compile, Rust unit checks and three rounds of TCP/UDP endpoint polling on previous exact test build, but no OS-enforced packet denial or application-scoped firewall isolation was demonstrated. `windows-firewall-policy-preflight.ps1` adds a conservative, read-only gate: validate exact executable SHA-256, read all Domain/Private/Public active firewall profiles, enumerate *enabled outbound Block* rules from Windows ActiveStore, and require an exact application path plus unrestricted protocol, ports, IPv4/IPv6 address scope, interfaces and services. Every outcome is nonzero and `NO_GO`, even when a candidate rule matches, because a rule definition alone cannot prove WFP enforcement or DNS/packet-level confinement.

The tool does **not** create, change or delete any firewall rules, disable updates, elevate privileges, send packets, attempt DNS, or touch protected `main`. It emits only status, reason and candidate count (no installed rule names, executable path, IPs, or patient data).

## Windows host facts and actual tests

- Authorized Windows device `Abdulaziz`: current remote terminal **not Administrator**. `New-NetFirewallRule`, `Get-NetFirewallRule` and `pktmon` commands exist; WindowsSandbox.exe absent. Installing/enforcing a rule or packet tracing is **not claimed**.
- Live read-only interrogation of a sample active outbound block rule showed it was scoped to UDP and loopback addresses, not a full-scope all-protocol rule; all three Windows Firewall profiles reported enabled.
- Source-controlled `windows-firewall-policy-preflight-qa.ps1` executed in local isolated scratch against Windows PowerShell executable as a **test control** (NOT against the MedOrigin native binary). PowerShell AST: PASS.
- Bad executable SHA-256 => `NO_GO / EXECUTABLE_SHA_MISMATCH / exit 4`, PASS.
- Nonexistent executable => `NO_GO / POLICY_READ_ERROR_OR_INCOMPLETE_OBSERVATION / exit 4`, PASS.
- Exact test control executable SHA-256 and live ActiveStore => `NO_GO / EXACT_FULL_SCOPE_BLOCK_RULE_NOT_FOUND / exit 2 / 0 candidates`, PASS.
- **3/3 actual Windows control cases PASS**; no successful exit or simulated policy activation was accepted.

**Important scope distinction:** absence of a matching full-scope rule for the PowerShell *test control* does **not** show whether a MedOrigin-specific firewall rule exists. A compiled MedOrigin D2 binary must be independently hash-pinned and checked on the target test host for program-specific policy acceptance. Even a matching rule must remain `NO_GO` pending independently monitored OS packet-denial negative tests.

## Still required

1. On a disposable admin-authorized Windows test environment, enforce a narrowly scoped per-app policy **before** launching exact pinned MedOrigin, with audited cleanup and no machine-wide WebView2/Edge update side effects; demonstrate policy persistence in descendants and that a safe test-only DNS/TCP/UDP escape attempt is blocked.
2. Capture independent packet/WFP/DNS attribution across startup, interaction, crash, restart and shutdown, plus deliberately injected negative controls. Read-only socket polls miss transient attempts.
3. Independent security sign-off, Linux RustSec #673, macOS spoken VoiceOver #676, optional extras #622, owner signing/release #574 and D1/WebView2 #662 remain unresolved. Do not merge/release, import PHI or claim clinical/offline readiness.

References: Windows PowerShell NetSecurity cmdlet documentation for Get-NetFirewallRule, Get-NetFirewallApplicationFilter, Get-NetFirewallPortFilter, Get-NetFirewallAddressFilter, and policy ActiveStore behavior. 
