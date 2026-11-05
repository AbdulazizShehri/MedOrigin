# MedOrigin D2 — private Windows clickable fictional R4 worklist

Date 2026-11-05. **OWNER-PRIVATE, SYNTHETIC-ONLY, RELEASE NO-GO.**
This is an opt-in user-local .cmd shortcut, NOT a signed installer, Start Menu
entry, auto-start task, EHR link, real patient Workspace or commercial release.

## Product benefit

The source-reviewed Core971 -> genuine offline HL7 R4 v4.0.1 STRUCTURE ONLY gate ->
two invented FHIR files -> ephemeral AES-GCM Workspace -> cold reopen/audit ->
HMAC-bound native Rust worklist needs long command-line paths and digests on
every use. The optional installer creates one fixed clickable entry under the
current user's LOCALAPPDATA/MedOrigin-D2-Private-Developer-QA directory.
Three explicitly selected modes are available: interactive, uia and auto-close.
No patient file picker, arbitrary CLI args, or production key are introduced.

## Requirements

- Real owner Windows 11 and the reviewed D2 source checkout
- A clean exact Core971 Git checkout SHA 9c27397f956303f92aeaf4bc173257c093a53238
- Genuine official offline HL7 R4 structural ZIP SHA 75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6
- The exact SHA-verified compiled native medorigin-desktop-d2-native-egui.exe
- The current owner-local Python executable (SHA-verified) with jsonschema==4.25.1

Example PowerShell from the D2 experiments/desktop-d2-native-egui directory
(the paths below MUST be replaced with already verified actual local paths):

    $python = (py -3.14 -c "import sys;print(sys.executable)")
    $pythonSha = (Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToLowerInvariant()
    $gui = "D:\reviewed-native-build\medorigin-desktop-d2-native-egui.exe"
    $guiSha = (Get-FileHash -LiteralPath $gui -Algorithm SHA256).Hash.ToLowerInvariant()
    py -3.14 -B scripts/install_windows_private_r4_desktop_entry.py --python $python --python-sha256 $pythonSha --core-source "D:\clean-Core971-checkout" --offline-r4-schema "D:\official-hl7\fhir.schema.json.zip" --native-exe $gui --native-sha256 $guiSha --mode interactive

The created clickable entry runs the EXISTING source-reviewed official-R4
launcher. On every actual use it rechecks exact Core source HEAD and cleanliness,
genuine ZIP hash, pinned jsonschema and native EXE bytes, then creates a fresh
HMAC session key and nonce that are not stored in the generated .cmd.

There is NO automatic install. Entry is exclusively created; existing files
are NEVER overwritten. Changing it requires conscious owner review and removal
of only that exact named .cmd. No elevated permission, registry, Start Menu,
task scheduler, PATH modification, installer, patient data or network needed.

## Security and physical tests

- All installation paths must be canonical, local absolute ASCII drive paths,
  with no junction/symlink ancestors, UNC paths, shell expansions, quotes,
  angle brackets, percent/bang characters, pipe, ampersand or multiline text.
- Installer verifies exact current Python binary and SHA, exact native SHA,
  strict clean Core971 source and reviewed official HL7 ZIP before touching
  current-user local output. It never writes secrets, PHI or patient identities.
- Five owner-Windows stdlib tests PASS, including three exclusive entry modes,
  no overwrite, arbitrary shell syntax denial, changed binary refusal,
  and actual Windows cmd.exe execution of the generated clickable file.
  The actual click was intentionally provided a BAD synthetic ZIP and
  correctly failed closed before any Core or GUI startup.
- Seven previously qualified official-R4 launcher source tests PASS. All tests
  used disposable task-owned source subdirectories, not persistent LocalAppData.
  The real Core971 encrypted/HMAC/native GUI positive test was previously
  separately verified in Draft #978; this shortcut's full genuine ZIP live
  launch has NOT been independently re-executed by these installation tests.

## Outstanding production requirements

The entry is developer convenience, not a complete patient Workspace.
Clinical data access, identity/RBAC/consent, production OS key custody,
profile/terminology/FHIRPath validation, packet-level egress enforcement,
code-signed installer, full accessible user journeys and independent
security/clinical reviews are separate release gates. NO PHI; NO publication;
NO protected-main merge; NO release authorization.
