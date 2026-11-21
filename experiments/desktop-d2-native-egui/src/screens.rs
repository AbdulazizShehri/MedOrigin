//! The 28 desktop screens from docs/design/desktop-v1/FEATURE_COVERAGE.md,
//! grouped and tagged as on the "Desktop — Encounter review" board.
//! Each one either routes to a working view in this build or shows an
//! accurately labelled status. Gated and deferred screens are disabled.

/// Board tags. `Gated` and `Deferred` screens are never clickable.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Tag {
    Gated,
    Deferred,
    Experiment,
}

impl Tag {
    pub fn label(self) -> &'static str {
        match self {
            Tag::Gated => "Gated",
            Tag::Deferred => "Deferred",
            Tag::Experiment => "Exp",
        }
    }
}

/// What a screen does in this build.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Route {
    Home,
    LocalSearch,
    /// The working FHIR records view. `facet` is the bundle type filter.
    Records {
        facet: &'static str,
    },
    NoteDrafts,
    PatientGraph,
    PatientTimeline,
    DocumentsCanvas,
    ClinicalEvidence,
    LiteratureScreening,
    Tables,
    /// Fixture checks and developer receipts (existing developer view).
    FixtureInspector,
    Analytics,
    DatasetManager,
    ExportQuarantine,
    ResearchExplorer,
    BenchmarkEvaluation,
    Integrations,
    AuditHistory,
    StorageRecovery,
    Settings,
    About,
    Help,
    /// Backend may exist in Python Core, but no desktop adapter yet.
    NotConnected,
    /// Not available: gated or deferred. The reason is shown, never an action.
    Unavailable,
}

#[derive(Clone, Copy, Debug)]
pub struct Screen {
    pub group: &'static str,
    pub label: &'static str,
    pub tag: Option<Tag>,
    pub route: Route,
    /// What the screen is for (FEATURE_COVERAGE "Desktop interaction contract").
    pub purpose: &'static str,
    /// FEATURE_COVERAGE "State / gate", verbatim in meaning.
    pub contract: &'static str,
    /// Why it is gated or deferred; empty otherwise.
    pub reason: &'static str,
    /// Backing modules named by the contract.
    pub sources: &'static str,
}

impl Screen {
    pub fn enabled(&self) -> bool {
        !matches!(self.tag, Some(Tag::Gated | Tag::Deferred))
    }
}

// One positional row per FEATURE_COVERAGE screen keeps the table readable.
#[allow(clippy::too_many_arguments)]
const fn s(
    group: &'static str,
    label: &'static str,
    tag: Option<Tag>,
    route: Route,
    purpose: &'static str,
    contract: &'static str,
    reason: &'static str,
    sources: &'static str,
) -> Screen {
    Screen {
        group,
        label,
        tag,
        route,
        purpose,
        contract,
        reason,
        sources,
    }
}

use Route::*;
use Tag::*;

pub const HOME: usize = 0;
pub const FHIR_WORKSPACE: usize = 14;
pub const FIXTURE_INSPECTOR: usize = 15;
pub const ABOUT: usize = 26;
pub const HELP: usize = 27;

pub const SCREENS: [Screen; 28] = [
    s(
        "Workspace",
        "Home",
        None,
        Home,
        "Workspace health, local state and recent synthetic work.",
        "Designed",
        "",
        "apps/workspace/README.md",
    ),
    s(
        "Workspace",
        "Local search",
        None,
        LocalSearch,
        "Search local records with exact scope and readable provenance.",
        "Foundation in Python Core; connected via synthetic retrieval adapter.",
        "",
        "retrieval.py, corpus.py",
    ),
    s(
        "Clinical",
        "Synthetic patients",
        None,
        Records { facet: "Patient" },
        "Synthetic records list, search, provenance and detail.",
        "Foundation; UI adapter connected. Shows patients from an open fictional bundle.",
        "",
        "identity.py, binding.py, patient_graph.py",
    ),
    s(
        "Clinical",
        "Encounters",
        None,
        Records { facet: "Encounter" },
        "Encounter timeline, status and source drill-down.",
        "Foundation; fixtures only. Shows encounters from an open fictional bundle.",
        "",
        "encounter.py, review.py",
    ),
    s(
        "Clinical",
        "Audio & transcript",
        Some(Gated),
        Unavailable,
        "Transcript review and adapter status.",
        "Foundation contract; capture gated.",
        "Live microphone capture is not qualified. No audio adapter is approved for this build.",
        "asr.py",
    ),
    s(
        "Clinical",
        "Note drafts",
        None,
        NoteDrafts,
        "Source-linked editable draft with missing-information indicators; review only.",
        "Foundation; synthetic-only. Connected via local clinical draft adapter.",
        "",
        "draft.py, review.py",
    ),
    s(
        "Clinical",
        "Orders & tasks",
        Some(Gated),
        Unavailable,
        "Explicit suggestion list with a manual review gate; never auto-submit.",
        "Designed; external write gated.",
        "Writing orders or tasks to any external system is not authorized.",
        "Clinical workspace roadmap 4.2",
    ),
    s(
        "Clinical",
        "Coding suggestions",
        Some(Deferred),
        Unavailable,
        "Source and rationale with human acknowledgement; no billing submission.",
        "Deferred / gated.",
        "Outside the currently authorized scope. Billing submission is never available.",
        "Clinical workspace capability map",
    ),
    s(
        "Context",
        "Patient graph",
        None,
        PatientGraph,
        "Graph of linked records with extracted versus inferred edges.",
        "Foundation; synthetic only. Connected via patient relation graph adapter.",
        "",
        "patient_graph.py, linked_workspace.py",
    ),
    s(
        "Context",
        "Patient timeline",
        None,
        PatientTimeline,
        "Chronological events with drill-down and visible uncertainty.",
        "Foundation; connected via patient timeline adapter.",
        "",
        "patient_graph.py, encounter.py",
    ),
    s(
        "Context",
        "Documents & canvas",
        None,
        DocumentsCanvas,
        "Structured notes, source links and local object blocks.",
        "Partial foundation; connected via structured document canvas adapter.",
        "",
        "draft.py, corpus.py",
    ),
    s(
        "Evidence",
        "Clinical evidence",
        None,
        ClinicalEvidence,
        "Query, frozen snapshot, citations, contradictions and abstention.",
        "Foundation; connected via clinical evidence retrieval adapter.",
        "",
        "retrieval.py, corpus.py, evidence_strength.py",
    ),
    s(
        "Evidence",
        "Literature screening",
        None,
        LiteratureScreening,
        "Results, screening criteria, provenance and export preview.",
        "Foundation; read-only. Connected via LitDB literature screening adapter.",
        "",
        "src/medscale/litdb, screen.py",
    ),
    s(
        "Data",
        "Tables & structured data",
        None,
        Tables,
        "Queryable local tables with export preview and boundaries.",
        "Foundation; connected via structured tabular data adapter.",
        "",
        "dataset.py, analytics.py",
    ),
    s(
        "Data",
        "FHIR workspace",
        None,
        Records { facet: "All" },
        "Open a fictional FHIR R4 bundle and browse it with provenance.",
        "Foundation; synthetic-only. Working in this build for fictional bundles.",
        "",
        "fhir_r4.py, src/medscale/fhirkit",
    ),
    s(
        "Data",
        "FHIR fixture inspector",
        Some(Experiment),
        FixtureInspector,
        "Native synthetic FHIR examples with verified hashes.",
        "Experiment; not a full validator.",
        "",
        "D2 native Rust experiment",
    ),
    s(
        "Data",
        "Analytics",
        None,
        Analytics,
        "Workspace-only indicators and local calculations with provenance.",
        "Foundation; no telemetry. Connected via workspace descriptive analytics adapter.",
        "",
        "analytics.py",
    ),
    s(
        "Data",
        "Dataset manager",
        None,
        DatasetManager,
        "Keep Research datasets and Workspace export staging apart.",
        "Foundation; connected via dual-domain dataset management adapter.",
        "",
        "dataset.py, src/medscale/dataset",
    ),
    s(
        "Data",
        "Export quarantine",
        None,
        ExportQuarantine,
        "Explicit target, preview, residual-risk result and quarantine manifest.",
        "Foundation; Research admission gated. Connected via outbound export quarantine adapter.",
        "",
        "nobackflow.py, dataset.py, lifecycle.py",
    ),
    s(
        "Research",
        "Research explorer",
        None,
        ResearchExplorer,
        "Read-only hypotheses, experiment artifacts and source-bound status.",
        "Foundation; read-only. Connected via research artifact explorer adapter.",
        "",
        "research_view.py, src/medscale/research",
    ),
    s(
        "Research",
        "Benchmark & evaluation",
        None,
        BenchmarkEvaluation,
        "Inspect trusted results and frozen evaluator versions.",
        "Foundation; training/promotion gated. Connected via benchmark scorecard adapter.",
        "",
        "src/medscale/bench, mesc, modelkit",
    ),
    s(
        "Research",
        "Model catalog & runtime",
        Some(Gated),
        Unavailable,
        "Available local adapters and their identity.",
        "Partial foundation; execution gated.",
        "Running models is not authorized in this build. MedOrigin never claims a model is installed.",
        "modelkit, asr.py",
    ),
    s(
        "Trust",
        "Integrations",
        None,
        Integrations,
        "Capability listing, consent and permissions, read-only dry run.",
        "Foundation contracts; connected via mock integration status adapter.",
        "",
        "connector.py, fhir_r4.py",
    ),
    s(
        "Trust",
        "Audit history",
        None,
        AuditHistory,
        "Append-only events, source identity, revisions and failure traces.",
        "Foundation; connected via cryptographic audit history adapter.",
        "",
        "audit.py, provenance.py",
    ),
    s(
        "Trust",
        "Storage & recovery",
        None,
        StorageRecovery,
        "Encrypted local store, backup and restore, key status, safe deletion.",
        "Foundation; connected via encrypted storage and recovery adapter.",
        "",
        "storage.py, lifecycle.py, keyprovider.py",
    ),
    s(
        "System",
        "Settings",
        None,
        Settings,
        "Appearance and offline state.",
        "Designed.",
        "",
        "versions.py",
    ),
    s(
        "System",
        "About & diagnostics",
        None,
        About,
        "App build, provenance and a sanitized issue report.",
        "Designed.",
        "",
        "Core version, CITATION.cff, lockfiles",
    ),
    s(
        "System",
        "Help & safety",
        None,
        Help,
        "Research-only, synthetic-only, no EHR writes, incident workflow.",
        "Required.",
        "",
        "SECURITY.md, governance",
    ),
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_28_feature_coverage_screens_are_listed_once() {
        let coverage = include_str!("../../../docs/design/desktop-v1/FEATURE_COVERAGE.md");
        let rows = coverage
            .lines()
            .filter(|l| l.starts_with("| **") && !l.contains("Section / screen"))
            .count();
        assert_eq!(rows, SCREENS.len());
        let mut labels: Vec<_> = SCREENS.iter().map(|s| s.label).collect();
        labels.sort_unstable();
        labels.dedup();
        assert_eq!(labels.len(), 28);
    }

    #[test]
    fn tags_match_the_design_board_and_gates_are_disabled() {
        let tagged: Vec<_> = SCREENS
            .iter()
            .filter_map(|s| s.tag.map(|t| (s.label, t)))
            .collect();
        assert_eq!(
            tagged,
            [
                ("Audio & transcript", Tag::Gated),
                ("Orders & tasks", Tag::Gated),
                ("Coding suggestions", Tag::Deferred),
                ("FHIR fixture inspector", Tag::Experiment),
                ("Model catalog & runtime", Tag::Gated),
            ]
        );
        for screen in &SCREENS {
            let blocked = matches!(screen.tag, Some(Tag::Gated | Tag::Deferred));
            assert_eq!(screen.enabled(), !blocked, "{}", screen.label);
            assert_eq!(
                blocked,
                screen.route == Route::Unavailable,
                "{}",
                screen.label
            );
            assert_eq!(blocked, !screen.reason.is_empty(), "{}", screen.label);
        }
    }

    #[test]
    fn named_indices_point_at_their_screens() {
        assert_eq!(SCREENS[HOME].label, "Home");
        assert_eq!(SCREENS[FHIR_WORKSPACE].label, "FHIR workspace");
        assert_eq!(SCREENS[FIXTURE_INSPECTOR].label, "FHIR fixture inspector");
        assert_eq!(SCREENS[ABOUT].label, "About & diagnostics");
        assert_eq!(SCREENS[HELP].label, "Help & safety");
    }

    #[test]
    fn exactly_24_screens_are_active_and_4_are_gated_or_deferred() {
        let active = SCREENS.iter().filter(|s| s.enabled()).count();
        let gated_or_deferred = SCREENS.iter().filter(|s| !s.enabled()).count();
        assert_eq!(active, 24);
        assert_eq!(gated_or_deferred, 4);
        assert_eq!(
            SCREENS
                .iter()
                .filter(|s| s.route == Route::NotConnected)
                .count(),
            0
        );
    }
}
