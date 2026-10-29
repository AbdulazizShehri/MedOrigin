// Adapted from emilk/eframe_template under Apache-2.0, see UPSTREAM-NOTICE.md.
// Modified: MedOrigin-only synthetic D0 fixtures, no persistence, network or browser UI.
use eframe::egui;
use medorigin_desktop_d0_rust_prototype::hash_fixture_raw_v1;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct FixtureSpec {
    pub id: &'static str,
    pub bytes: usize,
    pub sha256: &'static str,
}

pub const FIXTURES: [FixtureSpec; 4] = [
    FixtureSpec {
        id: "patient-minimal",
        bytes: 57,
        sha256: "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0",
    },
    FixtureSpec {
        id: "patient-invalid-utf8",
        bytes: 1,
        sha256: "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89",
    },
    FixtureSpec {
        id: "patient-over-limit",
        bytes: 32_769,
        sha256: "b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538",
    },
    FixtureSpec {
        id: "patient-exact-limit",
        bytes: 32_768,
        sha256: "ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e",
    },
];

#[derive(Default)]
pub struct MedOriginNativePreview {
    selected: usize,
    result: Option<String>,
}

impl MedOriginNativePreview {
    pub fn hash_selected(&mut self) -> Result<&str, &'static str> {
        let fixture = &FIXTURES[self.selected];
        match hash_fixture_raw_v1(fixture.id, 65_536) {
            Ok(outcome)
                if outcome.bytes == fixture.bytes && outcome.sha256_hex == fixture.sha256 =>
            {
                self.result = Some(format!(
                    "Synthetic raw SHA-256 verified: {}",
                    outcome.sha256_hex
                ));
                Ok(self.result.as_deref().expect("result just set"))
            }
            _ => {
                self.result = Some("FAIL CLOSED: synthetic parity mismatch".to_owned());
                Err("synthetic_parity_mismatch")
            }
        }
    }
}

impl eframe::App for MedOriginNativePreview {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ui, |ui| {
            ui.heading("MedOrigin — Native Rust Experiment");
            ui.strong("Synthetic developer preview only · No EHR · No clinical use");
            ui.label("No browser engine, IPC server, Python worker, filesystem input or model is used in this proof of concept.");
            ui.separator();
            ui.label("Choose one of four fictional, in-memory fixtures:");
            for (index, fixture) in FIXTURES.iter().enumerate() {
                if ui.selectable_label(self.selected == index, format!("{} ({} bytes)", fixture.id, fixture.bytes)).clicked() {
                    self.selected = index;
                    self.result = None;
                }
            }
            if ui.button("Verify synthetic SHA-256").clicked() {
                let _ = self.hash_selected();
            }
            if let Some(result) = &self.result {
                ui.monospace(result);
            }
            ui.separator();
            ui.label("Release: NO-GO · Network isolation: UNQUALIFIED · PHI: PROHIBITED");
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_four_fictional_vectors_match_canonical_d0_without_external_data() {
        for fixture in FIXTURES {
            let output = hash_fixture_raw_v1(fixture.id, 65_536).expect("allowlisted fixture");
            assert_eq!(output.bytes, fixture.bytes);
            assert_eq!(output.sha256_hex, fixture.sha256);
        }
    }

    #[test]
    fn synthetic_ui_view_model_never_uses_unapproved_data() {
        let mut app = MedOriginNativePreview::default();
        for selected in 0..FIXTURES.len() {
            app.selected = selected;
            let actual = app.hash_selected().expect("synthetic fixture must match");
            assert!(actual.contains(FIXTURES[selected].sha256));
        }
    }

    #[test]
    fn unknown_ids_are_rejected_by_the_canonical_d0_contract() {
        assert!(hash_fixture_raw_v1("../records", 65_536).is_err());
    }
}
