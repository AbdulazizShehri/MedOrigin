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
    /// The working FHIR records view. `facet` is the bundle type filter.
    Records {
        facet: &'static str,
    },
    /// Fixture checks and developer receipts (existing developer view).
    FixtureInspector,
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
        NotConnected,
        "Search local records with exact scope and readable provenance.",
        "Foundation in Python Core; desktop adapter pending. Search inside an open bundle is in FHIR workspace.",
        "",
        "retrieval.py, corpus.py",
    ),
    s(
        "Clinical",
        "Synthetic patients",
        None,
        Records { facet: "Patient" },
        "Synthetic records list, search, provenance and detail.",
        "Foundation; UI adapter pending. Shows patients from an open fictional bundle.",
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
        NotConnected,
        "Source-linked editable draft with missing-information indicators; review only.",
        "Foundation; synthetic-only. No desktop adapter yet.",
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
        NotConnected,
        "Graph of linked records with extracted versus inferred edges.",
        "Foundation; synthetic only. Reference links can be followed in FHIR workspace.",
        "",
        "patient_graph.py, linked_workspace.py",
    ),
    s(
        "Context",
        "Patient timeline",
        None,
        NotConnected,
        "Chronological events with drill-down and visible uncertainty.",
        "Foundation; desktop adapter pending.",
        "",
        "patient_graph.py, encounter.py",
    ),
    s(
        "Context",
        "Documents & canvas",
        None,
        NotConnected,
        "Structured notes, source links and local object blocks.",
        "Partial foundation / designed.",
        "",
        "draft.py, corpus.py",
    ),
    s(
        "Evidence",
        "Clinical evidence",
        None,
        NotConnected,
        "Query, frozen snapshot, citations, contradictions and abstention.",
        "Foundation; not a medical answer guarantee. Desktop adapter pending.",
        "",
        "retrieval.py, corpus.py, evidence_strength.py",
    ),
    s(
        "Evidence",
        "Literature screening",
        None,
        NotConnected,
        "Results, screening criteria, provenance and export preview.",
        "Foundation; read-only first. Desktop adapter pending.",
        "",
        "src/medscale/litdb, screen.py",
    ),
    s(
        "Data",
        "Tables & structured data",
        None,
        NotConnected,
        "Queryable local tables with export preview and boundaries.",
        "Foundation; desktop adapter pending.",
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
        NotConnected,
        "Workspace-only indicators and local calculations with provenance.",
        "Foundation; no telemetry. Desktop adapter pending.",
        "",
        "analytics.py",
    ),
    s(
        "Data",
        "Dataset manager",
        None,
        NotConnected,
        "Keep Research datasets and Workspace export staging apart.",
        "Foundation; no implicit cross-domain copy. Desktop adapter pending.",
        "",
        "dataset.py, src/medscale/dataset",
    ),
    s(
        "Data",
        "Export quarantine",
        None,
        NotConnected,
        "Explicit target, preview, residual-risk result and quarantine manifest.",
        "Foundation; Research admission gated. Desktop adapter pending.",
        "",
        "nobackflow.py, dataset.py, lifecycle.py",
    ),
    s(
        "Research",
        "Research explorer",
        None,
        NotConnected,
        "Read-only hypotheses, experiment artifacts and source-bound status.",
        "Foundation; read-only. Desktop adapter pending.",
        "",
        "research_view.py, src/medscale/research",
    ),
    s(
        "Research",
        "Benchmark & evaluation",
        None,
        NotConnected,
        "Inspect trusted results and frozen evaluator versions.",
        "Foundation; training and model promotion gated. Desktop adapter pending.",
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
        NotConnected,
        "Capability listing, consent and permissions, read-only dry run.",
        "Foundation contracts; EHR read later, EHR write gated. Desktop adapter pending.",
        "",
        "connector.py, fhir_r4.py",
    ),
    s(
        "Trust",
        "Audit history",
        None,
        NotConnected,
        "Append-only events, source identity, revisions and failure traces.",
        "Foundation; desktop adapter pending.",
        "",
        "audit.py, provenance.py",
    ),
    s(
        "Trust",
        "Storage & recovery",
        None,
        NotConnected,
        "Encrypted local store, backup and restore, key status, safe deletion.",
        "Foundation; platform secret provider must qualify. This build saves nothing.",
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
}
