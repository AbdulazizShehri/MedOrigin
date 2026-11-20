# Windows installed-Wheel fictional Core -> interactive native D2 (private)

**2026-11-04. Nonpublishing developer integration, stacked above #937. Not a patient application and NOT a release qualification.**

## Product-oriented advance

The previously proven Windows developer interactive native launcher in #937 runs a **pinned source checkout**. This slice adds an explicitly opt-in `scripts/launch_windows_installed_fictional_core.py` that instead runs the genuine encrypted fictional Workspace logic from a **separately installed pair of Python Wheels** inside an isolated `python -I -S -B` Core child, spawned suspended and assigned to a Windows kill-on-close Job Object **before** the first Python instruction.

At startup and after the native window closes, the launcher independently checks the exact pinned clean source Git checkpoint, the exact two QA-only Wheel archive SHA-256 hashes, **all 290 individual Git ↔ Wheel ↔ installed Python package files**, absence of unexpected installed top-level packages/bytecode/native loaders/symlinks, unchanged hashes of developer Python and D2 GUI, and unchanged source-compiled nonclinical exporter and redacted readback fixture. The worker independently asserts the actual imports `medscale.__file__` and `medscale_workspace.__file__` lie in the **installed** site, not in the Git source tree or a global package. It imports cryptography 50.0.1/cffi 2.1.1 from the developer machine's existing system Python site; these native dependencies were **not** independently supply-chain or OS-egress audited.

The independently installed Worker executes the actual source-approved **fictional-only** 3-resource AES-GCM atomic import + 3 provenance records + 1 audit event + manifest, closes/reopens the encrypted store, verifies the audit chain, reads back the decrypted fictional Bundle in Core memory, strips raw FHIR/patient-like values, and emits exactly 1,164 approved bytes with SHA256 `c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49`. The launcher checks actual bytes against the reviewed canonical projection before opening the native egui D2 window via its existing explicit one-shot, 2,048-byte-limited stdin mode. The native Rust GUI still does NOT launch Core or open arbitrary patient files. The user may interact with the recovered-resource facets, incoming/outgoing links and multi-step Back; optional `--qa-auto-close` auto-closes only the owned GUI window, `--qa-uia` uses **actual Windows UIAutomation** to click the received installed-Core results.

## Pinned local Windows developer QA Wheels

Windows WSL Ubuntu `uv 0.12.21` built these *private source-backed QA Wheels* offline from the clean `8e5ed5430f4ab2ebc8981c52c67234023382954b` checkout (which was never modified). They were installed with native Windows Python 3.14.7 `pip --no-index --no-deps --no-compile --target` under a disposable task-owned folder, **not** to global site packages. All 290 Python source files matched Git/Wheel/installed bytes. Because Wheel ZIP bytes **differ from independently observed macOS Wheel ZIPs** in #931, the following hashes are scoped only to this particular Windows WSL-built QA artifact. Do not replace or waive these pins without independent source-qualified rebuild and tests.

| Local Windows QA Wheel | SHA256 | Exact installed package source count |
| --- | --- | ---: |
| medscale-0.3.0-py3-none-any.whl | `9aad845ecec6b09e27b38a29a2fb521b3958218aef5ae4b0415abb88ee5fc24b` | 256 |
| medscale_workspace-0.1.0.dev1-py3-none-any.whl | `86488f14f113ec2e56f0c5185b91fbd61e546dc73f06587730b6794436e8d465` | 34 |

No generated packages, source fixture records, encrypted temporary Workspace stores, or patient-related content is committed to GitHub; only source code, QA, and this evidence are preserved. Rebuild only in approved no-PHI offline QA workspaces and verify exact Wheel hashes before reuse.

## Windows developer command (only when privately qualified local files exist)

```powershell
python -B scripts/launch_windows_installed_fictional_core.py `
  --core-source <CLEAN_EXACT_8e5ed54_GIT_CHECKOUT> `
  --wheels <QA_ONLY_OFFLINE_WHEELS_DIRECTORY> `
  --installed-site <QA_ONLY_WINDOWS_PRIVATE_PIP_TARGET> `
  --python <REVIEWED_WINDOWS_PYTHON_3_14_EXE> `
  --crypto-site <EXISTING_DEV_PYTHON_SITE_PACKAGES> `
  --native-gui <EXACT_COMPILED_D2_NATIVE_EXE> `
  --python-sha <EXACT_SHA256> --native-sha <EXACT_SHA256>
```

This is **not a desktop installer**, graphical first-run setup, a general import feature, a patient data pipeline, an authenticated IPC service, a clinical validation system or an approval to publish.

## Actually executed on Windows 11 PC

- Windows Python 3.14.7 on the owner's PC, WSL offline Wheel build, pip no-index/no-deps/no-compile target install. 290 actual package bytes verified against exact Git and local Wheel archives **before and after** Core use.
- Actual suspended Windows Core worker assigned to Job Object before resume; actual installed package import-path verification; genuine encrypted synthetic import/reopen/audit/readback; exact 1,164-byte projection SHA matched.
- Actual native D2 gui at source checkpoint #937 and SHA256 `221a126b5a09a5ab548973bb289ee0463d66a3d8282dc00fc4510da1301b6445`: interactive installed-Wheel launcher with `--qa-auto-close` returned exit 0 and `WINDOWS_INSTALLED_290_SOURCE_VERIFIED_ENCRYPTED_CORE_INTERACTIVE_D2_PASS_NOT_CLINICAL`.
- Second actual installed Core worker -> unchanged D2 GUI under `--qa-uia`: Windows UIA clicked native Patient facet, verified 1/3 visible and Observation hidden, restored All and traversed the recovered Observation/Encounter/Patient graph (incoming, outgoing, multi-step Back, Clear); exit 0 with `WINDOWS_INSTALLED_ENCRYPTED_CORE_TO_NATIVE_D2_GRAPH_UIA_PASS_NONCLINICAL`.
- Windows Python3.14: **11 attestation adversarial tests**, 7 source Core readback tests, **5 installed-Wheel launcher/source-boundary tests** passed (23 focused Python tests total), including an explicit empty/partial approved-Wheel pin-set refusal. `ruff check` and `ruff format` passed on the four changed Python modules. On offline native Rust D2 baseline #937, 68 Rust tests and Clippy/fmt passed; no Rust code changed in this particular slice. The older Windows source-Core-to-GUI UIAutomation route also re-ran PASS on the refactored Job Object supervisor.
- Separate GitHub CI on the new exact head must be checked before claiming hosted success. No independent red-team, regulatory, accessibility, performance or medical authorization from author-side proof.

## Security truth and NO-GO gates

Installed Python source integrity was established against a **single reviewed Git checkpoint**, but this does **not** attest Python.exe, compiled cryptography/cffi native module bytes, the toolchain chain-of-trust or the Windows command-shell process tree. Windows Job Object **only** supervises lifetime (kill-on-close), NOT TCP/UDP/DNS network isolation. Native GUI sender/freshness/session authenticity is NOT established by exact static bytes; byte payload can be replayed. No approved production key custody, persistent multi-user Clinical Workspace, patient identity/RBAC/consent, real EHR write path, full FHIR R4 conformance, independent security/clinical/OS confinement review or full accessibilty review. All access still fictional-only. Default branch has 66 security advisories at latest push. Release **NO-GO**. Never process PHI, claim clinical readiness, merge protected main, sign/notarize or publish artifacts without separately documented approvals.
