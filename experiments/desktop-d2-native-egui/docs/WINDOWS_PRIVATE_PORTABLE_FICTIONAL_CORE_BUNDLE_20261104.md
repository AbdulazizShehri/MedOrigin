# Private Windows portable fictional Core+native D2 developer kit

**2026-11-04. Private stacked Draft above #938. NO PHI; NOT a clinical product, public installer or production release.**

## Functional progress

Two-stage, explicitly opt-in dev workflow:
1. **Offline preparation** from *clean exact reviewed Git Core checkpoint* `8e5ed5430f4ab2ebc8981c52c67234023382954b`, two privately built exact-hash Wheels (as in #938), an isolated `pip --no-index --no-deps --no-compile --target` install, and exact reviewed compiled native D2 executable. `scripts/prepare_windows_portable_fictional_bundle.py` first verifies **all 290 Git ↔ Wheel ↔ installed Core/Workspace Python source files**, then copies exactly the 290 files (no installed package metadata/launcher shims/native code) into `bundle/core/`, reviewed fictional-only runtime helper scripts, exact source projection and UIAutomation observer, and the native GUI into a private **task-owned, atomic staging directory**. It computes a canonical source-tree SHA over sorted exact relative paths, lengths and per-file digests, and checks it against the review-pinned constant `2979a075ab7a4264b6eeffca365aebac1dd9677e7e6bd7ebe2f0f7b2405c23e9`. It then stores only explicit nonclinical manifest flags and runtime file digests, repeats the installed-Wheel attestation, and renames the finished stage to the chosen nonexistent destination. It does NOT install Python/cryptography, fetch online code, add patient data, publish or write to a global application directory.
2. **Interactive runtime** from `bundle/scripts/launch_windows_portable_fictional_core.py` **without any Git checkout, Wheel archives, build tools or CLI path to the source tree**. Before launch and after the GUI closes it verifies the exact 290-file Core tree, manifest schema with explicit `sender_or_session_authenticated=false`, fixed source commit, verified projection/exporter, no extra runtime/core files, and per-file manifest digests. It executes Python 3.14's `-I -S -B` installed-source Core worker **suspended then assigned to a Windows kill-on-close Job Object before first instruction**. The worker asserts actual imports reside in `bundle/core`, runs the real **fixed fictional** AES-GCM Workspace atomic import/close/reopen/audit/decrypted-memory readback, and emits only the exact 1,164-byte projection SHA `c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49`. The native D2 application receives those source-projected bytes over its existing bounded explicit one-shot stdin and displays the real recovered worklist, type facet, incoming/outgoing relationships, Back and Clear. The launcher owns the GUI lifecycle (max 30-minute interactive session); the GUI remains native Rust and never spawns Core.

## Actual Windows 11 proof

- Built private Windows source-backed Wheels **offline in WSL Ubuntu** from pinned Git checkpoint; exact SHA256 values `9aad845ecec6b09e27b38a29a2fb521b3958218aef5ae4b0415abb88ee5fc24b` (Core) and `86488f14f113ec2e56f0c5185b91fbd61e546dc73f06587730b6794436e8d465` (Workspace). Their contents were independently matched to clean Git+pip-installed Windows source. These QA Wheel ZIP hashes are Windows-build-specific, different from Mac #931 ZIP hashes.
- Prepared a **fresh 290-file sealed source tree bundle** with reviewed SHA `2979a075ab7a4264b6eeffca365aebac1dd9677e7e6bd7ebe2f0f7b2405c23e9`. The source Git checkout/Wheels were not consulted or passed at runtime.
- Actual Windows Python 3.14 / system cryptography 50.0.1 and cffi 2.1.1, source-import proof inside Job Object, genuine synthetic Core encrypted import/reopen/readback -> compiled native D2 executable SHA `221a126b5a09a5ab548973bb289ee0463d66a3d8282dc00fc4510da1301b6445`: `--qa-auto-close` **exit 0**, `WINDOWS_PORTABLE_INSTALLED_FICTIONAL_CORE_NO_GIT_NATIVE_D2_PASS_NOT_CLINICAL`.
- Actual independent Windows native UIAutomation `--qa-uia` clicked type facet (Patient 1/3), source-derived Observation/Encounter/Patient incoming/outgoing relations, multiple Back and Clear using the recovered byte-exact Core output; **exit 0**, `WINDOWS_PORTABLE_FICTIONAL_CORE_TO_NATIVE_D2_GRAPH_UIA_PASS_NONCLINICAL`.
- Two real **adversarial runtime refusal probes**: modified one byte in a packaged `medscale/__init__.py` and raised manifest's fake sender-authentication claim both refused with **exit 2** before Core starts. Each original file was restored in a `finally` block.
- Seven independent synthetic minitree source/manifest tests PASS (valid 2-file fake, source mutation, injected Python/native loader, false sender authentication, changed runtime script, extra script, non-Windows refusal, Job Object call order); Ruff check/format PASS. Full native Rust D2 unaffected; #938 Windows/Ubuntu CI previously PASS. New exact-head hosted CI must independently PASS before marking this branch green.
- The disposable dev kit was built locally for this verification; **no packaged executables, wheels, binary dependencies or patient records are committed to GitHub**.

## Developer-only commands

After locally qualifying the two exact pinned Wheels, private Windows installed-site and native executable as described above:

```powershell
python -B scripts/prepare_windows_portable_fictional_bundle.py `
  --core-source <CLEAN_REVIEWED_SOURCE_CHECKOUT> `
  --wheels <EXACT_PRIVATE_OFFLINE_WHEELS> `
  --installed-site <EXACT_PRIVATE_INSTALLED_SITE> `
  --native-gui <EXACT_REVIEWED_NATIVE_D2_EXE> `
  --native-sha <EXACT_64_HEX_NATIVE_SHA256> `
  --out <NEW_PRIVATE_BUNDLE_DIRECTORY>
```

Running the prepared kit does NOT need Git/Wheels:

```powershell
python -B <PRIVATE_BUNDLE>\scripts\launch_windows_portable_fictional_core.py `
  --python <REVIEWED_WINDOWS_PYTHON_EXE> `
  --crypto-site <KNOWN_DEVELOPER_SYSTEM_SITE_PACKAGES> `
  --python-sha <EXACT_64_HEX_PYTHON_SHA256>
```

For unattended QA only, add `--qa-auto-close` (owned GUI close) or `--qa-uia` (real Windows UI controls).

## Mandatory NO-GO caveats

- This is an **integrity-checked developer bundle, not a cryptographically signed distribution**. Its local JSON manifest is NOT a trusted external signing authority; an attacker able to rewrite both package and verifier is not addressed. Python binary, installed cryptography/cffi native extensions and runtime external dependencies have **not** been independently audited/attested.
- A Windows Job Object controls worker lifetime, **not** TCP/UDP/DNS/network egress. OS-enforced network confinement is still unresolved. Fixed source bytes and local path checks do **not** authenticate a sender, establish session freshness or prevent replay. No approval for real patient data.
- No production key custody, durable encrypted multiuser Workspace, real access-control/consent/identity, EHR, full FHIR R4 profiles/invariants/terminology or independently reviewed clinical safety/security/accessibility. 66 default branch security advisories remain. This experiment does not authorize merging protected main, signing, publishing or distribution.

Keep the development kit private, fictional-only and task-owned. Always remove temporary copies after qualification; source code/tests/evidence alone are committed.
