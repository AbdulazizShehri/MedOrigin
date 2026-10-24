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
