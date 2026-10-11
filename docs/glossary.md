# Glossary

- **Status:** Reference (append-only; extend, do not rename)
- **Date:** 2026-07-10

Terminology used across MedOrigin and preserved legacy research records. Acronyms are expanded on first use here so that
external contributors and collaborators can read any document without prior context.

| Term | Definition |
|---|---|
| **MedOrigin** | Current public identity of this medical AI research and local Clinical Workspace project. |
| **MedScale** | Historical project name and retained `medscale` Python distribution/API/CLI compatibility identity. |
| **Afia** | A separate healthcare product that *consumes* MedScale. MedScale never depends on Afia. |
| **MESC** | The MedScale clinical model family — a grammar-constrained, QLoRA-adapted clinical model. `MESC-v0` is the first adapter. *(The letter-expansion of the acronym is not yet ratified; a naming ADR is recommended.)* |
| **MedScale-Bench** | MedScale's deterministic, executable, PHI-free benchmark; the program's crown artifact. |
| **FHIR** | Fast Healthcare Interoperability Resources — the HL7 standard for exchanging health data. |
| **StructureDefinition** | The FHIR machine-readable specification of a resource's structure and constraints. |
| **FHIR profile** | A constrained specialization of a FHIR resource for a particular use. |
| **FHIRPath** | A path-based expression language for navigating and querying FHIR resources. |
| **CQL** | Clinical Quality Language — a higher-level language for expressing clinical logic over FHIR. |
| **Terminology / value set** | Controlled clinical vocabularies (LOINC, RxNorm, SNOMED CT, ICD, UMLS) and the permitted code sets bound to FHIR elements. |
| **SNOMED CT** | A large clinical terminology; licence-restricted, therefore interface-only and never vendored (R3). |
| **Grammar-constrained decoding** | Restricting a model's generation to a formal grammar (e.g. compiled from a StructureDefinition) so output is structurally valid by construction. |
| **GBNF** | A BNF-style grammar format used to constrain decoding. |
| **Validator** | The HL7 (Java) FHIR validator — MedScale's executable ground truth for structural/terminology/profile conformance. |
| **QLoRA / LoRA / PEFT** | Parameter-efficient fine-tuning methods; QLoRA is quantized LoRA, enabling training on modest compute. |
| **Synthea** | An open synthetic patient generator; MedScale's primary synthetic data source. |
| **PHI** | Protected Health Information — real patient data. MedScale is PHI-free by policy (R2). |
| **litdb** | The MedScale literature database (T1): PRISMA-screened, citation-verified. |
| **PRISMA** | The systematic-review reporting standard governing litdb screening. |
| **RQ (RQ1–RQ7)** | Research Questions — the falsifiable questions MedScale exists to answer. |
| **ADR** | Architecture Decision Record — a dated record of a hard-to-reverse decision (R6). |
| **Rules R1–R7** | The program rules; see [governance/rules.md](governance/rules.md). |
| **T0–T7** | The Horizon-1 execution phases; see the [ROADMAP](../ROADMAP.md). |
| **T-VALIDATE / T-REPAIR / T-EXTRACT** | Benchmark task families: detect conformance errors / repair them / extract a FHIR bundle from a note. |
| **Constraint delta / prompting delta** | The separately-reported effects of grammar constraint vs prompting in the 2×2 evaluation. |
| **Horizon (H1–H4)** | Time-gated stages of ambition; only H1 is committed work. |
| **Evidence Object** | ADR-0009's unit of validated evidence: one atomic claim + provenance + verification state + declared grading. |
| **PICO** | Population, Intervention, Comparator, Outcome — the structured slots of a clinical claim. |
| **Verification state** | The ADR-0009 state machine: unverified → source_verified → extraction_verified, with disputed/retracted. A model can never verify its own extraction. |
| **medscale-study-design-v1** | MedScale's deterministic study-design→level grading scheme (1 = systematic review/meta-analysis … 5 = preclinical/other). Grades design, not execution quality. |
| **Pillar 1 / Pillar 2** | Verifiable clinical generation / verified evidence infrastructure — MedScale's two pillars on one verification spine (ADR-0005). |
