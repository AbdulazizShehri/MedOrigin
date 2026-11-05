# MedOrigin D2 — private Windows single-EXE user setup

Status: PRIVATE, UNSIGNED, FICTIONAL-ONLY, UNPUBLISHED. This is an engineering path toward direct downloads without an app store. It is not a patient, clinician, production or clinical installer.

## Implemented

Windows IExpress, which is built into Windows 11, generates one self-extracting MedOrigin-Synthetic-Private-Setup-<source-hash>.exe. There is no third-party packaging product, cloud signing key, download, administrator elevation or Windows Store dependency in the LOCAL developer packaging step.

A source-controlled Python builder takes only a canonical ZIP produced by package_preview.py and verified by verify_preview.py. It checks the exact source HEAD and archive name, negative clinical and release flags, binary PE architecture, all five source-reviewed files, legally required notices, byte lengths and both independently pinned SHA-256 digests.

The IExpress installer contains only the five reviewed files, one hash-pinned Windows PowerShell 5.1 installation script and a fixed launcher command. On opt-in invocation, the script installs only into the current user's LOCALAPPDATA/MedOrigin-D2-Private-Developer-QA/InstalledPreview path. It creates Start Menu shortcuts for launch and removal. It does not add network services, telemetry, registry, scheduled tasks, elevation, auto updates, model loading, EHR access, real patient inputs or arbitrary file selection.

All installed files are checked against the SHA-256 values pinned at builder time. The program source commit and negative release flags are also checked. Existing installations and Start Menu links are not intentionally overwritten. The installer refuses reparse points and symlinked ancestors. It stages all files before moving them into place, creates temporary unique shortcut names before committing user-visible links and rolls back only its owned additions.

The installed PowerShell script supports Install, Verify and Uninstall actions. Uninstall is permitted only when called from its fixed installed directory, after validating all known files and both shortcut targets. Removal while the native app is running is denied. Other profile or workspace data is never deleted.

## Windows reputation and important limitations

IExpress Setup EXEs are UNSIGNED. They can trigger Microsoft Defender SmartScreen and an Unknown publisher warning when downloaded from the internet. An unsigned IExpress wrapper cannot solve publishing identity, Windows reputation, a code-signing certificate, polished production installer UX, Add or Remove Programs registration, secure automatic updates or clinical validation. Do not bypass those system protections for patient use or publish this engineering setup.

The D2 binary is an educational synthetic-only Rust/eGUI preview, not the clinical product. Source-level network restrictions are not an independent OS packet-isolation guarantee. No patient data, model, EHR connection or clinical processing is authorized.

## Source and acceptance commands

Use the reviewed Windows x64 checkout and already independently reviewed binary. First run package_preview.py with --binary, --output and --target windows-x86_64. Verify the resulting exact source-hash ZIP with verify_preview.py. Then call build_windows_private_user_setup.py with --archive, --repo, --output, --archive-sha256 and --native-sha256. The output directory must not already exist. The resulting unsigned EXE remains private and must not be uploaded.

For physical QA, run qualify_windows_private_user_setup.py with --setup, --source, --scratch, --binary-sha256 and optionally --real-gui. The disposable QA directory name must begin with private-installer-qa-. This script redirects both LOCALAPPDATA and APPDATA to task-owned mock Windows profile locations. It launches the genuine self-extracting setup, verifies the installed native binary and Start Menu shortcuts, optionally drives real GUI UIAutomation on the INSTALLED binary, alters a pinned non-executable README to establish fail-closed verification, restores it, verifies again, uninstalls and checks an unrelated sentinel survived. It never touches the normal user's actual Start Menu or installation path.

Source-only test_build_windows_private_user_setup.py exercises wrong archive and binary digests, modified source notices, extra and traversal archive entries, unsafe SED paths and shell metacharacters, overwrite refusal, malformed templates, strict source-pin rendering and PowerShell parsing. GitHub hosted CI should run only these source tests, never a physical installer on a runner.

## Real owner Windows result, November 6 2026

Initial exact parent source commit: dfbdc0947044d47ab007f4ead9332a8039cc640c. Real compiled native Windows EXE SHA-256: a1f81ed70fa9e1c88548400d9ceb5f3e00fd4839168188d029c6bdf4f9f03de7. Source-canonical synthetic ZIP SHA-256: 686457ba815d089fecfc374bec2a6a7ac20078b7cb3301371bfcb0c92cbebf2a. First private generated Setup EXE SHA-256: f2b7f96502e62c7a007a41f996aa6e2aa520b17a9d4019b4a0cf3b7edf4d3900.

The actual Windows self-extracting Setup.exe installed the exact genuine D2 native binary into an isolated disposable test-only LOCALAPPDATA and created test-only Start Menu shortcuts under a redirected APPDATA. Both real Windows UIAutomation suites ran against the INSTALLED binary: imaginary FHIR 8-case and Core963 redacted read-only multi-import GUI. Actual installed payload verification passed; altering a pinned README was refused; restoring it passed; uninstall removed owned files and shortcuts while retaining the unrelated test sentinel. Final receipt: REAL_MEDORIGIN_DESKTOP_SETUP_INSTALL_UA_VERIFY_TAMPER_UNINSTALL_PASS, exit 0.

An initial QA attempt modified the recently executed EXE directly and Windows temporarily refused to rewrite the locked PE. Its exact reviewed binary was restored and verified and the task-only installation uninstalled. The harness was corrected to tamper a non-executable pinned text file instead. This is not a security vulnerability or medical finding, but an important Windows file-lock lifecycle observation.

## Hard release NO-GO

Before public download, separately complete clinical identity, RBAC, patient consent and privacy governance; authenticated Core process handoff, packet and DNS network isolation; real FHIR profiles, terminology, invariants and clinical validation; production encryption key provision, recovery and rotation; all reachable dependency advisories and supply chain review; complete accessibility and usability acceptance; signed and reputable Windows installer, app identity/icon/version, Add or Remove Programs registration, safe updates and qualified uninstaller; independent security review and final owner authorization. Protected main and the public website are intentionally unchanged.