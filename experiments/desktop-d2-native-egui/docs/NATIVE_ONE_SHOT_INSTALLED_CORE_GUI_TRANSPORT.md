# Real installed Python Core → source-bound D2 native GUI (one-shot stdin) — 2026-11-04

**Private synthetic-only developer milestone. This is the FIRST observed local dynamic Core-to-GUI data path, NOT a clinical workflow, GUI-controlled Python worker, authenticated transport, installed release, approved signer or PHI data path.**

## New functional native contract

On ordinary launch, the actual D2 Rust/egui desktop still uses ONLY its fixed bundled fictional sources. It **does not read stdin**, create a subprocess or socket, open a file, accept a patient record, use a browser engine or connect to EHR. All original native fixture/provenance/workspace controls remain.

On the explicit command-line switch `--synthetic-core-stdin` **and no other flags**, D2 instead reads **at most 2049 bytes** from a caller-supplied finite pipe, refuses empty/overlong/malformed/duplicate/modified/unknown/"valid" data and admits only exact canonical report bytes matching one of **two previously source-reviewed embedded Python Core synthetic reports**. The actual Rust core_provenance admission function checks the nine-field canonical JSON, fixed created_at, fixed source input hash, error/warning status `not_validated` and exact SHA-256 of bundled bytes. All other report data fails before any GUI opens; no clinician/user file or custom FHIR input is permitted.

An admitted external report starts the **existing** accessible Core provenance panel in the open state with its SHA, `Core status: not_validated`, `FHIR R4 NOT validated` warning and a separate explicit text: **"One-shot external stdin synthetic Core report accepted (exact source hash). GUI does not authenticate its origin or freshness."** Other synthetic actions/Escape/Clear erase this one-shot view and its external marker; this is not secure RAM zeroization. The mode does **not** change the trusted artifact supply chain or attest who provided stdin; the canonical allowed reports are deterministic, not authenticated with a cryptographic signature.

No new Cargo package, native source file, network/HTTP dependency, `std::process` launcher, file reader, IPC server, telemetry, EHR adapter or production binary capability is added. The exact dependency/source guard for D2 still passes. The process that runs Python and sources the report is the **independent, user-directed, source-attested Mac QA harness**, not the GUI.

## End-to-end execution actually observed

Mac Apple Silicon macOS 26.6.2, authorized real native window and AX:
1. Existing QA Core source checkpoint `ad0c62b4366789f5c7e41fc601bb6d0f9d640873`; offline deterministic installed `medscale==0.3.0` Wheel SHA-256 `4f3a66c9657c8040832970fdffcaa0d2bf15c74c79ae76b17566fe573c9536c2`, **250/250 package source files exactly verified**, plus Wheel and installed RECORD metadata.
2. Explicit disposable private `uv` venv, CPython 3.11.15 SHA `e3938f2a272dafdc33f3dd12b093dfc85354629476cb97a7d7d4a7201b8482dd`. Real macOS Seatbelt deny-default policy with actual loopback TCP OS EPERM rejection and sibling filesystem write denial **after unconfined positive controls**, then Python `-I -S -B` import of only verified installed package path; source checkout is NOT added to runtime imports.
3. For exactly two synthetic Core inputs, the actual installed `medscale.cli.fhir.main` returns **exit 2**, canonical report status `not_validated`, saved report equal to stdout. The QA harness independently verifies exact report content and injects those bytes via finite stdin into the **real locally compiled D2 native application** with the explicit `--synthetic-core-stdin` switch. All executable bytes and SHA pins are checked before and after.
4. The source-controlled `tests/macos-installed-core-stdin-live-ax-qualification.swift` observes the real process-specific native AX window and the exact report SHA, status, FHIR disclaimer, and external-input provenance limitation. Each GUI process is separately cleaned up by its own QA harness after the test. No user file dialog, online provider or PHI is encountered.

Locally built actual D2 GUI Mach-O SHA-256: `7226b19c6e97f586dbe96b35af715d2b7b1b76e3f2489a37ab36726d105a7a44`. Observed acceptance output:
```
INSTALLED_WHEEL_SANDBOXED_CORE_REAL_NATIVE_GUI_CASE_PASS known
INSTALLED_WHEEL_SANDBOXED_CORE_REAL_NATIVE_GUI_CASE_PASS unknown
D2_INSTALLED_SANDBOXED_CORE_TO_ACTUAL_NATIVE_GUI_2_OF_2_PASS_NOT_CLINICAL
```

New main-binary source tests cover default stdin non-consumption, opt-in two known canonical reports, malformed/forged/over-limit denial and unrecognized CLI flags. D2 Rust unit and browserless guard suite, fmt and Clippy `-D warnings` pass. Hosted Windows/Ubuntu CI runs only Rust and source-adversarial tests (NOT installed Mac Python/GUI AX). Repro in Mac QA runner (independently pinned local executable hashes):
```sh
cd experiments/desktop-d2-native-egui
cargo +1.97.1 build --locked --offline
python3 scripts/qualify_installed_core_into_native_gui.py \
 --core-source /tmp/medorigin-d2-installed-core-qa/core-src \
 --wheel /tmp/medorigin-d2-installed-core-qa/wheel/medscale-0.3.0-py3-none-any.whl \
 --venv /tmp/medorigin-d2-installed-core-qa/venv \
 --venv-python /tmp/medorigin-d2-installed-core-qa/venv/bin/python3.11 \
 --python-sha256 e3938f2a272dafdc33f3dd12b093dfc85354629476cb97a7d7d4a7201b8482dd \
 --d2-gui /absolute/path/to/compiled/medorigin-desktop-d2-native-egui \
 --d2-gui-sha256 7226b19c6e97f586dbe96b35af715d2b7b1b76e3f2489a37ab36726d105a7a44
```

## Unresolved production gates

**The GUI still cannot independently launch, supervise, or terminate Core**: only an external local QA harness starts the installed sandboxed Core, and the GUI admits at most one canonical source-fixed synthetic report from stdin. Neither the GUI nor stdin can authenticate the **origin/freshness** of reports; a known same-byte synthetic report is repeatable. A true patient-grade bridge needs reviewed installed-wheel/interpreter trust across macOS/Windows/Linux, restricted child-process launch under OS-native policy, child identity and lifetime supervision, encrypted authenticated IPC, no-PHI leakage, complete OS-enforced packet/DNS/UDP denial and descendant confinement, clinical FHIR R4 validator/terminology/profiles, actual user authentication/RBAC/consent, encrypted workspace with OS keys/backup/recovery, independent security and medical qualification, and explicit owner release authority. macOS `sandbox-exec` has deprecated semantics and broad read allowances: this synthetic-only QA does NOT prove patient privacy. Keep #574/#603/#622/#662/#673/#676 and open dependency alerts NO-GO.

No protected main merge, public installer, signing, publication, clinical claims, EHR records or real patient data are authorized by this work.

## Regression and instability disclosure

The previous normal-launch, disposable **ad-hoc signed App Sandbox** D2 GUI tests were re-executed on the new source binary without passing the stdin switch: first cold start failed **only at the fourth primary AX fixture** (`patient-exact-limit` hash AX node not read); the other first three primary controls passed. A second independent native cold start passed **4/4 original AX, 4/4 real keyboard Tab/Shift+Tab/Space, 2/2 embedded Core AX, 4/4 fictional Workspace AX**, exit 0. This is an observed **intermittent accessibility test instability**, not a justified permanent waiver or independent spoken VoiceOver certification; #676 stays unresolved. The **new one-shot Core→GUI** test separately passed both actual installed Core cases using AX twice (including final exact binary SHA shown above).

## Real Windows 11 native GUI one-shot stdin acceptance (separate from installed Mac Core)

On the authorized Windows 11 desktop, an isolated private sparse checkout of the **same D2 functional Rust sources** at `56931026e7a59e3732985b3174cfe93f6d391d2c` (parent version of this PR, subsequent change is only Windows QA script/source tests/docs) built from pinned offline Rust 1.97.1 with actual native unit/source tests PASS. Windows native executable SHA-256: `e6c101f4f95c0ce682d695b8d9ab314f1ba2ffdbd722191d81878b0a78de1c49`.

The reviewed `tests/windows-native-core-stdin-uia.ps1` was retrieved from this private branch and checked against exact Git blob before running. It validates native EXE SHA before/after, two source-controlled report JSON file SHAs, then launches each Windows GUI with `--synthetic-core-stdin`, pipes finite exact synthetic Core bytes, and checks **real PID-specific native Windows UIAutomation** for both exact source report SHA-256 labels, `Core status: not_validated`, `FHIR R4 NOT validated` and the external-origin-not-authenticated disclosure. It independently sends forged clinical-valid-looking data and requires process exit **nonzero** before GUI acceptance. Observed after fixing an initial **test-harness-only** PowerShell reserved-variable `$PID` collision:

```
D2_WINDOWS_ONE_SHOT_CORE_STDIN_GUI_SOURCE_REPORT_PASS known
D2_WINDOWS_ONE_SHOT_CORE_STDIN_GUI_SOURCE_REPORT_PASS negative
D2_WINDOWS_ONE_SHOT_CORE_STDIN_FORGED_VALID_REFUSED
D2_WINDOWS_ONE_SHOT_CORE_STDIN_NATIVE_UIA_2_OF_2_PASS_NOT_CLINICAL
WINDOWS_STDIN_UIA_EXIT:0
```

Existing Windows primary native UIA controls **4/4 PASS**, exit 0 at the same actual executable SHA. This verifies the **Windows stdin-to-native-GUI acceptance**, NOT installation or sandbox confinement of Python Core on Windows. Windows report bytes are previously source-pinned synthetic fixtures in this test; the actual **fresh installed Python Core invocation** was performed separately on the authorized Mac and in the Mac end-to-end AX GUI qualification above. Do not combine the two into a claim that the Windows GUI launched an installed Python Core or that Windows outbound network, DLL loader or subprocess containment are solved.
