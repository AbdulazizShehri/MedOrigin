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
