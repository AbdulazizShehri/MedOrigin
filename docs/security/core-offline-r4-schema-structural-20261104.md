# Core offline HL7 FHIR R4 structural check — private Developer Beta slice (2026-11-04)

**Scope:** Python Core and CLI only. No Desktop, patient data, EHR, model use,
release/publication, external validator execution, or frozen root/lock/research
changes. This is a *real but partial* R4 JSON Schema structural check, **not**
full HL7 FHIR conformance or clinical validation.

## Interface (offline, synthetic fixtures only)

The existing `medscale fhir validate synthetic.json` default remains
`status=not_validated` / exit 2 with provenance only. The new optional command:

```sh
medscale fhir validate synthetic.json \
  --offline-r4-schema /local/path/fhir.schema.json.zip \
  --output-dir /local/path/fictional-reports
```

The archive is supplied locally by the caller; the Core library does not
download, embed or redistribute it. It must be the exact published **HL7 FHIR
R4 v4.0.1** archive at
`https://hl7.org/fhir/R4/fhir.schema.json.zip`,
SHA-256
`75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6`.
It contains one `fhir.schema.json` member, with 3,386,892 uncompressed bytes
and 680 definitions. The Python interpreter must have the separate locally
installed `jsonschema==4.25.1` (optional, never added to frozen root dependencies).

- Missing/tampered/symlinked/overlong archive or unqualified/missing `jsonschema`:
  exit 2, **no persisted report**.
- Structural schema failure: persisted report `status=invalid`, bounded
  structural issue codes, exit 2.
- Schema structural pass: persisted report `status=not_validated`, explicit
  partial-coverage warning, exit 2. **Never status=valid.**
- `--with-validator` remains intentionally blocked; neither flag silently
  invokes an external command, package installer, terminology server or EHR.

The structurally incomplete `StructureDefinition` with just `resourceType`
and `id` is known to pass official JSON Schema. A JSON Schema pass does
**not** validate profiles, terminology, invariants, references, cardinality
beyond the implemented schema, or clinical safety. The core remains
synthetic-only. These reports are diagnostics, not medical certificates.

## Reproducibility

`tests/test_core_offline_r4_schema.py` covers the default unchanged behavior,
source/size/admission failures, local CLI failure without reports, artificial
test-only schema positive/negative behavior, and fail-closed dependency version
control. The artificial test ZIP modifies internal test constants via monkeypatch:
it is **not** an official schema or official QA receipt.

Actual published schema E2E (only if explicitly supplied locally, no downloads):

```sh
MEDORIGIN_OFFICIAL_R4_SCHEMA_ZIP=/absolute/path/fhir.schema.json.zip \
  python -m pytest tests/test_core_offline_r4_schema.py -q
```

That opt-in test covers official positive Patient, three negative resources,
and the deliberately incomplete StructureDefinition blind spot. Record actual
Python/jsonschema versions and passed/skipped counts, not hypothetical counts.

## Remaining release NO-GO

This is NOT the requested full R4 validator. A maintained offline full validator
with version-bound HL7 R4 package and applicable terminology/profile resources
must be integrated and independently qualified first. Further gates remain
independent security review #603, source/optional-extras #622, version and
release authority #574, and desktop/network/accessibility qualification outside
this Core slice. No tag, public release, merge to main, real patient processing
or clinical claims are authorized by these tests.

## Actual private local engineering receipt — Windows + WSL, 2026-11-04

- Parent Core Draft #901 source SHA `ad0c62b4366789f5c7e41fc601bb6d0f9d640873`.
  Feature code commit `a22f9c06cf7446fea38723c802f22f6fa2cb9654`.
- Downloaded **only the public HL7 R4 schema archive** for bounded fictional QA;
  retrieved ZIP SHA-256 exactly matched the pin. No patient or project data was
  uploaded. JSON Schema 4.25.1 was installed into a task-only Python target,
  leaving the global Python environment and frozen root untouched.
- Native Windows Python 3.14: selected existing FHIR + new Core tests:
  **37 PASS, 3 DESELECTED** with actual official ZIP and correct library, including
  positive Patient, three invalid synthetic controls and the incomplete
  StructureDefinition blind spot. Two pre-commit formatting-only follow-ups
  then passed **36 PASS, 4 DESELECTED** without rerunning official opt-in.
- Native Windows Python 3.11.15 and 3.12.13: **33 PASS, 7 DESELECTED each**;
  borrowed preinstalled pure pytest from Python 3.14 via temporary PYTHONPATH.
  These runs did NOT claim real R4 schema execution or hermetic environments.
- `ruff check`, `ruff format --check`, and `git diff --check` passed.
- Real `uv build --offline --wheel` in PC's WSL produced local unpublished
  `medscale-0.3.0-py3-none-any.whl`, SHA-256
  `bdf5ad391313e4e1a46c2a4dc17da8dcda2dd24cf87581c6be2c9ecfeff9c25a`.
  The temporary archive was NOT committed or distributed.
- Actual Windows Python 3.14 offline/no-deps installation of that Wheel into
  task-only target contained `medscale/fhirkit/r4_schema.py`. Running the
  installed module with the exact official ZIP and pinned JSON Schema reported:
  structurally acceptable fictional Patient **exit 2 / not_validated**;
  fictional wrong-type Patient **exit 2 / invalid**. Both local report files
  persisted successfully. Generated console launchers were NOT independently
  attested; issue #893 stays open.
- This is local author-side QA, **not exact-head hosted CI or independent
  security/clinical review**. Default-branch security alerts and release NO-GO
  remain open. No PR merge, tag, PyPI upload, signing, or clinical deployment.
