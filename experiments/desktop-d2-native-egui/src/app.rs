// Adapted from emilk/eframe_template under Apache-2.0, see UPSTREAM-NOTICE.md.
// Synthetic-only, in-process native Rust eframe + D0; no browser, EHR, PHI or network.
use eframe::egui;
use medorigin_desktop_d0_rust_prototype::{
    hash_fixture_raw_v1, inspect_named_synthetic_fhir_envelope_v1,
};
#[cfg(test)]
use std::collections::HashSet;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FixtureSpec {
    pub id: &'static str,
    pub bytes: usize,
    pub sha256: &'static str,
    pub status: &'static str,
}

pub const PRIMARY_FIXTURE_COUNT: usize = 4;
pub const FIXTURES: [FixtureSpec; 12] = [
    FixtureSpec {
        id: "patient-minimal",
        bytes: 57,
        sha256: "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0",
        status: "FHIR_ENVELOPE_OK",
    },
    FixtureSpec {
        id: "patient-invalid-utf8",
        bytes: 1,
        sha256: "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89",
        status: "INVALID_UTF8",
    },
    FixtureSpec {
        id: "patient-over-limit",
        bytes: 32769,
        sha256: "b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538",
        status: "RESOURCE_TOO_LARGE",
    },
    FixtureSpec {
        id: "patient-exact-limit",
        bytes: 32768,
        sha256: "ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e",
        status: "FHIR_ENVELOPE_OK",
    },
    FixtureSpec {
        id: "observation-minimal",
        bytes: 251,
        sha256: "527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19",
        status: "FHIR_ENVELOPE_OK",
    },
    FixtureSpec {
        id: "observation-bad-subject",
        bytes: 253,
        sha256: "d2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838",
        status: "INVALID_REFERENCE",
    },
    FixtureSpec {
        id: "bundle-valid",
        bytes: 531,
        sha256: "3a530a66c0f2b71908b1282985432e405f0f2f412c7ccc0143aa1972d9447983",
        status: "BUNDLE_GRAPH_OK",
    },
    FixtureSpec {
        id: "bundle-bad-reference",
        bytes: 528,
        sha256: "4aabcfa54309c83052d62b4fdcf1c6635a6cd3d937551e2ab947899345f9f082",
        status: "INVALID_REFERENCE",
    },
    FixtureSpec {
        id: "bundle-duplicate",
        bytes: 531,
        sha256: "813f8a3b8fee59ba74abdb293c6cac5cca103b390153730e6e3bc4656540f15b",
        status: "DUPLICATE_ENTRY",
    },
    FixtureSpec {
        id: "bundle-wrong-type",
        bytes: 532,
        sha256: "293c10c8abf055e8c1f84bae4913c7246bf9be5bf53dee0fb3c918e32a8346a7",
        status: "INVALID_BUNDLE_TYPE",
    },
    FixtureSpec {
        id: "bundle-linked",
        bytes: 559,
        sha256: "1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88",
        status: "BUNDLE_GRAPH_OK",
    },
    FixtureSpec {
        id: "bundle-dangling",
        bytes: 559,
        sha256: "1bbc0bac94b3ff19dce3502164f3243748cf5aa7e869433bdb09e7ec2266b229",
        status: "INVALID_REFERENCE",
    },
];

#[derive(Default)]
pub struct MedOriginNativePreview {
    selected: usize,
    result: Option<String>,
}

impl MedOriginNativePreview {
    /// Fail closed if either the trusted raw digest OR the independent
    /// structural outcome differs from the compiled fictional fixture catalog.
    /// A structurally invalid fixture is a correctly identified NEGATIVE test,
    /// not a clinically validated resource.
    pub fn hash_selected(&mut self) -> Result<&str, &'static str> {
        self.result = None;
        let Some(fixture) = FIXTURES.get(self.selected) else {
            self.result = Some("FAIL CLOSED: invalid synthetic selection".to_owned());
            return Err("invalid_synthetic_selection");
        };
        let (Ok(digest), Ok(envelope)) = (
            hash_fixture_raw_v1(fixture.id, 65_536),
            inspect_named_synthetic_fhir_envelope_v1(fixture.id, 65_536),
        ) else {
            self.result = Some("FAIL CLOSED: fictional Rust verification failed".to_owned());
            return Err("synthetic_verification_failed");
        };
        if digest.contract != "medorigin-desktop-d0-raw-sha256-v1"
            || digest.fixture_id != fixture.id
            || digest.bytes != fixture.bytes
            || digest.sha256_hex != fixture.sha256
            || envelope.contract != "medorigin-d0-synthetic-fhir-envelope-v1"
            || envelope.fixture_id != fixture.id
            || envelope.bytes != fixture.bytes
            || envelope.status != fixture.status
            || !envelope.synthetic_only
            || envelope.full_fhir_r4_validated
            || envelope.release_authorized
        {
            self.result = Some("FAIL CLOSED: synthetic parity mismatch".to_owned());
            return Err("synthetic_parity_mismatch");
        }
        self.result = Some(format!(
            "Synthetic raw SHA-256 verified: {}\nFictional FHIR envelope: {} (NOT full FHIR R4 validation)",
            digest.sha256_hex, envelope.status
        ));
        Ok(self
            .result
            .as_deref()
            .expect("just assigned verified result"))
    }
}

impl eframe::App for MedOriginNativePreview {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ui, |ui| {
            ui.heading("MedOrigin — Native Rust Experiment");
            ui.strong("Synthetic developer preview only · No EHR · No clinical use");
            ui.label("No browser engine, IPC server, Python worker, filesystem input or model is used in this proof of concept.");
            ui.separator();
            // Keep all four original controls visible in the same order.
            // This retains the testable AX/UIA keyboard contract from D2.
            ui.label("Choose one of four fictional, in-memory fixtures:");
            for (index, fixture) in FIXTURES[..PRIMARY_FIXTURE_COUNT].iter().enumerate() {
                if ui.selectable_label(self.selected == index, format!("{} ({} bytes)", fixture.id, fixture.bytes)).clicked() {
                    self.selected = index;
                    self.result = None;
                }
            }
            if ui.button("Verify synthetic SHA-256").clicked() {
                let _ = self.hash_selected();
            }
            if let Some(result) = &self.result {
                // Preserve the original standalone UIA/AX SHA text node. The
                // FHIR status is a distinct accessible node for screen readers.
                for line in result.lines() {
                    ui.monospace(line);
                }
            }
            egui::CollapsingHeader::new("Additional fictional FHIR/Bundle cases (8)")
                .default_open(false)
                .show(ui, |ui| {
                    for (offset, fixture) in FIXTURES[PRIMARY_FIXTURE_COUNT..].iter().enumerate() {
                        let index = PRIMARY_FIXTURE_COUNT + offset;
                        if ui.selectable_label(self.selected == index, format!("{} ({} bytes)", fixture.id, fixture.bytes)).clicked() {
                            self.selected = index;
                            self.result = None;
                        }
                    }
                });
            ui.separator();
            ui.label("FHIR structural checks only · Release: NO-GO · Network isolation: UNQUALIFIED · PHI: PROHIBITED");
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_twelve_fictional_vectors_match_compiled_sha_and_expected_envelope_status() {
        assert_eq!(FIXTURES.len(), 12);
        let mut seen = HashSet::new();
        for fixture in FIXTURES {
            assert!(seen.insert(fixture.id), "duplicate static fixture ID");
            let digest = hash_fixture_raw_v1(fixture.id, 65_536).expect("known fictional fixture");
            let envelope = inspect_named_synthetic_fhir_envelope_v1(fixture.id, 65_536)
                .expect("known fictional fixture");
            assert_eq!(digest.bytes, fixture.bytes);
            assert_eq!(digest.sha256_hex, fixture.sha256);
            assert_eq!(envelope.bytes, fixture.bytes);
            assert_eq!(envelope.status, fixture.status);
            assert!(envelope.synthetic_only);
            assert!(!envelope.full_fhir_r4_validated);
            assert!(!envelope.release_authorized);
        }
    }

    #[test]
    fn synthetic_ui_view_model_never_uses_unapproved_data() {
        let mut app = MedOriginNativePreview::default();
        for (selected, fixture) in FIXTURES.iter().enumerate() {
            app.selected = selected;
            let actual = app.hash_selected().expect("synthetic fixture must match");
            assert!(actual.contains(fixture.sha256));
            assert!(actual.contains(fixture.status));
        }
        // State cannot become a panic or silently reuse prior success.
        app.selected = usize::MAX;
        assert_eq!(app.hash_selected(), Err("invalid_synthetic_selection"));
        assert!(!app.result.as_deref().unwrap().contains("verified"));
    }

    #[test]
    fn unknown_ids_are_rejected_by_the_canonical_d0_contract() {
        for id in [
            "../records",
            "file:///patient.json",
            "https://example.org/fhir/Patient/1",
        ] {
            assert!(hash_fixture_raw_v1(id, 65_536).is_err());
            assert!(inspect_named_synthetic_fhir_envelope_v1(id, 65_536).is_err());
        }
    }

    #[test]
    fn original_accessibility_fixture_order_is_stable() {
        assert_eq!(PRIMARY_FIXTURE_COUNT, 4);
        assert_eq!(FIXTURES[0].id, "patient-minimal");
        assert_eq!(FIXTURES[1].id, "patient-invalid-utf8");
        assert_eq!(FIXTURES[2].id, "patient-over-limit");
        assert_eq!(FIXTURES[3].id, "patient-exact-limit");
        assert_eq!(FIXTURES[10].status, "BUNDLE_GRAPH_OK");
        assert_eq!(FIXTURES[11].status, "INVALID_REFERENCE");
    }
}
