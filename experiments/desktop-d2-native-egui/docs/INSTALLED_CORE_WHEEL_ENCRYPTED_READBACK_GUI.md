# Exact installed Python Core + Workspace encrypted readback → D2 native GUI

**2026-11-04. Private stacked Draft on #929, synthetic-only. Nonclinical.**
This implements and actually tests a closer-to-distribution runtime bridge for MedOrigin D2. It is not production process supervision, an authenticated Core transport or a patient-ready product.

## What was implemented

The new `scripts/attest_installed_encrypted_core_readback.py` independently verifies that the entire locally installed **medscale 0.3.0** Core source and **medscale_workspace 0.1.0.dev1** Workspace source come from a reviewed, clean exact Git checkpoint `8e5ed5430f4ab2ebc8981c52c67234023382954b` (#927). The two Wheels were built offline from that source using `uv build --offline --wheel`:

| Pure-Python Wheel | SHA256 | Git tracked package files verified |
| --- | --- | --- |
| `medscale-0.3.0-py3-none-any.whl` | `9b43d0c48678234838d6b76ea794741e8bafe78338c55aa2c7ccbc7e8d22adc8` | 256 |
| `medscale_workspace-0.1.0.dev1-py3-none-any.whl` | `1eedca3fb868e916e3597f7e158ca81fdc56475410d9e7534c6a82797f78b703` | 34 |

All **290 actual installed package files** were checked byte-for-byte against both Wheel members and exact Git-tracked source files. A missing or changed installed module, unexpected Git-tracked/ignored file, `__pycache__` or `.pyc/.pyd/.pth/.dll/.so/.dylib` shadow module, unapproved site top-level package or module, forged Wheel SHA or unreviewed source commit forces NO-GO before Python Core launch. Install uses `python3.13 -m pip install --no-index --no-deps --no-compile --target <private QA location>` and explicit `python3.13 -I -S -B` import roots, never a global install. The harness attests twice, before and after execution.

The new `scripts/qualify_mac_installed_encrypted_readback_gui.py` externally supervises the explicitly source-compiled **synthetic encrypted readback exporter**, running Python Core and Workspace from the **installed Wheel site, not from a source checkout**. Native macOS Seatbelt's deny-default network/outside-write rule is applied to this short-lived Python child; a real unconfined loopback positive / OS-confined network denial and file-write denial are tested each run. A new 0700 disposable directory contains the encrypted fictional Workspace, which performs an actual atomic 3-resource/3-provenance/1-audit/1-manifest commit, close/reopen, anchored audit verification, and `read_synthetic_bundle_in_memory`. Only the exact source-derived 1,164-byte readback projection is delivered to D2's preexisting finite 5s/2048-byte one-shot stdin, SHA256 `c99af04367aeaedeecb29b7fccc8a8fb58f2a85753eeae874eae5ad363307a49`. D2 still starts **no process** and reads no arbitrary FHIR records or paths.

The external harness owns native D2 process lifetime with terminate/wait/kill cleanup. Actual native Mac AX then selects the readback-derived Observation, navigates to recovered Patient → Back, recovered Encounter → Back and clears the readback view. Fixed SHA and nonclinical disclosures must all be present. The private temporary encrypted store is removed before the projection leaves Core and all owned QA temporary directories are removed on exit.

## Observed on genuine Apple Silicon Mac

- Actual Git checkpoint 8e5ed543: clean; offline built 2 Wheels with the exact pinned SHA256 values above.
- Private no-network/no-dependency-installed source site: 290 Git ↔ Wheel ↔ installed files byte equal before and after.
- 10 independent adversarial `test_attest_installed_encrypted_readback.py` unit tests passed, including valid toy install, forged installed module, changed Git source, changed/re-pinned Wheel with extra member, bytecode/native-loader/symlink-related source inventory controls, unreviewed `.pth`, dirty checkout.
- Actually executed installed Core + Workspace AES-GCM synthetic write/reopen/readback in macOS deny-default network/outside-write sandbox with real negative canaries; live output matched the immutable projection.
- Actually executed native D2 GUI and AX tested recovered resource follow/back/clear; runner EXIT 0, exact markers:

```text
TWO_OFFLINE_WHEELS_AND_290_INSTALLED_SOURCE_FILES_BYTE_ATTESTED_NOT_CLINICAL
MACOS_REAL_INSTALLED_WHEELS_CORE_ENCRYPTED_READBACK_SOURCE_MATCHED
MACOS_REAL_ENCRYPTED_CORE_READBACK_NATIVE_THREE_FICTIONAL_RESOURCE_NAV_AX_PASS_NOT_CLINICAL
TWO_OFFLINE_WHEELS_AND_290_INSTALLED_SOURCE_FILES_BYTE_ATTESTED_NOT_CLINICAL
MACOS_ATTESTED_INSTALLED_CORE_ENCRYPTED_READBACK_TO_NATIVE_D2_GUI_PASS_NONCLINICAL
```

Existing #929 native Mac/Windows source Core readback and real GUI journeys independently passed; **new installed-Wheel qualification is so far on macOS only**. Hosted Windows/Ubuntu source-only 9 adversarial unit tests may pass but **do not** prove real installed-Wheel or GUI functionality on those OSes.

## Explicit limits / remaining serious work

The current approved Mac cache contains **cryptography 50.0.0 and cffi 2.0.0**, while Workspace package's reviewed metadata requires `cryptography==50.0.1`. The QA harness uses those already locally cached native packages only to exercise fictional data, and **neither attests their native binaries nor asserts production dependency compliance**. The Windows system-crypto QA path previously used cryptography 50.0.1/cffi 2.1.1 but is a separate source Core test; do not conflate the two.

No in-app approved persistent Python Core worker lifecycle or authenticated/fresh monotonic IPC exists; this is still **an external private synthetic-only supervisor**, not a clinical application service. No production cryptographic key custody, user identity/RBAC/consent, audited persistent patient Workspace or EHR input, Windows/Linux OS-enforced process/descendant/egress proof, full HL7 FHIR R4 terminology/profile/conformance proof, trusted updater/package provenance or independent clinical/security/accessibility review is complete. No real PHI, protected-main merge, distribution, signing, notarization or publication permitted. 66 Dependabot notices on main and release issues #574/#603/#662/#673/#676 remain independent NO-GO gates. Future qualification must first use an *exactly supported and independently audited* crypto dependency chain on each OS and replace externally verified static replayable reports with an authenticated Core session and restricted worker process.

**This proof is a substantial trusted-packaging integration improvement but remains NO-GO for clinical release.**
