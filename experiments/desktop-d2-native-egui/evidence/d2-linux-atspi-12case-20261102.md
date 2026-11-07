# D2 Linux AT-SPI 12-case native GUI — exact-source qualification (2026-11-02)

**Scope:** nonpublishing fictional developer preview, no PHI, EHR, clinical FHIR R4 conformance, or arbitrary file/network data. This is one **disposable Ubuntu 24.04 GitHub runner**, not a spoken screen-reader workflow or an independent physical Linux device review.

**Source:** stacked private Draft PR #855 on private Draft #854, originally exact qualified source HEAD `5fc1f12c6a68c3442b659f7ba2d7816f9847cf27`. All code is unmerged Draft, and protected main has not changed.

## Genuine positive evidence

Source-controlled native test `tests/linux-native-fhir-atspi-qualification.py` and workflow `.github/workflows/medorigin-d2-linux-atspi-gui.yml` build the **real pinned Rust 1.97.1 D2 executable**, verify its SHA-256, launch it only inside a disposable `Xvfb` + `fluxbox` + `dbus-run-session`, and interact with actual AT-SPI controls using system `pyatspi`.

- **GitHub push exact-head Actions:** [41470264834](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41470264834) — `linux-atspi-native-gui` **SUCCESS**; actual `LINUX_D2_ATSPI_12_OF_12_PASS_NONPUBLISHING` in logs; real application process/GUI/X11/D-Bus/AT-SPI.
- **GitHub PR exact-head Actions:** [41470272426](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41470272426) — same native Linux AT-SPI job **SUCCESS**. Source test is not merely static code parsing.
- **Cases actually acted on:** four fixed fictional Patient examples, two fictional Observations and six fictional Bundles; controls selected through the exposed AT-SPI Action; `Verify synthetic SHA-256` pressed; two **distinct** exact accessible text nodes required for trusted digest and limited fictional FHIR envelope status. A deliberately negative fixture returning `INVALID_REFERENCE`, `INVALID_BUNDLE_TYPE`, `DUPLICATE_ENTRY`, `INVALID_UTF8` or `RESOURCE_TOO_LARGE` is a correctly identified **negative test**, not a FHIR-valid patient.
- **Local Windows source harness:** 7/7 pure Python tests PASS; Ruff lint + format PASS. These verify rejection of wrong executable hash, missing executable, fatal process exit preservation, retry of transient AT-SPI initialization, an exact app identity + unnamed frame, and ambiguous/missing UI identity fail closed. These unit tests do not substitute for actual Linux GUI; positive evidence above uses real AT-SPI.
- **Separate native core matrix:** source branch also triggers locked D0/D2 Rust tests and Clippy on Windows and Ubuntu. Recheck its final exact-head status separately; native compilation alone never counted as AT-SPI qualification.

## Real defects found and source-bound repairs

1. Initial runner built Rust successfully but the D2 app **panicked with exit code 101** while loading the X11 dynamic keyboard library. Installed Ubuntu `libxkbcommon-x11-0` explicitly, confirmed the `libxkbcommon-x11.so.0` loader in the isolated runner. This is runtime packaging, not a source application security vulnerability.
2. `xdotool windowactivate --sync` could not obtain EWMH focus inside the disposable window manager. Switched to X11 core `windowfocus --sync` and required successful focusing. Actual hosted logs printed `DISPOSABLE_X11_WINDOW_FOCUSED`.
3. Source test incorrectly expected the **frame** to be named `MedOrigin Native Rust`. Real Linux AccessKit exposes an `application` named `medorigin-desktop-d2-native-egui`, an **unnamed frame**, and a separate child label `MedOrigin — Native Rust Experiment`. This caused a false-negative AT-SPI timeout even though the tree contained the expected controls. Replaced guessing by unique exact app identity plus correct child title and two original controls. Added negative unit tests to refuse missing or duplicate frames.
4. Source test previously converted real application crashes to timeouts; distinct fatal-error type now preserves an immediate fail-closed exit with the true stderr. A transient startup can still retry within a bounded deadline.

All mutations were confined to the private Draft branch and disposable GitHub runner; no user's live Linux bus, WFP/ETW, system firewall, audit settings, data, installed software or clinical state was modified. No test failures were skipped to achieve the green result.

## Explicit residual release NO-GO

**#673 remains OPEN:** the Linux AccessKit transitive `zbus 5` / `zvariant 5` / `zbus_names 4` RustSec unmaintained notices remain. Successfully using AT-SPI **does not remediate** the maintenance debt or constitute an independently accepted release risk. Any upstream-compatible zbus 6 migration must be separately audited.

**#676 remains OPEN:** actual spoken macOS VoiceOver announcements, independent reviewer, and second-device assessment are not established by this Linux programmatic AT-SPI test. **#662 remains BLOCKED** for real Windows WebView2 broker/descendant DNS/TCP/UDP packet-level confinement; native eframe's lack of WebView does not close D1 gates. **#622/#603/#574** optional frozen research dependency advisories, human security review, owner ADR package/version/signing and explicit release authorization remain unresolved.

No protected-main merge, tag, installer, public release, PyPI upload, PHI, patient processing, or clinical claim was made.
