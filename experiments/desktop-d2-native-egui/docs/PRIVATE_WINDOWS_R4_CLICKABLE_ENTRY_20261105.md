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

## Guarded Core #979 clickable entry (private D2 integration, 2026-11-05)

This owner-private linear source integration incorporates the Core #980 clickable developer entry into the exact Core #982 guarded Core979 FHIR reference and official R4/HMAC native worklist source, without merging another protected branch. The installer remains opt-in, current-user-only and expressly NON-PRODUCTION. No Start Menu, elevation, startup task, registry, system-wide installer, clinical record picker or persistence enabled.

New optional CLI selector: --core-revision core979 (default core971 unchanged). Explicit Core979 creates separate fixed-name owner-only .cmd entries for interactive, actual UIAutomation QA and auto-close QA, so it cannot overwrite old Core971 entry names. Exact source Core979 commit 440cee21494a62c458106631931f3610c05d1ea8 must be a clean reviewed Git tree; the installer invokes an independent actual Core979 six-resource invented two-person Bundle preflight, including mismatched Observation/Encounter subjects and reversed entry order, BEFORE writing any owner-only developer entry. The generated .cmd invokes the reviewed launch_windows_real_core979_guarded_r4_fictional_batch.py which independently repeats this source check and pins actual local official HL7 R4 v4.0.1 ZIP SHA256 and the native Windows executable SHA before running Core. It uses only temporary encrypted invented Workspace readback and a fresh HMAC-bound native session. The old Core971 path preserves its exact revision and launcher unmodified.

Owner Windows source tests: 8/8 PASS; includes exclusive distinct names for all three modes, no replacement, strict filename/metacharacter validation, source preflight before write, wrong Python/native SHA rejection, unknown revision refusal and actual cmd.exe invocation against a deliberately invalid dummy Core979 source that FAILS CLOSED with exit2/no GUI. All tests used only temporary task-owned directories, did not install a real owner LocalAppData entry. A real genuine official R4 clicked shortcut to the native GUI has not been executed in this merge; previous full actual Core979 -> R4 -> HMAC native GUI UIAutomation PASS belongs to parent #982. A clickable developer entry is NOT a signed or production installed application. Do not claim source identity, same-user process tamper resistance or clinical readiness from this work.