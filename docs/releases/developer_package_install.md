# MedOrigin — Install the synthetic-only developer packages

- **Status:** Developer/source-checkout installation instructions and test evidence, **not** an authorized new GitHub Release, package-index publication or clinical deployment.
- **Tracking:** [Software release candidate, Issue #574](https://github.com/AbdulazizShehri/MedOrigin/issues/574)
- **Release policy:** [Software release track](software_release_track.md), [versioning](versioning.md), [ADR-0010](../adr/0010-release-architecture.md)
- **Supported Python minors:** 3.11 and 3.12 are tested in Linux CI and on Windows. The Workspace package metadata currently allows Python 3.11–3.14.

The repository has **two independent Python distributions**, both currently for development and synthetic-only workflows. The **MedOrigin** project identity does not rename the stable Python import or CLI namespaces.

| Class | Build root | Distribution / current source version | Installed import / entry point | Status |
| --- | --- | --- | --- | --- |
| Research Core | Repository root | `medscale` / `0.3.0` (unpublished source candidate) | `import medscale`, `medscale --help` | Source-built developer tool; not a clinically qualified answer service |
| Clinical Workspace | `apps/workspace/` | `medscale-workspace` / `0.1.0.dev1` | `import medscale_workspace`, `python -m medscale_workspace` | Independently installable **synthetic offline Python shell/API**, no general-purpose desktop or browser GUI |

These versions describe the current **source baseline**, not authorization to overwrite historical tag `v0.2.0` or claim a new release. A newly approved immutable package release needs a governed successor version and qualified exact-tag artifacts.

## Source-based wheel build (developer-only)

Use a clean checkout of the **specific, reviewed commit**. The following are examples for Unix shells with Python 3.11 or 3.12 and pip available. Wheel *building* can download backend/build dependencies; the Workspace wheel *installation* resolves `cryptography==50.0.1` and its required dependencies. **Offline runtime** means no network or EHR connector is used by the synthetic shell; it does not mean dependency installation is offline.

```bash
git clone https://github.com/AbdulazizShehri/MedOrigin.git
cd MedOrigin
git rev-parse HEAD  # record this exact source identity
python -m pip wheel --no-deps --wheel-dir build/core .
python -m pip wheel --no-deps --wheel-dir build/workspace ./apps/workspace
sha256sum build/core/*.whl build/workspace/*.whl
```

To check the Research Core wheel independently, use a fresh environment and run commands **outside** the checkout:

```bash
python3.11 -m venv /tmp/medorigin-core-smoke
/tmp/medorigin-core-smoke/bin/python -m pip install --no-index --no-deps build/core/medscale-0.3.0-py3-none-any.whl
cd /tmp
./medorigin-core-smoke/bin/python -c 'import medscale, importlib.metadata as m; print(m.version("medscale"), medscale.__file__)'
./medorigin-core-smoke/bin/medscale --version
./medorigin-core-smoke/bin/medscale --help
```

The same source wheel can be installed into a separate Python 3.12 environment. If adapting these commands for PowerShell, use the actual Python interpreter path and `Scripts\python.exe` / `Scripts\medscale.exe` inside the Windows venv; do not rely on `py -3.11` being registered if only a uv-managed interpreter is available.

To check Workspace, use another venv and its **own wheel**, not an editable or source-tree import. Run the installed shell from outside the checkout:

```bash
# From the checkout root, first create the independent Workspace venv:
python3.11 -m venv /tmp/medorigin-workspace-smoke
/tmp/medorigin-workspace-smoke/bin/python -m pip install build/workspace/medscale_workspace-0.1.0.dev1-py3-none-any.whl
cd /tmp
./medorigin-workspace-smoke/bin/python -c 'import medscale_workspace as w, importlib.metadata as m; assert m.version("medscale-workspace")==w.__version__; assert m.version("cryptography")=="50.0.1"; print(w.__version__, w.__file__)'
./medorigin-workspace-smoke/bin/python -m medscale_workspace
```

The expected shell output is exactly:

```json
{"application":"medscale-workspace","data_class":"SYNTHETIC","mode":"offline-shell","ready":true}
```

**Important:** the `cd /tmp` commands are smoke examples; when invoking an install wheel from a different working directory, use its absolute path or install *before* leaving the checkout, as shown. For Python 3.12 repeat in a new venv; do not mix Research Core and Workspace site-packages and mistake a source-tree import for an installed artifact.

## Independent verified evidence — not release receipts

At protected source commit `3f1992a408b8b97ff709506d472a28c86daed449` on Windows, source-built separate Core and Workspace wheels were installed in fresh Python 3.11.15 and 3.12.13 environments and passed version/import/CLI/synthetic-shell smoke. Exact outputs and local artifact SHA-256 values are in [Issue #574](https://github.com/AbdulazizShehri/MedOrigin/issues/574).

The [Workspace CI qualification](../../.github/workflows/workspace-package-qualification.yml) was introduced in [PR #576](https://github.com/AbdulazizShehri/MedOrigin/pull/576) and merged after **16/16 exact-head required checks passed**. Before its update to latest main, two real Linux CI jobs proved independently installed Workspace wheels on Python 3.11.17 and 3.12.15, each with a correct synthetic shell. Their artifacts matched each other by SHA-256:

| Linux-built artifact | SHA-256 (qualification build, not a published release) |
| --- | --- |
| `medscale_workspace-0.1.0.dev1-py3-none-any.whl` | `52c04ecd1138d3adf964cdd0b5bdc5edf3b617bdf4af50311c66806eaa4ce14f` |
| `medscale_workspace-0.1.0.dev1.tar.gz` | `79b010d0355791bbfefa16d6cd9d62a6475fbed39d7802344e5b7f6978ecccf7` |

The locally built Windows wheel had a different SHA-256. **No cross-platform reproducible-byte claim** follows from these tests. The two Linux builds only demonstrate byte identity across those tested Linux jobs. Fresh exact-tag release artifact/CI receipts are still required for a public versioned release.

## Reproducible first-run synthetic FHIR example

The [standalone Developer Beta synthetic FHIR demo](../../examples/synthetic_fhir_developer_beta/README.md)
runs against the **actually installed** `medscale 0.3.0` executable, using
only committed synthetic JSON fixtures. It exercises the documented and legacy
FHIR commands, writes a local content-addressed validation report, rejects
malformed JSON, and produces an inspectable receipt. The demo also supports an
optional second Python runtime for comparing deterministic report bytes.
If the separate `medscale-workspace 0.1.0.dev1` distribution is already installed,
the demo can optionally include its **four-field, synthetic-only local shell
status** via `--workspace-python /path/to/workspace/bin/python` (use
`Scripts/python.exe` on Windows). It rejects extra metadata, incompatible
versions, and missing environments rather than displaying any object data.
Workspace is **not required** for the Core FHIR example, and this optional
status does not imply a clinician GUI, real patient support or approved key
management.

It also generates a **standalone static `preview.html`** for locally
reviewing the synthetic structural result and SHA-256 hashes in a browser,
with no web server, external resources, JavaScript or patient data.

The `valid` report status demonstrates this local structural validation
example, **not** full HL7 FHIR conformance, clinical correctness, or an
authorized distribution. The example has no publication path and does not
modify the frozen research root or historical v0.2.0 data.

## Synthetic-only local evidence export from native desktop

The optional native Developer Beta preview also offers an explicit
**Save synthetic evidence...** action after a successful bundled synthetic
FHIR validation. It saves a new JSON receipt containing **only the
structural-check status and SHA-256 digests**, plus tightly whitelisted
synthetic Workspace flags when applicable. It never writes the source FHIR
fixture, original patient/encounter objects, arbitrary medical records,
machine paths, or any existing output file. The GUI export is **disabled**
before a verified run or after failure. This is a private local developer
artifact, not a clinical report or authorization to publish the package.

## Optional pinned synthetic case exploration

The [native developer-only desktop example](../../examples/synthetic_fhir_developer_beta/README.md)
also offers a **Synthetic cases** page when an already-installed,
synthetic-only `medscale-workspace 0.1.0.dev1` runtime is supplied via
`--workspace-python`. It reads precisely the bundled fictional patient and
encounter fixtures by calling the installed Workspace snapshot, then
presents only a pinned non-PHI label set. Unknown or changed object fields
fail closed. The **Run FHIR validation** action transitions to the
existing installed-Core validation workflow; no patient import, clinical
functionality, network server or historical v0.2.0 dataset migration is
introduced.

## Optional interactive native Developer Beta preview

After installing the Core Wheel into a supported Python 3.11/3.12 environment,
developers may run the [synthetic-only Tkinter desktop preview](../../examples/synthetic_fhir_developer_beta/README.md)
via `python examples/synthetic_fhir_developer_beta/desktop.py --cli
/path/to/installed/medscale` (Windows uses `Scripts/medscale.exe`).
This example is a **repository-only tool**, not a packaged installer or
general-purpose clinician GUI. It provides an actual interactive validation
button, report SHA-256 display and clipboard action, using **only bundled
synthetic FHIR data** with temporary local reports. An optional separately
installed Workspace Python environment can supply *strictly non-object*
SYNTHETIC shell status; Tkinter may not be available on every Python install.
No additional public release, PHI access or persistent production store is
authorized by this preview.

## Hard stop boundaries

- Use synthetic data only. There is **no authorization** to enter, import or process PHI or real-patient records; no production EHR writes or autonomous diagnosis.
- Workspace local protected storage has **no production platform-protected root-key provider**; it fails closed, and is not production-ready.
- The installed Python shell is **not** a full clinician-facing web/desktop application.
- A wheel build, a local Python import, a successful hosted CI check, and a GitHub Release are distinct states. No new tag, publisher activation, PyPI/TestPyPI/Hugging Face publication, scientific runtime validation or model-efficacy claim is authorized merely by these installation steps.
- The freeze on root research `pyproject.toml` and `uv.lock`, evidence provenance, data-domain no-backflow, licensing and historical `v0.2.0` identity remain in effect.
