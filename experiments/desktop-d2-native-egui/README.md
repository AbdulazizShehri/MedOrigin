# MedOrigin D2 — native Rust UI (experimental, strictly nonpublishing)

This is an **isolated browser-engine-free native UI feasibility spike** derived
from the permissively licensed eframe template, not a replacement for the Tauri
D1 source candidate, the Python Research Core or the Workspace.

## Strict test scope
- Only four exact **fictional in-memory** fixture IDs from the already qualified
  D0 Rust crate, with byte-for-byte SHA-256 checks. Not a FHIR validator.
- No WebView2, JavaScript, TCP server, telemetry, EHR API, file picker,
  patient data, model, download, updater, installer or automatic cloud service
  intentionally present in this source. Dependency auditing is still required.
- Native application compilation is distinct from proving zero network egress:
  an OS-scoped packet-level observation is still required on each platform.
- The UI does not persist state or read from an arbitrary path.
- `eframe`'s `accesskit` feature is enabled explicitly (default features are
  disabled). Before enabling it, Windows UI Automation exposed **0** descendants
  of the native window; after enabling it, Windows exposed **10** accessible
  controls/text nodes, including the four synthetic fixture selectors and
  the verification button. This added Rust/Windows accessibility dependencies
  to the locked dependency graph; their licenses and advisories require review.

## Browser/network dependency regression guard

`tests/browser_free_boundary.rs` runs automatically with `cargo test
--locked --all-targets` in the existing Windows/Linux/macOS matrix. It checks
that D2's direct dependencies remain the native `eframe` UI plus the existing
D0 Rust contract, AccessKit remains enabled without eframe default features,
the committed lock contains no known WebView2/browser engines or selected HTTP
client/server stacks, and authored `src/*.rs` files do not introduce common
direct socket, browser, or external process-launch entry points. Four regression
tests include deliberately forbidden synthetic examples to verify the guard.

This is a **narrow code-review tripwire**, not a complete static analysis,
supply-chain guarantee, operating-system sandbox or packet-capture proof.
Platform-specific dependencies such as `tokio` and `web-sys` may appear in the
multi-platform lockfile without showing that D2 sent any network traffic. Any
intentional feature or dependency expansion needs separate review and a new
audited baseline; never relax this gate silently to enable clinical data.

## Source-bound Rust supply-chain gate (strictly nonpublishing)

`deny.toml` is the explicit `cargo-deny 0.20.2` policy for the native D2
dependency graph across Windows x86_64, Linux x86_64, and Apple Silicon. It
**denies known vulnerability advisories**, disallowed/unlicensed SPDX
expressions and unknown package registries. The license allowlist includes
font-specific `OFL-1.1` and `Ubuntu-font-1.0`, but this is NOT a waiver
of font notice/distribution obligations. No advisory IDs are silently ignored.

This source graph currently contains three **transitive Linux accessibility
maintenance notices**: `RUSTSEC-2026-0370` (`zvariant`),
`RUSTSEC-2026-0371` (`zbus_names`), and `RUSTSEC-2026-0372`
(`zvariant_derive`). See [maintenance issue #673](https://github.com/AbdulazizShehri/MedOrigin/issues/673).
The documented `advisories.unmaintained = "workspace"` policy continues to
**fail on unmaintained direct dependencies** while these transitive notices
remain explicit unresolved review risks. A fully strict `unmaintained = "all"`
scan still FAILS on three records as of 2026-10-29; no release is authorized.
This policy does not downgrade known security vulnerabilities. Re-evaluate
and migrate to the maintained zbus/AccessKit chain before any release.

The independent GitHub source-only security job compiles a **version-pinned,
locked, free `cargo-deny` CLI** and checks advisories, licenses and package
sources with a refreshed remote advisory database. It never runs patient
data, exports packages or publishes releases. Offline reproducibility of
the local policy can be checked using:

```sh
cargo deny --offline --locked check advisories licenses sources
```

An offline pass is dependent on the local advisory database age and is **not**
a substitute for an online refreshed RustSec scan. This D2 policy does not
remediate Python optional extras or historical research pins (issue #622).

## Build and qualification
Use Rust 1.97.1 and checked-in Cargo.lock, from this folder:

```sh
cargo +1.97.1 fmt --all -- --check
cargo +1.97.1 test --locked
cargo +1.97.1 clippy --locked --all-targets -- -D warnings
```

Only execute `cargo +1.97.1 run --locked` on an approved graphical development
machine with sufficient disk capacity and fictional data. Windows, Linux and
macOS CI can verify compilation and pure-data unit tests; headless CI cannot
prove a window was displayed or that outbound packets never occurred.

## Native Windows runtime observation (manual and nonpublishing)

On the authorized interactive Windows machine, after building the native D2
binary and independently checking its SHA-256, run the source-controlled
fail-closed host smoke on a **fresh fixed-drive directory**:

```powershell
$exe = 'D:\MedOrigin-D1-target\debug\medorigin-desktop-d2-native-egui.exe'
$sha = '<caller-verified-build-SHA256>'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests/windows-native-host-qualification.ps1 `
  -ExePath $exe -ExpectedSha256 $sha `
  -AuditDirectory 'D:\MedOrigin-D2-new-audit-dir'
```

The single host runner now verifies the caller-pinned SHA-256, copies the
approved native executable to a **new fixed-drive staging folder** under the
fresh audit directory, and verifies the copied bytes a second time. It runs
the real Windows UI Automation smoke **4/4** on that copy, verifies the same
staged digest after UIA, then relaunches that **same staged copy** for three
TCP/UDP process-tree snapshots. It refuses an absent window or mismatched
fixture result. The audit receipt `qualification.json` records
`staged_executable_sha256`, `executing_verified_copy=true`,
`interactive_uia_4_of_4_pass=true` and always
`network_isolation_qualified=false`, `clinical_qualified=false` and
`release_qualified=false` **even when all socket snapshots are clean**.

A successful *observation* exits nonzero (2); enumeration or identity failure
exits 1. Full endpoint logs remain local. The tool does not change firewall,
WebView2, installers, network or patient data. Windows CI runs five *source-only*
negative cases (wrong digest/name, relative output, UNC source and pre-existing
audit folder preservation) without launching any fixture executable.
This is a better **test-consistency boundary**, not a complete solution to
symlinks/races in a hostile filesystem or a guarantee of OS-enforced offline
runtime.

After enabling AccessKit (2026-10-29), the native window displayed a
Windows UI Automation tree with **10 descendants**. The independent
`tests/windows-native-uia-smoke.ps1` exercised the four actual selector
buttons and verification button, then matched the rendered digest for every
fictional fixture: **4/4 PASS on Windows**. The Windows CI parses this script
but does not run an interactive graphical session. On the rebuilt AccessKit
executable (author-local SHA-256
`45D19A06E5E21667A23A858BA50B6D4077C68C27F6CF6133141C61281221DF4E`),
the host probe again observed a native window and **three samples with 0
external established/all-state TCP and 0 UDP**. The RustSec audit returned
**0 known advisories** for the newly regenerated lock at test time. These
are encouraging limited observations, **not packet-level zero-egress proof**.

**All releases, merging into protected main, distribution, PHI and clinical
usage remain NO-GO** until separate acceptance, security, provenance,
dependency/licensing, accessibility, native UI, and offline-network gates.

Upstream copy-first attribution: [UPSTREAM-NOTICE.md](UPSTREAM-NOTICE.md).

## Real macOS NSAccessibility qualification (synthetic-only, nonpublishing)

The source-controlled `tests/macos-native-ax-qualification.swift` runs on an
**authorized interactive Mac** with Accessibility permission enabled for the
inspecting process. It accepts the process ID of a **real running D2 native GUI**,
enumerates the macOS AX window and requires all four allowlisted fictional
fixture selector controls plus the verification button. It exercises **each
selector through `AXPress`**, then invokes `Verify synthetic SHA-256` and
reads the exact expected 64-character SHA-256 from a *live AX text node*, rather
than calling the D0 hashing function inside the test. Any missing permission,
window, selector, action or result fails with a nonzero exit code.

From this crate's directory on the authorized machine:

```sh
cargo +1.97.1 build --locked
cargo_pid=
./target/debug/medorigin-desktop-d2-native-egui &
cargo_pid=$!
swift tests/macos-native-ax-qualification.swift "$cargo_pid"
kill "$cargo_pid"
```

To conserve disk space, override `CARGO_TARGET_DIR` and delete the disposable
target directory after testing. Do **not** run on patient/PHI data. The scripted
AX test does not disable macOS privacy/security controls, require a paid
service, interact with EHR systems or distribute the unsigned experiment.

**Important asynchronous AccessKit activation:** the first AX request can
legitimately expose only window/title-bar elements (an initial placeholder).
The script repeatedly queries up to 20 times at 200-ms intervals, waiting
for the native widget tree before treating it as failed; it also re-queries
after each action. A single immediate AX screenshot/child listing is
**insufficient evidence that widgets are permanently missing**.

**Actual 2026-10-30 Apple Silicon/macOS 26.6.2 evidence:** the source-bound
D2 **eframe 0.36.0** candidate at parent Draft #675, using Rust 1.97.1,
was compiled and launched from a disposable Mac checkout. The fail-closed
Swift AX smoke returned `MACOS_AX_NATIVE_UIA_4_OF_4_PASS_NONPUBLISHING`
for all four selectors, AX button invocations and four expected digest readbacks,
including on a fresh cold start. The experimental eframe 0.37.0 upgrade alone
did **not** immediately solve missing AX nodes before activation and is **not
part of this proposal**. This evidence corrects the earlier first-query-only
title-bar observation recorded in issue #676; it does not erase that earlier
observation or mean the macOS accessibility release gate is fully accepted.

**Still unqualified:** physical keyboard/VoiceOver focus order, actual screen
reader announcements, independent assistive-technology validation, platform
packet-level zero egress, Linux transitive RustSec notices (#673), third-party
licensing, release signing and artifact provenance. No new D2 release,
installer, protected-main merge, public tag, PHI or clinical claim.

## Real macOS keyboard-only focus and verification acceptance

The source-controlled `tests/macos-native-keyboard-qualification.swift` is a
**separate** real native Mac test from the AXPress-based
`tests/macos-native-ax-qualification.swift`. It uses Apple `CGEvent` virtual
key codes and NSAccessibility *inspection only*: **Tab/Shift+Tab** must move
focus through the four fictional fixture selectors and the Verify control in
both directions, **Space** must select each fictional fixture and activate
the Verify button, and the exact expected SHA-256 must then be readable in the
real app's Accessibility text tree. Direct Rust hashing or accessibility
`AXPress` calls are **not** used by this test.

Run against an **already built, running, unpublished synthetic-only D2
native GUI**, on an authorized interactive Mac with Accessibility permission:

```sh
swift format lint --strict tests/macos-native-keyboard-qualification.swift
swift tests/macos-native-keyboard-qualification.swift "$D2_APP_PID"
```

The script rejects an absent process, missing AX window/controls, incorrect
Tab order or reverse order, nonresponding Space selection, missing Verify
button or digest. It checks for AccessKit's async initialization placeholder
before testing focus; the test sends genuine CGEvent key events to the current
Mac foreground app, so only run in an approved interactive developer session.
It never changes macOS system settings or creates global firewall rules.

**Observed actual Mac evidence (2026-10-30):** Apple Silicon macOS 26.6.2,
pinned eframe 0.36.0, `cargo +1.97.1 build --locked`; all 5 forward Tab
targets, 4 reverse Shift+Tab targets, and **all 4 fictional fixtures
selected/verified using keyboard events only** passed with exact AX-displayed
hashes. Repeated against a **fresh cold launch** with the same
`MACOS_KEYBOARD_4_OF_4_PASS_NONPUBLISHING` and exit 0. A deliberately
incorrect PID returned `MACOS_KEYBOARD_NO_GO`, exit 1.
`swift format lint --strict` also passed. Initial isolated test runs exposed
a synthetic key modifier flags issue, repaired **only in the test harness**
by explicitly clearing modifier flags on key-up. No production Rust/egui
source or lockfile was changed, and no unsupported upgrade is proposed.

This **qualifies synthetic-only keyboard traversal and action delivery on
one real Mac**. It does **not** test actual VoiceOver spoken announcements,
full focus behavior across all OS settings, screen-reader usability on a
second Mac, independent security audit, Linux zbus RustSec maintenance
(#673), OS-enforced network isolation or release authorization. Issue #676
remains OPEN and publication remains NO-GO.


## Experimental macOS App Sandbox network-denial acceptance (NO RELEASE)

A separate source-controlled experiment evaluates **Apple App Sandbox** without
granting the com.apple.security.network.client or network.server entitlements.
This is an experimental, ad-hoc signed *developer-only* alternative to D1's
unresolved Windows WebView2 egress; it **does not** approve switching desktop
architecture or removing any broader security gate (#662/#673/#603).

On an authorized Mac, from this crate directory, run the host-only test:

    bash tests/macos-native-sandbox-network-negative.sh

It compiles a tiny synthetic loopback TCP probe using clang, signs a temporary
app with tests/macos-d2-no-network.entitlements, and verifies all of these:

- Entitlements contain app-sandbox=true but NO network.client/server key.
- An unsigned control successfully connects to an ephemeral listener **bound
  only to 127.0.0.1**, ruling out a false pass from a closed port.
- The identical probe inside a separate ad-hoc signed App Sandbox bundle gets
  EPERM/EACCES (exit 77); crashes or unrelated failures do NOT count as denial.
- No global firewall, Edge/WebView2, macOS security setting or remote socket
  is touched. The listener and all temporary signed probe files are removed.

The second **interactive** test applies the SAME entitlement source to a
**temporary signed copy** of the actual prebuilt D2 native GUI. Run only in an
approved interactive graphical developer session:

    cargo +1.97.1 build --locked
    bash tests/macos-d2-app-sandbox-interactive.sh \
      "$(pwd)/target/debug/medorigin-desktop-d2-native-egui"

When CARGO_TARGET_DIR is overridden, pass the correct absolute binary path.
The script creates a temporary local .app with Info.plist, uses ad-hoc
codesign with the fail-closed entitlement, checks signature and launches
through Launch Services. Then it runs the **real AX 4/4** and **keyboard-only
4/4** Swift tests against the signed app's own PID. It terminates the
experiment and removes the temporary bundle on exit. No binary is uploaded.

**2026-10-30 observed:** Apple Silicon/macOS 26.6.2, Rust 1.97.1,
pinned eframe 0.36.0 native D2 compiled from an immutable Draft branch. The
signed GUI passed four genuine Accessibility selector/hash checks and four
keyboard Tab/Shift+Tab/Space selector/hash workflows, both exit 0. An unsigned
loopback control connected, while an App Sandbox signed probe returned
errno=1 (EPERM), with
MACOS_APP_SANDBOX_LOOPBACK_DENY_PASS_NOT_PRODUCT_EGRESS_AUTHORITY.
A naive sandbox-signed *unbundled* helper initially crashed with SIGTRAP
because its app identifier/Info.plist was missing; the reproducible acceptance
instead uses a verified .app bundle and requires **actual EPERM/EACCES** so a
crash can never be mistaken for network isolation.

**Strict limitations:** this is OS-enforced network denial for a bounded
*probe* and signed-app graphical usability, NOT packet-level no-egress
attestation for all D2 subprocesses, proxies, IPv6, DNS or system services.
It does not qualify Windows/Linux or D1 WebView2. An ad-hoc signed developer
bundle is not notarized or authorized for distribution. VoiceOver spoken
announcements/independent accessibility, RustSec/zbus maintenance, third-party
licenses, owner version/ADR approval, publisher governance, signed release
and protected-main merge remain separate NO-GO. No PHI or clinical data.

## Test-only D2 GUI wrapper with an actual in-process loopback attempt

The **product D2 source under src/** remains **completely network-free**.
In particular, the existing `tests/browser_free_boundary.rs` continues
to reject source code containing `std::net::` and `TcpStream::`.
No exception or suppression was added to that guard. A first experimental
attempt to insert an optional network feature into `src/app.rs` correctly
**failed** this architectural test (3 tests passed, 1 failed). Those changes
were **reverted before committing**.

Instead, the new non-shipping `examples/medorigin_d2_self_sandbox_probe.rs`
uses the unmodified `MedOriginNativePreview` component from the actual
D2 crate and adds exactly one **localhost-only** connection attempt
in the *test wrapper process*. The only destination is numeric 127.0.0.1
on a supplied positive ephemeral port. No DNS, externally addressed socket,
arbitrary endpoint, network plugin, EHR/PHI, or product networking is added.

To build the separate **test-only** binary on an authorized Mac:

    cargo +1.97.1 build --locked --example medorigin_d2_self_sandbox_probe
    bash tests/macos-d2-self-process-network-negative.sh \
      "$(pwd)/target/debug/examples/medorigin_d2_self_sandbox_probe"

For an alternate CARGO_TARGET_DIR, provide its correct absolute example
binary path. The script starts a disposable 127.0.0.1 listener and verifies:
(1) an independent unrestricted C probe can connect;
(2) the **exact same Rust example binary** can connect with no sandbox,
showing `D2_SAME_BINARY_UNCONFINED_LOOPBACK_ALLOWED_CONTROL_PASS` inside
its live AX tree; (3) a signed disposable App Sandbox .app using the same
example binary and no network-client/server entitlement instead yields
`D2_NATIVE_TEST_WRAPPER_LOOPBACK_EPERM_DENIAL_VISIBLE_IN_AX_PASS`;
(4) the signed wrapper still supports genuine **AX 4/4** and genuine
**keyboard-only 4/4** in-memory synthetic SHA-256 GUI workflows. It fails
on any mismatch, crash, missing permission or inconclusive error and
destroys its listener, app, and scratch directory on exit. Neither the
production D2 executable nor its Cargo.lock/frozen research dependencies
are modified; the test-only program is never distributed.

**2026-10-30 real Apple Silicon macOS 26.6.2:** Rust 1.97.1,
pinned eframe0.36.0, standalone example source build PASS, `cargo test
--locked --all-targets` PASS (3 library + 4 architectural guards);
same binary unrestricted control **connected**, signed sandboxed clone
**reported EPERM**, actual synthetic D2 view-model controls/hash outputs
**AX 4/4** and **keyboard 4/4** both PASS. Exact source-bound
macOS hosted CI checks default product source tests, builds this separate
example, lints Swift, and reruns the independently signed helper negative
test; hosted CI does not claim a live graphical session.

**This is not an unmodified product executable self-egress proof.**
It proves the App Sandbox mechanism on a process **embedding the exact D2
UI component** with a test-only networking shim. Packet-level verification
of all product descendants, IPv6/DNS/proxies, Windows D1 WebView2 TCP, Linux
maintenance, notarized signing, independent VoiceOver and security approval
are separate NO-GO gates. Do not publish or merge to protected main.
