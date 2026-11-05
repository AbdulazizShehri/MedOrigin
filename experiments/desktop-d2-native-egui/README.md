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
- The UI does not persist state. In the new opt-in drag/drop demo it reads only
  the file explicitly dropped by the user, under a strict fictional-only JSON
  allowlist; this is NOT a general patient file opener. Explicitly selected
  paths may still be OS-mounted drives, so packet-level isolation remains NO-GO.
- `eframe`'s `accesskit` feature is enabled explicitly (default features are
  disabled). Before enabling it, Windows UI Automation exposed **0** descendants
  of the native window; after enabling it, Windows exposed **10** accessible
  controls/text nodes, including the four synthetic fixture selectors and
  the verification button. This added Rust/Windows accessibility dependencies
  to the locked dependency graph; their licenses and advisories require review.

## Drag-and-drop local synthetic Bundle demo (private, NONCLINICAL)

A user can now launch the native egui program normally, then drag **one**
canonical FHIR-shaped **fictional-only** JSON file into the window. For an
admitted example use
`fixtures/core/synthetic-multipatient-fhir-bundle.json` from this reviewed
source checkout. The existing multi-patient fictional chart opens with a
visible "Opened local synthetic-only JSON" indicator. The demo can be cleared
with its existing fictional records Clear control or Escape.

The file is read locally with a 32,768-byte upper bound and only after an
explicit drop. Non-JSON files, multiple dropped files, symlinks/reparse paths,
noncanonical bytes, real-world patient names, observations/values, extraneous
fields, nonfictional resource IDs, malformed references or cross-patient
relationships fail closed. Rejected names, paths, or source bytes are not
shown in the UI or logged. Existing protected Core session modes cannot be
replaced by a dropped file; clear them first. The app does not save, export,
watch a directory, create an account, use a model or call an application
network API. It does not qualify PHI processing or network isolation. A
Windows mapped drive is not independently ruled out by an ordinary drive
letter, so operators must use a reviewed local fixture drive for offline QA.

This is useful end-user interaction work in the **experimental** native
Desktop only; it is neither an EHR file importer nor a clinical validator.
The Windows drag-and-drop action still requires real interactive UI testing
on the exact commit. Rust tests cover positive canonical fictional input,
invalid/oversize/noncanonical input, safe path checks and source/session
fail-closed behavior. Source tests or compilation alone do not prove Windows
drag-and-drop or an installed user journey.

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

## Fictional JSON side-by-side comparison (nonclinical)

The native GUI can compare **two distinct source-compiled fictional JSON**
fixtures in two read-only columns. Each side independently rechecks its D0 raw
SHA-256, byte length, allowlisted ID, limited FHIR envelope status, and
synthetic-only/no-release contract before either text is displayed. The nine
eligible fixtures are at most 2,048 bytes each. The three raw-byte boundary
fixtures (invalid UTF-8, 32,768 and 32,769 bytes), forged indices, and comparing
a fixture to itself fail closed without retaining a previous comparison.

This is an educational developer aid for observing differences between
**fictional** Patient, Observation and Bundle examples. Expected negative
statuses are test outcomes, not clinical conclusions. No JSON is repaired,
imported, normalized, exported, copied to the clipboard, persisted, transmitted
or processed by a model. A new fixture selection, verification or preview
clears stale comparisons. It does not validate FHIR R4 or prove network
isolation; release remains NO-GO.

The comparison selector uses accessible buttons rather than a ComboBox: a real
Windows UIA probe found that the native ComboBox did not expose the required
ExpandCollapsePattern. The source-controlled real Windows test exercises the
button-based alternative on an exact SHA-256-pinned executable:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows-native-fictional-compare-uia.ps1 `
  -ExePath '<absolute path to approved native debug exe>' `
  -ExpectedSha256 '<externally verified 64-hex SHA256>'
```

See [the nonpublishing Windows evidence](evidence/d2-fictional-json-comparison-20261102.md).
This does not replace independent macOS VoiceOver or Linux AT-SPI acceptance
for the new comparison UI.

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

## Experimental Linux rootless network namespace E2E (NO RELEASE)

The separate, **nonshipping** `examples/medorigin_d2_self_sandbox_probe.rs`
now supports a Linux-only probe result for `ENETUNREACH` / `EHOSTUNREACH`
(errno 101/113) and emits that one in-memory synthetic probe result to the
test process's stderr. This does **not** add networking to D2's
`src/` files. The existing conservative
`tests/browser_free_boundary.rs` contract still forbids network/browser
entrypoints in the real application source without exceptions.

On a specifically authorized Linux development host with unprivileged
USER+NETWORK namespaces enabled, and a temporary built test example:

    cargo +1.97.1 build --locked --example medorigin_d2_self_sandbox_probe
    bash tests/linux-d2-rootless-netns-negative.sh \
      "$(pwd)/target/debug/examples/medorigin_d2_self_sandbox_probe"

The fail-closed script uses a temporary **127.0.0.1-only** listener, a
separate Python TCP positive control and the **identical Rust test-only
GUI executable** in two conditions: unrestricted connection **ALLOWED**,
then `unshare -Urn` rootless network namespace **UNREACHABLE**. In both
conditions it requires a real eframe window to appear in a disposable Xvfb
display. Linux's X11 abstract UNIX sockets are network-namespace scoped,
so Xvfb is intentionally started **within** the isolated namespace for
the isolated GUI (not accessed across the boundary). The child compares
its `/proc/self/ns/net` inode with the parent host namespace inode and
requires exactly one DOWN loopback interface; the host never changes its
firewall, addresses, or routes. The child explicitly requires
`D2_LINUX_ROOTLESS_NETNS_LOOPBACK_UNREACHABLE`, never treats a timeout or
unknown socket failure as a qualifying denial, and reports its native
window observation. Nonzero exit if any permission, namespace, positive
control, test-only process, socket result, or window condition fails.

**Local evidence (2026-10-30):** authorized Ubuntu 26.04 WSL2,
Rust 1.97.1, pinned eframe 0.36.0, real Xvfb/X11, rootless
`unshare -Urn`; unrestricted same-binary socket and window PASS;
within isolated user+network namespace, only `lo` DOWN, same-binary
connection UNREACHABLE and GUI window visible, full E2E **exit 0**.
The initial diagnostic uncovered WSLg's external Wayland default;
the test explicitly selects disposable X11. A further diagnostic
showed that an X server launched *outside* the network namespace cannot
be used through its abstract UNIX socket from inside; the accepted
test runs a separate Xvfb **inside** the new namespace.

GitHub Actions source CI on Linux compiles and tests the exact code
and conservatively preserves the production no-network source guard.
It does **not** claim hosted unprivileged user/network namespace support
or substitute source compilation for live namespace execution.

**Limits:** this is an isolated **test-only wrapper** embedding actual D2
UI components, not the untouched product executable, and does not
prove every GUI descendant, data path, IPv6, DNS, proxies, system service,
Windows D1 WebView2 outbound TCP or macOS notarization. This also
does **not** resolve the Linux AccessKit/zbus5 transitive unmaintained
RustSec notices (#673), VoiceOver, independent security review or owner
publisher approval. No PHI, release, protected-main merge or installer.

### Additional real default D2 executable smoke under rootless Linux isolation

The native default executable is also tested **without a modified or
test-only networking entry point**. Source-controlled
`tests/linux-d2-real-app-isolated-window.sh` accepts only the absolute
`medorigin-desktop-d2-native-egui` executable, creates separate unprivileged
USER+NETWORK namespaces using `unshare -Urn`, verifies a distinct
`/proc/self/ns/net` inode and exactly one DOWN loopback interface, and starts
an Xvfb server **inside the same isolated namespace**. It then launches the
unmodified default D2 app and requires its real X11 window title to appear,
while the process remains alive; any missing user namespace, interface
violation, GUI failure, crash or missing window fails closed.

    cargo +1.97.1 build --locked --bin medorigin-desktop-d2-native-egui
    bash tests/linux-d2-real-app-isolated-window.sh \
      "$(pwd)/target/debug/medorigin-desktop-d2-native-egui"

Observed on authorized Ubuntu 26.04 WSL2 / Rust1.97.1 / eframe0.36.0
on 2026-10-30: `D2_UNMODIFIED_NATIVE_GUI_ROOTLESS_NETNS_WINDOW_PASS_NOT_RELEASE`,
exit0. This is **real default binary** runtime evidence, separate from
the `examples/` wrapper's positive-control/negative-control socket tests.
The native product source contains NO networking API, so the default
binary does not deliberately attempt a socket connection in this smoke;
therefore a visible window and network namespace confinement **do not**
constitute packet-level proof of zero egress by every transitive process
or system service. No release, distribution, PHI or waiver is authorized.

## Windows native D2 synthetic UI Automation technical acceptance (NO RELEASE)

The separate source-controlled `tests/windows-native-uia-qualification.ps1` is a
real Windows 11 UI Automation test for a **running, unchanged, unpackaged
native D2 executable built from a pinned source commit**. This is a bounded
developer test and does **not** enable any clinical feature, access PHI,
add browser/IPC/network capabilities, install a service, configure a
firewall, or authorize release.

On an authorized foreground Windows developer session, build with pinned
Rust 1.97.1, launch the original native D2 executable, and supply its
current PID and the SHA-256 of the *actual executable bytes*:

```powershell
$exe = 'D:\path\to\target\debug\medorigin-desktop-d2-native-egui.exe'
$sha = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
$app = Start-Process -FilePath $exe -PassThru
powershell.exe -NoProfile -STA -File tests\windows-native-uia-qualification.ps1 `
  -AppPid $app.Id -ExpectedExeSha256 $sha
```

Only stop the process that this script's operator launched and authorized.
The test itself **never starts or kills apps**. It checks the reported
process executable name and byte SHA, visible window native handle/PID
and MedOrigin title prefix; the hidden `Winit Thread Event Target` window
is *not* mistaken for a second user window. Windows AccessKit exposes
the four fictional fixture selectors as **UIA Button + TogglePattern** and
the Verify control as **UIA Button + InvokePattern**. It uses these real
UIA actions, re-queries controls after every change, and requires the
exact expected 64-character SHA-256 to appear in the window's UIA **Text**
node after each fixture verification. It fails closed on absent/ambiguous
controls, unsupported patterns, a mismatch or a wrong executable SHA.

The script also takes a **single bounded snapshot** of the native process
and descendants, explicitly rejects any observed child named
`msedgewebview2.exe` or an established external TCP connection owned by
its process tree. This is an **observation**, not OS-enforced outbound
network denial; it cannot exclude transient TCP, DNS/UDP, IPv6 flows
outside the snapshot, network brokers, unexpected proxies or all process
lifetime events. It does not fix **D1 Windows WebView2 egress #662** or
approve replacing D1 with D2.

**Observed real Windows 11, 2026-10-31:** Windows x64 MSVC Rust 1.97.1,
source `62ea415826d93d5dcbfd6a52fa57c01f8fc537d4`, pinned
eframe 0.36.0; local native executable SHA-256
`d630f6845050b40c62496ee62396f3d08a710063b0af356ecbe1155ccf1c39ff`.
Native process produced an actual visible UIA window and exactly the
four fixture buttons plus Verify; real UIA **Toggle/Invoke and displayed
SHA-256 4/4 PASS**. A fresh cold launch repeated **4/4 PASS** with
`D2_WINDOWS_NATIVE_UIA_4_OF_4_PASS_NONPUBLISHING` exit0.
The bounded process-tree snapshot on each run found **1 descendant and
0 established external TCP**. Deliberately wrong PID999999 and a false
64-digit executable SHA both failed closed (exit1). The first test
draft incorrectly assumed InvokePattern for selectable labels; runtime
UIA explicitly exposes TogglePattern for those selectors, which was
corrected in the test source before committing. The first window probe
also revealed a hidden winit event target; the accepted test binds the
real visible window to the PID **and native window handle**.

GitHub hosted CI checks this script's PowerShell syntax and Windows
native source build/tests but intentionally **does not claim hosted
interactive UIA acceptance**. No signed production installer, package
or published artifact is created. Linux zbus transitive maintenance
#673, macOS spoken VoiceOver #676, independent release-security #603
and owner/ADR #574 remain separate NO-GO; #662 Windows D1 egress
remains OPEN. Protect frozen research roots and historical data.


## D2 native Rust FHIR-shaped fictional preview extension (2026-11-02)

The newest **Draft-only** D2 experiment imports the fixed, non-clinical D0 Rust JSON-envelope corpus from the independent D1 synthetic Bundle work (source reference Draft #840, exact SHA `0997e713941f90cb2ede7366521d20b3ac153224`). The D0 helper accepts twelve **compiled-in, fictional fixture IDs**: the original four Patient byte fixtures, two fake Observations, and six fake Bundles testing relative and Bundle-local URN references, missing Patient references, duplicate fullUrl, and unsupported Bundle type. It uses `serde_json` in memory for *limited* exact-field/graph checks and continues to hash original raw bytes. This does not validate real FHIR R4 profiles, clinical content, terminology, external references or arbitrary data, and there is no EHR or file importer.

The first four selectors and `Verify synthetic SHA-256` button remain in their original order and visible without expansion for the existing one-device Windows UIA and macOS AX/keyboard tests. The additional eight fiction-only cases live under an **initially collapsed** section after the original Verify button. Each local Rust verification requires the SHA contract, digest, exact byte length, fixed synthetic fixture identity, FHIR-envelope result status and negative permission flags to agree before showing a result; a negative sample is explicitly labeled as a negative *test*, not real patient/FHIR validity. No WebView2 or Tauri IPC is involved.

This is a new **native D2 product feasibility** capability, not a migration of the D1 application or a full product feature. The source-defined crate graph continues to include AccessKit for accessibility; the transitive Linux `zbus 5` maintenance notices (#673) are **not resolved**. Native OS packet-drop proof (#662), actual spoken VoiceOver (#676), independent security review (#603), owner release decisions (#574), and optional research advisories (#622) all remain NO-GO. Existing Mac AX tests have not been re-run on the expanded UI; only the four unchanged visible labels/button order has been preserved by source review. No release, tag, installer, PHI or protected-main merge.


## Native Windows UIAutomation regression for the 12-fixture FHIR preview (2026-11-02)

A new source-controlled `tests/windows-native-fhir-uia-qualification.ps1` verifies all eight newly added fictional Observation/Bundle cases by interacting with the **real locally built native eframe window** through Windows UIAutomation, then reading two distinct exact accessibility text nodes: the approved raw SHA-256 digest and expected limited FHIR envelope status. This complements, and does not replace, `tests/windows-native-uia-smoke.ps1`, which was re-run successfully for all original four Patient cases.

The GUI now renders SHA and FHIR status as separate text nodes so prior Window UIA/AX digest readers can still find the original SHA exactly. The new test requires a manually supplied binary SHA-256, refuses altered binaries before launch, and terminates only its own test app. Actual authorized Windows cold launches: original 4/4 PASS; new 8/8 PASS twice; deliberately wrong binary digest exit 1. See `evidence/d2-native-windows-uia-fhir-20261102.md` for exact receipt and limitations.

CI **parses the PowerShell source** on Windows and runs native Rust tests/Clippy on Windows and Linux but does **not** launch a graphical app in hosted runners. The new interface has **not** been replayed with Mac NSAccessibility/VoiceOver or independently audited for packet-level network egress. The inherited #662/#673/#676/#603/#574/#622 NO-GO blockers remain; this is never clinical FHIR R4 validation or release approval.


## Real macOS NSAccessibility — eight additional fictional FHIR cases (2026-11-02)

Source-controlled `tests/macos-native-fhir-ax-qualification.swift` extends the earlier four-case Mac AX/keyboard evidence to **all eight additional** native D2 fictional Observation and Bundle fixtures. On the user's actual authorized Apple Silicon Mac, the script opened the already built native application, expanded the initially collapsed section through `AXPress`, selected each fictional fixture, pressed Verify and read both exact synthetic SHA and exact fictional envelope status as **two separate AXStaticText nodes**. All eight passed twice on independent cold launches; the original four Mac AX actions and original four keyboard-only interactions also passed on the same new D2 source. The script requires an externally supplied exact binary SHA-256, verifies it against the live native executable with CryptoKit, and refuses mismatched hash or bogus PID. See `evidence/d2-macos-fhir-ax-8case-20261102.md`.

The hosted macOS job **only lints and typechecks** the new Swift test. The live test runs only in an authorized GUI session and does NOT constitute actual VoiceOver spoken announcements, multiple-device acceptance, OS packet/egress proof, FHIR R4/clinical validation, human security signoff or release approval. #676/#662/#673/#603/#622/#574 remain open NO-GO issues.


## Linux AT-SPI native GUI evidence (2026-11-02)

The source-controlled `tests/linux-native-fhir-atspi-qualification.py` is an **actual, fail-closed, nonpublishing** Linux native GUI acceptance test. On a disposable Ubuntu/Xvfb/D-Bus session it builds the pinned native Rust D2 executable, verifies exact binary SHA-256, interacts with real AT-SPI controls for four fictional Patient, two Observation and six Bundle cases, and matches separate exact accessible digest/status nodes. GitHub push/PR runs [41470264834](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41470264834) and [41470272426](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41470272426) demonstrated **12/12 genuine programmatic AT-SPI interactions** (not source-only tests). Source-bound root causes included a missing XKB X11 runtime shared library, a headless EWMH focus mismatch, and an unnamed AT-SPI frame whose identity must be established via its application + child controls. Report: `evidence/d2-linux-atspi-12case-20261102.md`.

This does **not** remediate #673 Linux zbus5 transitive RustSec maintenance, prove spoken VoiceOver or independent accessibility sign-off #676, establish actual D1 WebView2 OS packet confinement #662, fix frozen optional dependencies #622, replace human security review #603 or grant founder release permission #574. All remain NO-GO. No clinical FHIR R4 conformance, PHI, protected-main merge, installer, tag, or publication.


## Actual Linux keyboard-only native GUI acceptance (2026-11-02)

Draft #856 extends the real disposable Ubuntu/Xvfb/D-Bus AT-SPI test with an **independent keyboard-only** mode. The test uses genuine X11 XTest Tab/Shift+Tab/Space input on the pinned executable (never programmatic AT-SPI press), reads accessible focus state, and verifies distinct exact fictional SHA-256 and FHIR envelope status labels. All four original Patient examples and backward Shift+Tab navigation passed in two source-exact GitHub runs, alongside the previous 12/12 actual programmatic AT-SPI controls. The test also prevents fixture-switch/Verify redraw races by requiring the previous verified receipt to disappear before selecting the next one. Reproducible source/CI evidence: `evidence/d2-linux-x11-keyboard-20261102.md`.

The three AccessKit/zbus5 **unmaintained** notices (#673) are still open; the successful real keyboard/AT-SPI tests do not remove those dependencies or authorize a release. No clinical FHIR R4 conformance, PHI, actual spoken reader review, OS packet-confinement proof, human security sign-off, protected-main merge or publication.


## In-app verified fictional JSON preview (2026-11-02)

The native Rust app now has **Inspect fictional JSON (verified, read-only)**: a developer can view the *exact* original raw JSON bytes for nine compiled-in fictional Patient, Observation and Bundle samples (at most 2,048 bytes), only after in-process D0 SHA-256, source identity and limited FHIR-envelope status checks agree. Intentionally malformed UTF-8 and 32 KiB size-limit boundary tests cannot be previewed. The source is never parsed/reformatted for display: a fake negative Bundle with duplicate fullUrl stays byte-exact. Selecting a new sample, verifying again or encountering any mismatch clears stale preview text before rendering anything else. The control comes **after** the original four selectors and Verify button, preserving previously qualified Windows UIA / Mac AX / Linux AT-SPI keyboard sequences. No clipboard, file reader, EHR, clinical data, network endpoint or local persistence is introduced.

Actual Windows native UIAutomation on one authorized device found the real preview button, clicked and read exact raw fictional Patient JSON, rejected invalid UTF-8 without leaking stale text, and clicked/read exact fictional Bundle source bytes (**3/3 PASS**). The old four primary SHA selectors (**4/4**) and eight advanced Observation/Bundle selectors (**8/8**) were replayed and passed with the new native executable. The Ubuntu ephemeral Xvfb/AT-SPI qualification additionally runs a separate native preview interaction mode alongside its existing 12-case AT-SPI and keyboard-only cases; hosted results must be checked on the exact commit. Details and security limitations: `evidence/d2-fictional-raw-json-preview-20261102.md`.

This is fictional-only *developer inspection*, NOT full FHIR R4, a clinical validator or a production model platform. The existing #673 (unmaintained AccessKit/zbus5), #676 (spoken Mac VoiceOver/independent review), #662 (Windows WebView2 OS packet proof), #622/#603/#574 source/approval blockers remain NO-GO. No protected-main merge, installer, tag or release.


## Source-only D0/D2 fictional fixture catalog gate (2026-11-03)

The separate Python 3 standard-library audit `tests/verify_d2_fixture_catalog.py` checks **all 12 source-compiled fictional vector digests and byte lengths**, including six committed Bundle JSON files and the three intentionally invalid/boundary vectors. It also validates the nine permitted JSON previews, the exact synthetic envelope status labels and the D0 dispatch routes from each name to its original byte source (nine names, three paths each). Source file symlinks, changed D0 Rust declarations, new/missing catalog entries, mismatched length/SHA or unexpected statuses fail closed. This gate does not process user files.

From the `experiments/desktop-d2-native-egui/tests` directory, run:

```bash
python3 -m unittest discover -s . -p 'test_verify_d2_fixture_catalog*.py' -v
python3 verify_d2_fixture_catalog.py
```

The eleven source-only unit tests (eight negative helper cases and three temporary-tree integration cases) passed in an isolated Python environment, at the earlier GitHub HEAD, and a separate independent SHA-256 implementation matched **12/12 actual GitHub D0 source bytes** against D2's catalog. Six subsequent source-only mutation tests were added to the tree suite, bringing it to **17 authored test cases**. The new checks pin the three Rust boundary constructors and the D2 selector order. The full **17/17 source-only Python unit tests have now run and PASS** twice on Python 3.13.5, using three locally reproduced files whose Git blob hashes matched GitHub's exact PR #865 inputs. The earlier focused **6/6** boundary checks were an intermediate stage. See `evidence/d2-verified-17-python-source-tests-20261103.md` for verified input blob hashes, command, exact test scope and process exit 0. The **full-repository Python audit against an actual full D0/D2 checkout** and the integrated native Rust tests have **not** been executed on the current branch HEAD; only the exact source-only Python unit suite has passed. The source-only workflow will request these commands for future eligible PR changes in D0 fixtures or D2 catalog, but there is **no exact-head hosted CI PASS** yet. This checks frozen synthetic source provenance only, not network confinement, actual OS accessibility, clinical FHIR or release authorization.

## Independent fictional raw-byte SHA check (2026-11-03 integration)

In Draft #865, the native Rust GUI now independently computes SHA-256 over the **actual `raw_json.as_bytes()` returned for display or side-by-side comparison**, in addition to checking the existing D0 provider contract, length, synthetic-only metadata, and fixed fixture catalog. Both `preview_selected` and `verified_json_for` refuse any byte content with a mismatched digest; their existing failure paths clear stale raw/comparison content. The new D2 implementation uses the **existing locked `sha2 0.11.1` crate** already required by D0; no separate version or network client was introduced. It refuses raw text exceeding 2,048 bytes even when a claimed fixture length matches.

The Rust regression `fictional_preview_hash_checks_returned_bytes_not_only_provider_metadata` checks original fictional Patient source, same-length altered bytes, forged expected digest, oversized text, and all nine approved compiled fiction-only preview vectors. A separate local Python SHA-256 check confirmed that the fixed 57-byte Patient fixture hashes to `747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0`, while the same-length `synthetix` mutation hashes differently. **These source/hash checks are not a compiled Rust test PASS or native GUI acceptance.** This change has not yet been executed on an exact-head native Windows/Linux/macOS build; no hosted CI outcome is claimed.

This verifies integrity of **already built-in fictional raw preview bytes**, not PHI erasure, generic file-import safety, a trusted filesystem, operating-system egress confinement, full clinical FHIR R4, or release authorization. All preexisting NO-GO gates remain.

## Exact fictional JSON byte difference (2026-11-02)

The native D2 side-by-side comparison additionally shows a **zero-based first differing byte offset**, the length of the unchanged common byte suffix, and both exact source byte lengths. This is calculated only from the two separately SHA-256/envelope-verified, compiled-in fictional JSON texts (at most 2,048 bytes each). It never normalizes, reformats, imports, saves, copies, or sends data, and it does not interpret a changed byte as a clinical or semantic FHIR difference. The byte index deliberately counts UTF-8 bytes, not Unicode characters. A fresh Verify, changed selection, invalid second selection, or refused comparison clears the old byte summary along with the source comparison.

The independent Windows UIAutomation script `tests/windows-native-fictional-compare-uia.ps1` requires an exact executable SHA-256 and now checks the pinned Patient-vs-Observation byte summary and its removal on fail-closed or stale comparison. Rust unit tests cover identical bytes, insertion, Unicode byte offsets and prefix-only changes. See `evidence/d2-fictional-byte-difference-20261102.md` for exact local results and remaining qualification limits. This is source-only, synthetic developer functionality: release remains NO-GO under #574/#603/#622/#662/#673/#676.

## Bounded fictional first-difference HEX context (2026-11-02)

The native comparison shows at most eight original UTF-8 bytes before and after the first difference, separately for each independently verified fixed fictional JSON. This is a byte-level developer aid, not JSON/FHIR semantic comparison. No arbitrary files, PHI, clipboard, persistence or network are involved. Stale results clear with selection and verification. Release remains NO-GO.

## Native source-bound fictional relationships (2026-11-04, Slice 7)

D2 now offers **Inspect verified fictional relationships (read-only)** for exactly three compiled-in, positive-test fictional D0 resources: `observation-minimal`, `bundle-valid`, and `bundle-linked`. The native Rust UI rechecks exact D0 source SHA-256 and the bounded FHIR-shaped envelope, then displays only reviewed JSON Pointers, membership/reference targets, source byte counts, and fixed SHA-256. Invalid, changed or unreviewed inputs fail closed; selection changes and re-verification clear stale results.

**No event dates exist in this D0 corpus, so the native UI explicitly refuses to infer a medical timeline.** This feature adds no new dependencies, browser, Python service, network, arbitrary file inputs, patient data or FHIR R4/clinical validity claims. Existing native Windows UIA scripts and the new source-bound relationship UIA are qualified in [the Slice 7 evidence](evidence/d2-native-fictional-relations-20261104.md). Prior D2 release/security blockers remain NO-GO.

## Cross-platform portable synthetic builds (Windows / macOS / Linux)

A source-pinned, strictly nonpublishing packaging workflow now builds **native portable developer-preview archives** across Windows x86-64, macOS Apple Silicon (and host-supported Intel), and Linux x86-64. It packages the verified executable with the original Apache-2.0 license, upstream notice, explicit *NOT FOR PATIENT DATA* instructions, and a SHA-256 source manifest. It does **not** make this D2 experiment a finished healthcare product, trusted offline sandbox, signed installer, notarized DMG, or app-store release.

Read [Cross-platform preview instructions](docs/CROSS_PLATFORM_PREVIEW.md). Linux users may need the Ubuntu runtime package `libxkbcommon-x11-0`; CI checks an actual X11 window under Xvfb. The accompanying GitHub Actions workflow uploads only private, short-lived synthetic artifacts; there is no publish or release action. Full Core/Workspace functionality and medical-security gates remain open.

## Interactive encrypted fictional Core explorer (Windows developer-only)

A deliberately opt-in Windows **developer launcher** now opens the native GUI after a genuine, exact-source-pinned fictional AES-GCM Core import/reopen/readback under a kill-on-close worker Job Object. The native app itself still does not start Core or authenticate stdin. Its recovered-only resource browser supports type facets, incoming/outgoing references, bounded multi-step Back and Clear. See [Windows interactive fictional explorer](docs/WINDOWS_INTERACTIVE_ENCRYPTED_CORE_EXPLORER_20261104.md) for the explicit invocation, tested Windows results, strict nonclinical scope and remaining NO-GO release/security gates. This is **not** an installable healthcare product or a PHI workflow.

## Windows installed-Wheel encrypted fictional Core interactive GUI

Windows now has a separate explicit nonpublishing **installed-Wheel** native GUI developer route using two offline-built, exact source-attested pure-Python Core/Workspace packages (290 source files), isolated Python `-I -S -B` worker under Windows Job Object, actual synthetic AES-GCM close/reopen/audit/decrypted-readback, and live D2 native UI. The native GUI itself never starts Python. The source-backed Wheel-to-GUI route includes actual Windows UIA verification of resource facets, incoming links and Back. See [Windows installed-Wheel interactive GUI evidence](docs/WINDOWS_INSTALLED_WHEELS_INTERACTIVE_ENCRYPTED_CORE_20261104.md) for invocation, pinned Windows-only dev QA Wheels, limitations, and explicit NO-GO release gates; installed cryptography native code and OS network confinement remain unverified.

## Private Windows portable fictional Core developer kit (NO Git required at runtime)

A new two-stage developer-only workflow prepares a source-attested 290-file installed Python Core/Workspace tree **offline** from exact approved Git/Wheel/package source, alongside the actual native GUI and approved source-bounded test components. The prepared native D2 kit can then launch the genuine fixed fictional AES-GCM Core readback **without any Git checkout, Wheels or build tools**. The real Windows GUI is tested with both unattended owned-window closing and native UIAutomation navigation. Python/crypto system dependencies remain external; the bundle manifest is **not cryptographically signed** and the Windows Job Object does **not** confine network egress. Strictly nonclinical, no PHI, signing or publishing. See [portable developer kit evidence](docs/WINDOWS_PRIVATE_PORTABLE_FICTIONAL_CORE_BUNDLE_20261104.md).

## Per-launch fictional Core session MAC for portable Windows Desktop

The portable fictional Windows D2 launcher now defaults to a **fresh per-GUI-process 128-bit nonce and 256-bit HMAC-SHA256 secret** over the exact 1,164-byte source-recovered imaginary encrypted Core report. The native Rust GUI accepts the envelope only under an explicit `--synthetic-encrypted-readback-session-stdin` flag and refuses altered content or stale/foreign nonce/key before showing the window. The real Windows automated UIA traversal passes using this mode, as do six actual Windows no-window invalid-frame/replay process refusals. This is **NOT authenticated production IPC, key custody, signed distribution, medical safety, or OS egress isolation**; secrets originate from the private launcher environment. The old exact static readback mode remains for independent historical synthetic QA only. See [private D2 session-MAC evidence](docs/WINDOWS_FICTIONAL_D2_PER_LAUNCH_SESSION_MAC_20261104.md).

## Native searchable recovered fictional Core worklist

The native Rust encrypted Core explorer now supports **ephemeral in-app case-insensitive search of source-recovered fictional resource type, ID and reference**, alongside its existing All/Observation/Patient/Encounter filters. Search input is strictly bounded to one short ASCII identity token, never raw clinical content or a remote lookup; no search history is saved. Search changes clear selection/Back history, invalid input fails closed, and verified source links reset the filter and search so their targets remain visible. The real Windows UIAutomation flow clicks and checks the new search controls before its existing resource-relationship journey. Strictly synthetic-only. See [search UX verification and limitations](docs/WINDOWS_RECOVERED_FICTIONAL_CORE_SEARCH_20261104.md).

## Verified fictional relationship inspector and clickable history

The read-only source-recovered encrypted Core explorer now shows directly verified outgoing/incoming reference counts and **clickable breadcrumbs** for previous visited Observation/Encounter/Patient fictional identities. A breadcrumb jump truncates intervening history, restores a valid source-derived record, and clears search/type filters. Invented, stale or malformed history fails closed; no arbitrary patient input or remote lookup is enabled. Windows native UIAutomation covers the actual breadcrumb click and relation-count UI. See [inspector and history qualification](docs/WINDOWS_RECOVERED_FICTIONAL_CORE_INSPECTOR_BREADCRUMBS_20261104.md). Nonclinical QA only; not a release.

## Opt-in persistent encrypted fictional Core Workspace (Windows developer QA only)

The Windows desktop's **portable fictional Core launcher** can now cold-reopen an actual locally persistent, real Core AES-256-GCM SQLite test Workspace created in an earlier process. A **fixed, test-only root key and external audit anchor** are stored under **Windows user-scope DPAPI**, not plaintext. The private Core worker verifies and reads back the same three *imaginary* FHIR-shaped source records from disk, then supplies an **independently SHA-pinned redacted 1215-byte persistent projection** to native Rust D2 over a fresh owner-bound HMAC session. The GUI truthfully distinguishes `Persistent fictional QA vault reopened: true` from the pre-existing ephemeral removed-store mode; all real native Windows search, graph relationships and breadcrumb UIA flows work with both. The default ephemeral mode remains unchanged. This **does not implement a production key provider or authorize PHI**. See [actual cold-reopen, Windows DPAPI and portable GUI QA](docs/WINDOWS_FICTIONAL_PERSISTENT_DPAPI_WORKSPACE_20261104.md).

## First-run persistent fictional Workspace demo in native Windows D2

The private offline Windows D2 portable launcher now supports **`--ensure-fictional-demo`** with an explicitly supplied fixed-name `--fictional-persistent-qa-root`: on its **first** run only it creates the source-verified three-record imaginary Core AES-256-GCM SQLite Workspace with DPAPI-wrapped test key and source/audit anchor inside a Windows Job Object-supervised child, then a **separate** Core child cold-reopens that same encrypted store and sends only exact reviewed redacted resource identities to native Rust D2 over a fresh per-launch HMAC session. Repeating the **same command** reopens without regenerating or overwriting the vault. A damaged existing key/anchor fails closed; it is never automatically reset. The old default ephemeral mode still works. Real Windows UIA has verified both first and second launches and a corrupt existing-vault refusal. This is strictly **fictional developer QA**, not a real-patient first-run product or production protected-key provider. See [first-run persistent demo workflow and evidence](docs/WINDOWS_FICTIONAL_FIRST_RUN_DESKTOP_20261104.md).

## Native Workspace home and graph-verified fictional patient context

The actual encrypted Core source-recovered worklist now has a top-level **Workspace home** showing whether its exact nonclinical fixture came from a cold-reopened persistent test-only AES-GCM vault or a reopened/deleted ephemeral vault, along with reviewed audit/reopen evidence. A one-tap **fictional patient context** action verifies the exact source graph Patient ← Observation/Encounter, shows the two source-linked fictional members and lets the user open each and navigate Back. Forged, ambiguous or non-source-derived edges fail closed. All historical developer controls, resource filters, search and history remain operational; actual Windows native UI Automation verifies the home, patient view and member navigation. **This is not a real-patient clinical chart or production readiness claim.** See [native Workspace home and fictional patient-context proof](docs/WINDOWS_NATIVE_FICTIONAL_PATIENT_CONTEXT_WORKSPACE_HOME_20261104.md).

## Session-only fictional source resource walkthrough

The native Workspace home now offers a usable, source-derived **fictional visit walkthrough** for exactly three recovered imaginary Core identities in the sequence Patient → Encounter → Observation. `Open next unvisited fictional identity`, `Mark fictional identity visited (demo only)`, and `Reset fictional walkthrough (session only)` update a three-step progress count without modifying the real encrypted Core test Workspace or recording a clinical sign-off. Both separate SHA-verified ephemeral and DPAPI-persisted fictional readback projections are supported; changed graphs/invalid links/stale indices fail closed and clear the demonstration marks. Real Windows Core-to-native GUI and Windows UIAutomation now drive the full three-step workflow. **These are not physician reviews, approvals, encounter completion or production medical records.** See [native fictional resource walkthrough implementation and qualification](docs/NATIVE_FICTIONAL_RESOURCE_WALKTHROUGH_20261104.md).

## One-click Windows native fictional Core Desktop (owner-local private QA only)

A separate **one-time, source-only Windows installer** now creates a fixed current-user `Start-MedOrigin-Fictional-Desktop.cmd` shortcut bound to the exact SHA-256-verified Windows Python runtime and existing **290-source-file-attested offline private portable kit**. Double-clicking the owner-local shortcut invokes the **real native Rust GUI** over a source-verified AES-256-GCM fixed fictional Core Workspace, initializes it only if absent and cold-reopens it on later runs without overwriting the user-DPAPI-protected demo key and audit anchor. Actual Windows `cmd.exe` first/second launch with owner-window UIAutomation PASS, same key/anchor digest on second launch, corrupted protected anchor/portable source both refuse with EXIT2. The generated shortcut and demo vault were verified only in a task-owned local test folder, never committed or treated as a release. There is no production key provider, authenticated clinical EHR connection or real patient processing. See [private one-click Windows fictional Core Desktop workflow and evidence](docs/WINDOWS_PRIVATE_ONE_CLICK_FICTIONAL_DESKTOP_20261105.md).

## Focused native fictional Workspace screen (separate from developer evidence)

The native Rust GUI now has a dedicated, opt-in **focused fictional Workspace** screen launched from the verified encrypted Core Workspace home. It makes the exact source-derived Patient, Encounter and Observation resource navigation, Back, session-only visits and source/audit disclosures easy to access without scrolling through experimental fixture controls. A single action returns to the unchanged developer evidence view; invalid/forged resource graph or clearing the source fails closed and resets the view. Windows real compiled UIAutomation and actual AES-GCM Core-to-GUI qualification have passed on the new source; macOS Accessibility and hosted GitHub checks are separately verified. This **remains a strictly fictional QA interface, not a production EHR or clinical authorization**. See [focused native fictional Workspace implementation and evidence](docs/NATIVE_FOCUSED_FICTIONAL_WORKSPACE_20261105.md).

## Focused Workspace source-verified resource browser

The focused native Rust Workspace now includes a **source-derived fictional resource list**, with preset type and identity keyword filters, exact 3/1/0 worklist counts, a genuine empty-result state and one-click details for the visible Patient/Encounter/Observation identities. Filters use the existing trusted Core projection and conservative search/selection checks, clear stale selection/history, and cannot import patient data or widen the source gate. Existing direct patient-context navigation, Back, session visits and the developer evidence screen still work. Windows real GUI UIAutomation and actual Core AES-256-GCM-to-GUI qualification cover the new browser; Mac is separately checked. This remains a private three-identity **fictional QA workflow only**, not clinical readiness. [Focused Core browser implementation and validation](docs/FOCUSED_CORE_SOURCE_BROWSER_20261105.md).

## Direct-to-Workspace native Windows one-click fictional startup

The real Windows source-attested 290-file offline Core+Workspace portable launcher now supports an **explicit focused-first native GUI startup**. The normal owner-local Start-MedOrigin-Fictional-Desktop.cmd generated by the private installer opens the already source-verified imaginary Core Workspace directly in the focused source browser, instead of displaying developer evidence first; the original developer mode and all UIA controls remain available via Return to developer evidence. Both new focused one-shot and HMAC session startup switches use the identical restrictive fake Core source gate, bounded stdin, and (for session mode) per-launch nonce/MAC; no clinical or patient import is added. Actual Windows one-click CMD → reviewed Python Core → real native GUI first-screen UIAutomation PASS, two independent DPAPI-persisted fictional vault cold-reopen HMAC runs PASS, and legacy/focused negative HMAC spoof/replay tests PASS. Source-only Mac focused startup and hosted GitHub checks are qualified separately. **Strictly imaginary records and a private QA shortcut, NOT a real patient EHR, licensed clinical product or signed release.** See [real direct-to-Workspace startup proof](docs/FOCUSED_CORE_WORKSPACE_DIRECT_STARTUP_20261105.md).

## Interactive source-linked graph inside focused Workspace

The fictional, source-verified native Workspace now exposes clickable **incoming and outgoing FHIR-shaped references**, plus a bounded **16-step verified navigation trail**, Back along the actual history, and source-linked ancestor breadcrumb jumps. Resource IDs, edge names and destinations come solely from the exact source-approved encrypted Core readback; no separate patient database or clinical timeline is inferred. Windows actual Rust UIAutomation and real source-pinned Core AES-256-GCM→native GUI tests traverse the graph and return to the focused filtered browser; actual Mac AX and hosted CI are independently checked. This remains a **fixed three-imaginary-record, nonclinical QA** view, not a general clinical chart or a production FHIR resolver. See [focused source graph navigation proof](docs/FOCUSED_SOURCE_GRAPH_NAVIGATION_20261105.md).

## Multi-patient fictional FHIR Bundle browser (bounded, structural only)

A separate opt-in **real native Rust Workspace** now supports a generated **up-to-48-resource / 16-fake-patient** FHIR-shaped Bundle instead of only three immutable source-compiled identifiers. It groups imaginary Patient/Encounter/Observation identities by patient, provides type facets, source-local incoming/outgoing references, Back and a 24-step bounded navigation history, and fails closed on cross-patient, missing/remote references, real clinical fields, duplicate IDs, excessive size or disallowed JSON. The included standard-library generator supplies eight fictional resources for two pretend patients or 48 for 16; the reviewer-exercised Windows GUI actually navigates across patient groups. This is strictly **a separate unencrypted synthetic structural demo CLI** (`--synthetic-multipatient-bundle-stdin`), not a general clinical import or production FHIR R4 proof. The original AES-GCM Core/HMAC readback workflow remains independently unchanged. See [bounded multi-patient FHIR-shaped workspace, QA and explicit limitations](docs/NATIVE_MULTIPATIENT_STRUCTURAL_BUNDLE_20261105.md).
