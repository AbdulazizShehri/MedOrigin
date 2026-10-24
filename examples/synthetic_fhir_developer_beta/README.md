# MedOrigin — synthetic FHIR first-run demo

**Engineering-only example for the unpublished Developer Beta candidate.** MedOrigin is the project name; the currently qualified Python distribution/import/CLI remains **`medscale 0.3.0`**. This folder contains only source and synthetic fixtures. It is not bundled into the isolated Core Wheel and is not an authorized public release.

## One-command demonstration

Using an *already installed* `medscale 0.3.0` executable from a trusted Wheel on Python 3.11 or 3.12:

```powershell
python examples/synthetic_fhir_developer_beta/reproduce.py --cli "C:/path/to/venv/Scripts/medscale.exe" --out "C:/path/to/new-synthetic-demo"
```

On Linux/macOS, supply `venv/bin/medscale` instead. To compare output bytes from two independently installed Python environments, provide `--alt-cli "C:/path/to/other/venv/Scripts/medscale.exe"`. Only Python's standard library is needed to run the script itself. Network installation may be needed to obtain dependencies beforehand; this example **does not access network APIs**.

The command checks the installed distribution version, validates a tiny synthetic `StructureDefinition` file, verifies its local content-addressed `report.json`, exercises the documented and legacy FHIR commands, and confirms a malformed JSON fixture exits with code **1**. Successful completion prints `MEDORIGIN_SYNTHETIC_FHIR_DEMO_PASS` and the SHA-256 digests. `--out` must name a *nonexistent* directory, which protects existing evidence from accidental overwrite. If an error occurs, treat the partial output as nonqualifying.

## Strict limitations

- Use synthetic inputs **only**. The `valid` result means the tiny fixture passed the **local structural validator**, not full HL7 FHIR standards conformance, clinical correctness, diagnostic accuracy or production EHR readiness.
- The existing `v0.2.0` persisted data format is known incompatible. The example never loads, migrates, overwrites or repairs historical patient/research data.
- Core Beta's 20/20 hosted CI is engineering evidence, not independent audit, publication permission or a finished clinician UI.
- [Independent security review #603](https://github.com/AbdulazizShehri/MedOrigin/issues/603) and [formal package/version decision #574](https://github.com/AbdulazizShehri/MedOrigin/issues/574) remain open. No tag, release, deployment or data collection is authorized by this example.
