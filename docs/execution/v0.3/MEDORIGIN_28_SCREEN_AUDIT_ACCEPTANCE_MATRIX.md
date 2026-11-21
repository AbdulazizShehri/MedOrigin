# MedOrigin Desktop — 28-Screen Functional Reality Audit & Acceptance Matrix

- **Audit Date:** 2026-11-21
- **Baseline Release:** v0.3.4 (`cd5e5ec2589cded9fa735a256a742f094f3165e8`)
- **Target Release:** v0.3.5
- **Audit Standard:** Strict adherence to `docs/design/desktop-v1/FEATURE_COVERAGE.md`, Lane A (Developer Software Track), Lane B (Scientific Invariants), and Lane C (Clinical Boundaries). Real dynamic computations and mathematical cryptographic chains over admitted synthetic data.

---

## 1. Executive Summary & Audit Baseline

An independent review of `experiments/desktop-d2-native-egui/src/screens.rs` revealed that the 28 declared desktop screens originally fell into three distinct categories:
- **8 Functional / Experimental Routes:** Home, Synthetic Patients, Encounters, FHIR Workspace, FHIR Fixture Inspector, Settings, About, and Help.
- **4 Gated / Deferred Screens:** Audio & Transcript (Gated), Orders & Tasks (Gated), Coding Suggestions (Deferred), and Model Catalog & Runtime (Gated).
- **16 Unconnected Screens (`NotConnected`):** Local Search, Note Drafts, Patient Graph, Patient Timeline, Documents & Canvas, Clinical Evidence, Literature Screening, Tables & Structured Data, Analytics, Dataset Manager, Export Quarantine, Research Explorer, Benchmark & Evaluation, Integrations, Audit History, and Storage & Recovery.

Previously claiming that "all 28 screens were fully functionally audited" conflated route declaration with functional implementation. This matrix establishes the definitive, verifiable state of every screen, connects the 16 unconnected capabilities to native synthetic adapters, and preserves all 4 non-negotiable research/clinical gating boundaries.

---

## 2. Definitive 28-Screen Acceptance Matrix

| # | Group | Screen Label | Route Category | Backend Connection | Real User Interaction | State | Test Evidence | Authorization Boundary | Acceptance Status |
|---|---|---|---|---|---|---|---|---|---|
| **0** | Workspace | **Home** | `Route::Home` | In-memory native preview + `synthetic_bundle.rs` | Local JSON path input (Ctrl+O), drag-and-drop file admission, built-in two-patient fictional demo button, identity walkthrough, light/dark theme switch | Session-only | `windows-native-typed-fictional-path-uia.ps1`, `windows-native-local-fictional-ole-drop-uia.ps1` | Synthetic demo data only; zero real patient data (NO PHI). | **QUALIFIED (Active)** |
| **1** | Workspace | **Local Search** | `Route::LocalSearch` | Native search adapter + `retrieval.py` / `corpus.py` fixture index | Query input, scope filter (Patients, Encounters, Observations, Lit), match table with SHA-256 digests, navigate to resource | Session-only | `test_desktop_screens_execution.rs` | Local memory only; no external network or EHR queries. | **QUALIFIED (Synthetic Adapter)** |
| **2** | Clinical | **Synthetic Patients** | `Route::Records { facet: "Patient" }` | `synthetic_bundle.rs` | Patient selection (`Fictional-Pt-Alpha-101`, etc.), reference drill-down, active condition filter | Session-only | `windows-native-fictional-workspace-uia.ps1` | Synthetic fictional patients only; zero PHI. | **QUALIFIED (Active)** |
| **3** | Clinical | **Encounters** | `Route::Records { facet: "Encounter" }` | `synthetic_bundle.rs` | Encounter timeline list, reasonCode inspection, serviceProvider reference linking | Session-only | `windows-native-fictional-workspace-uia.ps1` | Fictional encounters only; zero live EHR connection. | **QUALIFIED (Active)** |
| **4** | Clinical | **Audio & Transcript** | `Route::Unavailable` (Tag: `Gated`) | `asr.py` (Contract only) | None (Disabled with explanation) | None | `screens.rs::tests::tags_match_the_design_board_and_gates_are_disabled` | **GATED (Lane C):** Live microphone capture unqualified; no audio adapter authorized. | **GATED (Compliant)** |
| **5** | Clinical | **Note Drafts** | `Route::NoteDrafts` | Native drafting adapter + `draft.py` / `review.py` | SOAP note editor (Subjective, Objective, Assessment, Plan), missing-data verification, synthetic provenance receipt attestation | Session-only | `test_desktop_screens_execution.rs` | **Lane C:** Review-only draft; zero EHR writeback; non-clinical research. | **QUALIFIED (Synthetic Adapter)** |
| **6** | Clinical | **Orders & Tasks** | `Route::Unavailable` (Tag: `Gated`) | CW roadmap 4.2 | None (Disabled with explanation) | None | `screens.rs::tests::tags_match_the_design_board_and_gates_are_disabled` | **GATED (Lane C):** Writing orders or tasks to external systems is strictly prohibited. | **GATED (Compliant)** |
| **7** | Clinical | **Coding Suggestions** | `Route::Unavailable` (Tag: `Deferred`) | CW capability map | None (Disabled with explanation) | None | `screens.rs::tests::tags_match_the_design_board_and_gates_are_disabled` | **DEFERRED (Lane C):** Billing submission is permanently disabled. | **DEFERRED (Compliant)** |
| **8** | Context | **Patient Graph** | `Route::PatientGraph` | Native graph projection + `patient_graph.py` | Node selection (Patient, Condition, Observation, Encounter), edge type filter (Explicit FHIR Reference vs Derived Inference) | Session-only | `test_desktop_screens_execution.rs` | Synthetic relationships only; zero external knowledge injection. | **QUALIFIED (Synthetic Adapter)** |
| **9** | Context | **Patient Timeline** | `Route::PatientTimeline` | Native timeline adapter + `encounter.py` | Chronological event stream, category toggle (Encounters, Labs, Vitals), uncertainty flag display | Session-only | `test_desktop_screens_execution.rs` | Synthetic temporal events only. | **QUALIFIED (Synthetic Adapter)** |
| **10** | Context | **Documents & Canvas** | `Route::DocumentsCanvas` | Native document canvas + `draft.py` / `corpus.py` | Structured block view (History, Medications, Assessment), source link viewer, local quarantine warning | Session-only | `test_desktop_screens_execution.rs` | Synthetic research documents only; no patient health records. | **QUALIFIED (Synthetic Adapter)** |
| **11** | Evidence | **Clinical Evidence** | `Route::ClinicalEvidence` | Native evidence adapter + `retrieval.py` / `evidence_strength.py` | Query input, frozen snapshot selector, citation list, contradiction alerts, abstention threshold slider | Session-only | `test_desktop_screens_execution.rs` | Not a clinical decision support or medical answer system. | **QUALIFIED (Synthetic Adapter)** |
| **12** | Evidence | **Literature Screening** | `Route::LiteratureScreening` | Native screening adapter + `src/medscale/litdb` | Inclusion/exclusion criteria toggles, abstract viewer, decision buttons (Include, Exclude, Uncertain), screening receipt export | Session-only | `test_desktop_screens_execution.rs` | Open-source scientific literature workflows only. | **QUALIFIED (Synthetic Adapter)** |
| **13** | Data | **Tables & Structured Data** | `Route::Tables` | Native tabular adapter + `dataset.py` / `analytics.py` | Sortable columns (Code, Date, Value, Unit), category filter, CSV/JSON format preview with boundary verification | Session-only | `test_desktop_screens_execution.rs` | Local tabular projection; zero telemetry. | **QUALIFIED (Synthetic Adapter)** |
| **14** | Data | **FHIR Workspace** | `Route::Records { facet: "All" }` | `synthetic_bundle.rs` | Full FHIR R4 resource tree, bidirectional reference navigation, raw JSON inspection | Session-only | `windows-native-fictional-workspace-uia.ps1` | Synthetic R4 bundles only; structural validation only. | **QUALIFIED (Active)** |
| **15** | Data | **FHIR Fixture Inspector** | `Route::FixtureInspector` (Tag: `Exp`) | In-memory Rust fixture catalog | 12 fixture selectors, SHA-256 verification button, envelope validation display | Session-only | `windows-native-fhir-uia-qualification.ps1` | Native synthetic fixture experiment; not a full validator. | **QUALIFIED (Active)** |
| **16** | Data | **Analytics** | `Route::Analytics` | Native analytics adapter + `analytics.py` | Descriptive cohort metrics (size, condition prevalence, observation count, missingness rate), zero-telemetry badge | Session-only | `test_desktop_screens_execution.rs` | Local calculations only; zero telemetry to Research Core. | **QUALIFIED (Synthetic Adapter)** |
| **17** | Data | **Dataset Manager** | `Route::DatasetManager` | Native dataset adapter + `src/medscale/dataset` | Dual-domain dataset browser (Research Benchmark vs Workspace Export), domain isolation verification | Session-only | `test_desktop_screens_execution.rs` | Strict domain boundary: no implicit cross-domain copy. | **QUALIFIED (Synthetic Adapter)** |
| **18** | Data | **Export Quarantine** | `Route::ExportQuarantine` | Native quarantine adapter + `nobackflow.py` / `lifecycle.py` | Outbound export inspection, residual-risk scanner (zero PHI), quarantine manifest generator, disabled Research admission gate | Session-only | `test_desktop_screens_execution.rs` | Export quarantine; Research Core backflow permanently blocked. | **QUALIFIED (Synthetic Adapter)** |
| **19** | Research | **Research Explorer** | `Route::ResearchExplorer` | Native research adapter + `src/medscale/research` | Read-only study design viewer, hypothesis inspector, experiment configuration, cryptographic provenance hash | Read-only | `test_desktop_screens_execution.rs` | Read-only research view; Lane B invariants preserved. | **QUALIFIED (Synthetic Adapter)** |
| **20** | Research | **Benchmark & Evaluation** | `Route::BenchmarkEvaluation` | Native benchmark adapter + `src/medscale/bench` | Benchmark scorecard browser, seed lock display, deterministic evaluation receipts | Read-only | `test_desktop_screens_execution.rs` | Model training and model promotion permanently gated. | **QUALIFIED (Synthetic Adapter)** |
| **21** | Research | **Model Catalog & Runtime** | `Route::Unavailable` (Tag: `Gated`) | `modelkit` (Specification only) | None (Disabled with explanation) | None | `screens.rs::tests::tags_match_the_design_board_and_gates_are_disabled` | **GATED (Lane B):** Running models or claiming installed models is prohibited. | **GATED (Compliant)** |
| **22** | Trust | **Integrations** | `Route::Integrations` | Native connector adapter + `connector.py` | Mock endpoint directory (Mock FHIR R4, Synthetic Fixture Provider), permission matrix, dry-run simulation button | Session-only | `test_desktop_screens_execution.rs` | EHR write permanently gated; dry-run synthetic only. | **QUALIFIED (Synthetic Adapter)** |
| **23** | Trust | **Audit History** | `Route::AuditHistory` | Native audit adapter + `audit.py` / `provenance.py` | Append-only event viewer, hash-chain inspector, event sequence IDs, "Verify Chain Integrity" button | Session-only | `test_desktop_screens_execution.rs` | Cryptographic SHA-256 append-only ledger. | **QUALIFIED (Synthetic Adapter)** |
| **24** | Trust | **Storage & Recovery** | `Route::StorageRecovery` | Native vault adapter + `storage.py` / `keyprovider.py` | AES-256-GCM vault status, DPAPI key provider status, backup integrity verification, cryptographic zero-wipe simulation | Session-only | `test_desktop_screens_execution.rs` | Ephemeral & test vault simulation only; no production keys. | **QUALIFIED (Synthetic Adapter)** |
| **25** | System | **Settings** | `Route::Settings` | In-memory egui theme settings | System / Light / Dark theme selector, UI density slider, font scaling, offline status indicator | Session-only | `app.rs::settings_ui` | User interface preferences only. | **QUALIFIED (Active)** |
| **26** | System | **About & Diagnostics** | `Route::About` | Embedded build metadata | Version display, commit hash, compiler info, license, "Generate Sanitized Diagnostic Report" button | Read-only | `app.rs::about_ui` | Sanitized diagnostic receipts; zero PHI in logs. | **QUALIFIED (Active)** |
| **27** | System | **Help & Safety** | `Route::Help` | Embedded safety documentation | Safety guidelines, Lane A/B/C boundary rules, incident reporting procedures, keyboard shortcuts reference | Read-only | `app.rs::help_ui` | Safety governance documentation. | **QUALIFIED (Active)** |

---

## 3. Screen Status Summary

- **Total Screens Defined:** 28
- **Active Native Views:** 24 (8 original active + 16 newly connected synthetic adapters)
- **Gated / Deferred Screens:** 4 (strictly preserved with non-clickable status and explicit safety reasons)
  1. *Audio & transcript* (Gated — Lane C microphone capture unqualified)
  2. *Orders & tasks* (Gated — Lane C external EHR writes prohibited)
  3. *Coding suggestions* (Deferred — Lane C billing submission prohibited)
  4. *Model catalog & runtime* (Gated — Lane B unapproved model execution prohibited)
- **Compliance with Governance:** 100% compliant with Lane A, Lane B, and Lane C. Zero fake clinical authorizations, zero unapproved model training, zero live EHR writes.
