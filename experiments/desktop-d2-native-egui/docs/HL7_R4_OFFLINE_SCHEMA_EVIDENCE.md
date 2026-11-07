# Offline official HL7 FHIR R4 JSON Schema — synthetic qualification, 2026-11-04

**This is a REAL offline structural JSON-Schema validation tool, but it is intentionally NOT a full FHIR R4 validator, medical certification, Core CLI change, or permission to process patient records.**

## Source and pinned validator material

- Source: published HL7 FHIR **R4 v4.0.1** JSON Schema archive `https://hl7.org/fhir/R4/fhir.schema.json.zip`. Retrieved into a temporary local QA directory; **not copied, bundled or redistributed** in this repository. Zip SHA-256 `75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6`; exactly one member `fhir.schema.json`, 3,386,892 bytes uncompressed and 680 schema definitions, draft-06, schema ID `http://hl7.org/fhir/json-schema/4.0`.
- Local nonproduct isolated Python 3.11.15 venv uses open-source `jsonschema==4.25.1` and pinned package version. Public packages were installed without submitting any user or patient data.
- The new script `scripts/qualify_offline_fhir_r4_schema.py` has **no patient-file argument or network path** and accepts only a locally present zip with the exact SHA-256, size/member count, draft, ID and definition-count expectations. It uses the installed Draft6 validator only on fixed synthetic literals. It fails closed for missing/wrong library or altered schema.
- `scripts/test_offline_fhir_r4_schema.py` adds **7/7 stdlib-only negative and source contract tests**, so hosted CI does not need to download the official schema or silently claim that full R4 schema QA ran there.

## Actual local tests on authorized Apple Silicon Mac

Input type | Meaning | Observed official R4 schema result
--- | --- | ---
`Patient` with synthetic ID and boolean `active=true` | narrow positive schema-only control | **ACCEPTED**, 0 structural errors
`Patient` with `active="true"` string | wrong type negative control | **REJECTED**, >=1 error
`UnknownFictionalResource` with fictional ID | unsupported resource type | **REJECTED**
`Observation` without mandatory status/code | missing mandatory structure | **REJECTED**
`StructureDefinition` with only fictional ID | **critical schema blind spot**: incomplete for clinical conformance | **ACCEPTED** by JSON Schema, therefore **NOT evidence of full FHIR R4 validity**

The last result initially caused our QA to fail. It was investigated, reproduced and added as an **explicit expected coverage gap** that must appear in every subsequent receipt. Final output includes `fhir_r4_conformance_established=false`, `terminology_validated=false`, `profiles_validated=false`, `cross_references_validated=false`, `clinical_release_authorized=false`, `requires_full_r4_profile_and_terminology_validator=true`, and lists `incomplete_structure_definition_accepted` among known blind spots. Final CLI marker: `HL7_R4_OFFLINE_JSON_SCHEMA_STRUCTURAL_CONTROLS_PASS_NOT_CLINICAL_VALIDATION`.

## Reproduce (test-data only)

```sh
cd experiments/desktop-d2-native-egui
python3 -m unittest discover -s scripts -p test_offline_fhir_r4_schema.py -v
# In an isolated QA Python 3.11 environment with jsonschema==4.25.1:
python scripts/qualify_offline_fhir_r4_schema.py \
  --official-r4-schema-zip /absolute/path/to/pinned/fhir.schema.json.zip
```

No patient records, EHR data, internet terminology service, unreviewed clinical profiles or research model predictions were used. The script does not change the MedOrigin Core local `status=not_validated` baseline, which remains the correct conservative conclusion until actual schema, invariant, terminology, profile, reference resolution, clinical safety and regulatory release gates are independently qualified.

## Missing clinical and release requirements

HL7's own R4 validation specification distinguishes **structure**, **cardinality**, **value domains**, **terminology bindings**, **invariants**, **profiles**, **questionnaires** and **business rules**. JSON Schema alone does not implement all of these. For actual FHIR conformance, select and source-pin a fully qualified local HL7 FHIR Validator CLI or equivalent maintained validator; source-pin offline R4 core packages and applicable IG/profile/terminology dependencies, prohibit external terminology-server calls, provide positive/negative/edge-case reference resources, verify error severity/OperationOutcome and independent clinical domain tests, and require independent clinical/security review. See official HL7 documentation: `https://hl7.org/fhir/R4/validation.html` and `https://hl7.org/fhir/R4/downloads.html`.

Do **not** interpret a JSON Schema pass, a synthetic Core report, or this QA receipt as patient data validity or an approved medical release. Keep default-branch dependency alerts, #662 D1 WebView2 egress, #673 Linux AccessKit maintenance, #676 spoken accessibility, #603 independent security review and #574 release authority open. D2 GUI remains synthetic-only, no production FHIR validation, no protected main merge or publication.
