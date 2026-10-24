# MedOrigin — synthetic FHIR first-run demo

**Engineering-only example for the unpublished Developer Beta candidate.** MedOrigin is the project name; the currently qualified Python distribution/import/CLI remains **`medscale 0.3.0`**. This folder contains only source and synthetic fixtures. It is not bundled into the isolated Core Wheel and is not an authorized public release.

## One-command demonstration

Using an *already installed* `medscale 0.3.0` executable from a trusted Wheel on Python 3.11 or 3.12:

```powershell
python examples/synthetic_fhir_developer_beta/reproduce.py --cli "C:/path/to/venv/Scripts/medscale.exe" --out "C:/path/to/new-synthetic-demo"
```

On Linux/macOS, supply `venv/bin/medscale` instead. To compare output bytes from two independently installed Python environments, provide `--alt-cli "C:/path/to/other/venv/Scripts/medscale.exe"`. Only Python's standard library is needed to run the script itself. Network installation may be needed to obtain dependencies beforehand; this example **does not access network APIs**.

The command checks the installed distribution version, validates a tiny synthetic `StructureDefinition` file, verifies its local content-addressed `report.json`, exercises the documented and legacy FHIR commands, and confirms a malformed JSON fixture exits with code **1**. Successful completion prints `MEDORIGIN_SYNTHETIC_FHIR_DEMO_PASS` and the SHA-256 digests. `--out` must name a *nonexistent* directory, which protects existing evidence from accidental overwrite. If an error occurs, treat the partial output as nonqualifying.

## Optional installed synthetic Workspace status

MedOrigin also has a **separate**, independently installed Python distribution,
`medscale-workspace 0.1.0.dev1`. If you have already installed it into an
independent Python 3.11/3.12 environment, add `--workspace-python` pointing to
that environment's `python.exe` (Windows) or `bin/python` (macOS/Linux):

```powershell
python examples/synthetic_fhir_developer_beta/reproduce.py --cli "C:/path/to/core/venv/Scripts/medscale.exe" --workspace-python "C:/path/to/workspace/venv/Scripts/python.exe" --out "C:/path/to/new-synthetic-combined-demo"
```

The optional check executes the separately installed `python -I -m
medscale_workspace` synthetic shell, verifies exact distribution version and
admits **only** four known non-object metadata fields: application, SYNTHETIC
data class, offline-shell mode and ready=true. Any unexpected fields (including
patient names or record content), wrong version, missing package, or invalid
status cause a **fail-closed** result and cannot appear in the static preview.

The browser preview adds a clear **Synthetic Workspace** status card when this
optional check passed. Otherwise the original Core-only FHIR example and its
browser preview work without any Workspace installation. The Workspace shell
is not a real clinician UI and has no production platform root-key provider.
Its dependencies can require a normal *free* Python package installation
before the local runtime can operate offline; this demo itself never uploads
data or connects to an EHR.

## Explicit synthetic-only evidence export (desktop preview)

After **Validate synthetic fixture** succeeds, select
**Save synthetic evidence...** in the native developer preview.
Choose a new `.json` filename using the save dialog. The output contains
**only** validated structural-check status and SHA-256 digests, flags
indicating that the optional installed synthetic Workspace/case preview was
verified, and explicit statements that public release, independent security
review, and clinical use are **not** authorized.

This is an **explicit local export**, not a saved patient record or a
clinical FHIR bundle. Original JSON documents, names, encounter identifiers,
machine-specific paths, Workspace objects and validation source data are
**excluded**. A destination that already exists is **never overwritten**,
and failed/partial validation does not enable export. Each successful
receipt is deterministic for a fixed set of validated synthetic results.
No server or network connection is involved in writing the local file.

The exported receipt does **not** independently certify its SHA-256 values,
the completeness of HL7 FHIR conformance, or historical dataset compatibility.
Use the existing source-bound package attestations and separate review gates
for release qualification. Do not save any real patient data here.

## Pinned synthetic case explorer (desktop preview only)

The optional native Tkinter preview has a **Synthetic cases** navigation page.
When `--workspace-python` points to a separately installed
`medscale-workspace 0.1.0.dev1`, **Load synthetic case** reads the existing
Workspace's immutable, fictional `Synthetic Patient Alpha` and
`Synthetic Encounter 001` fixtures. The page also links to the ordinary
**Run FHIR validation** workflow, using the already installed Core CLI.

The explorer deliberately **does not** allow typing patient data, file
selection, opening real medical records, searching a clinic, saving changes,
or migrating historical datasets. An explicit **allowlist of the entire
pinned Workspace snapshot** (including the fixture identities, SYNTHETIC
classification and offline safety capabilities) must match before it shows
the whitelisted synthetic names. Unexpected metadata, patient-like fields,
wrong Workspace versions, numeric stand-ins for Boolean safety fields,
duplicate JSON keys (including hidden overwritten fields), or modified fixture
bytes are **rejected rather than displayed**. The same strict JSON and Boolean
admission rules apply to the optional installed Workspace shell. Installed Workspace is optional: the synthetic Core
validation screen continues to operate without it.

The example is a **local developer UX prototype**, not a clinical patient
directory, a persistent patient store, or a packaged desktop application.

## Native Windows desktop preview (interactive)

An optional **real local Tkinter desktop window** is available for developers
who have a trusted, **already-installed** `medscale 0.3.0` CLI. Python must
include the standard-library Tkinter/Tcl runtime (confirmed on Windows Python
3.11). Tkinter is not required by the Core Wheel or the existing CLI example.

From the repository root, Windows PowerShell:

```powershell
python examples/synthetic_fhir_developer_beta/desktop.py --cli "C:/path/to/core/venv/Scripts/medscale.exe"
```

To display the separately installed **synthetic-only Workspace** status:

```powershell
python examples/synthetic_fhir_developer_beta/desktop.py --cli "C:/path/to/core/venv/Scripts/medscale.exe" --workspace-python "C:/path/to/workspace/venv/Scripts/python.exe"
```

This *functional developer preview*, not a full clinical GUI, has three
screens: Overview, Synthetic validation and Safety & scope. Select
**Validate synthetic fixture** to invoke the **installed CLI** asynchronously;
the UI remains responsive, checks a bundled fictional fixture, and displays
only a whitelisted result and its SHA-256 digest. **Copy report SHA-256** copies
the displayed digest. Any optional Workspace result is restricted to the
SYNTHETIC offline shell metadata with no patient fields. Only a local
temporary directory is used for each run, cleaned after normal completion;
interrupted processes may leave OS temporary files to clean up manually.

**No arbitrary file opening, patient import, EHR connection, recording,
clinical interpretation, permanent dataset store, server, or cloud call is
implemented in this preview.** A missing Tk runtime should be treated as
an unsupported optional GUI environment, not a failure of the Core CLI.

## Offline browser preview

Successful execution also writes a **static `preview.html`** in the new
`--out` folder. Open the file directly in a local browser: it displays
the synthetic structural-check results, report and fixture SHA-256 hashes,
and a prominent disclaimer. No web server, JavaScript, fonts from CDNs,
data uploads or network connections are required. All rendered receipt
fields are HTML-escaped, and the page declares a restrictive CSP.

## Strict limitations

- Use synthetic inputs **only**. The `valid` result means the tiny fixture passed the **local structural validator**, not full HL7 FHIR standards conformance, clinical correctness, diagnostic accuracy or production EHR readiness.
- The existing `v0.2.0` persisted data format is known incompatible. The example never loads, migrates, overwrites or repairs historical patient/research data.
- Core Beta's 20/20 hosted CI is engineering evidence, not independent audit, publication permission or a finished clinician UI.
- [Independent security review #603](https://github.com/AbdulazizShehri/MedOrigin/issues/603) and [formal package/version decision #574](https://github.com/AbdulazizShehri/MedOrigin/issues/574) remain open. No tag, release, deployment or data collection is authorized by this example.
