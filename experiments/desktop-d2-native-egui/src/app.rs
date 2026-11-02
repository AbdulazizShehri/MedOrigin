// Adapted from emilk/eframe_template under Apache-2.0, see UPSTREAM-NOTICE.md.
// Synthetic-only, in-process native Rust eframe + D0; no browser, EHR, PHI or network.
use eframe::egui;
use medorigin_desktop_d0_rust_prototype::{
    HashError, fictional_json_preview_v1, hash_fixture_raw_v1,
    inspect_named_synthetic_fhir_envelope_v1,
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

#[derive(Clone, Debug)]
struct FictionalComparison {
    left: FixtureSpec,
    right: FixtureSpec,
    left_json: &'static str,
    right_json: &'static str,
    byte_diff_summary: String,
    byte_context: String,
    json_path_diff: String,
}

/// Byte offsets are intentionally zero-based source bytes, not UTF-8 characters.
/// The two inputs have already passed the fixed fictional SHA/envelope contracts.
fn fictional_byte_diff_summary(left: &str, right: &str) -> String {
    let a = left.as_bytes();
    let b = right.as_bytes();
    let prefix = a.iter().zip(b).take_while(|(x, y)| x == y).count();
    if prefix == a.len() && prefix == b.len() {
        return format!("Fictional byte comparison: identical ({} bytes)", a.len());
    }
    let suffix = a[prefix..]
        .iter()
        .rev()
        .zip(b[prefix..].iter().rev())
        .take_while(|(x, y)| x == y)
        .count();
    format!(
        "Fictional byte difference: first differing byte offset {prefix} (zero-based); common suffix {suffix} bytes; left {} bytes, right {} bytes. Original source bytes unchanged.",
        a.len(),
        b.len()
    )
}

/// Bounded HEX around the first changed UTF-8 source byte, not a JSON semantic diff.
fn fictional_byte_context(left: &str, right: &str) -> String {
    let a = left.as_bytes();
    let b = right.as_bytes();
    let offset = a.iter().zip(b).take_while(|(x, y)| x == y).count();
    if offset == a.len() && offset == b.len() {
        return "Fictional HEX context: identical source bytes".to_owned();
    }
    fn window(bytes: &[u8], offset: usize) -> String {
        let start = offset.saturating_sub(8);
        let end = bytes.len().min(offset.saturating_add(8));
        let hex = bytes[start..end]
            .iter()
            .map(|byte| format!("{byte:02X}"))
            .collect::<Vec<_>>()
            .join(" ");
        format!("bytes {start}..{end} [HEX {hex}]")
    }
    format!(
        "Fictional HEX context at zero-based byte {offset}: left {}; right {}. Raw bytes only, not JSON semantics.",
        window(a, offset),
        window(b, offset)
    )
}

/// A deterministic, bounded JSON Pointer summary for already verified
/// source-compiled fictional payloads. Never loads external JSON or treats
/// structural comparisons as clinical FHIR validation.
fn fictional_json_path_diff(left: &str, right: &str) -> Result<String, &'static str> {
    use serde_json::Value;

    fn pointer_segment(key: &str) -> String {
        key.replace('~', "~0").replace('/', "~1")
    }

    fn first_diff(
        a: &Value,
        b: &Value,
        path: &str,
        depth: usize,
    ) -> Result<Option<(String, &'static str)>, &'static str> {
        if depth > 32 {
            return Err("fictional_json_depth_exceeded");
        }
        match (a, b) {
            (Value::Object(left), Value::Object(right)) => {
                // Shared keys first, sorted by name, so differences in the
                // same field take precedence over unrelated missing fields.
                let mut shared: Vec<_> =
                    left.keys().filter(|key| right.contains_key(*key)).collect();
                shared.sort();
                for key in shared {
                    let next = format!("{path}/{}", pointer_segment(key));
                    if let Some(diff) = first_diff(&left[key], &right[key], &next, depth + 1)? {
                        return Ok(Some(diff));
                    }
                }
                let mut missing: Vec<_> = left
                    .keys()
                    .chain(right.keys())
                    .filter(|key| !left.contains_key(*key) || !right.contains_key(*key))
                    .collect();
                missing.sort();
                if let Some(key) = missing.first() {
                    return Ok(Some((
                        format!("{path}/{}", pointer_segment(key)),
                        "field missing on one side",
                    )));
                }
                Ok(None)
            }
            (Value::Array(left), Value::Array(right)) => {
                for (index, (a, b)) in left.iter().zip(right).enumerate() {
                    let next = format!("{path}/{index}");
                    if let Some(diff) = first_diff(a, b, &next, depth + 1)? {
                        return Ok(Some(diff));
                    }
                }
                if left.len() != right.len() {
                    return Ok(Some((
                        format!("{path}/{}", left.len().min(right.len())),
                        "array length differs",
                    )));
                }
                Ok(None)
            }
            _ if a == b => Ok(None),
            _ => {
                let kind = if std::mem::discriminant(a) == std::mem::discriminant(b) {
                    "value differs"
                } else {
                    "JSON type differs"
                };
                Ok(Some((
                    if path.is_empty() {
                        "/".to_owned()
                    } else {
                        path.to_owned()
                    },
                    kind,
                )))
            }
        }
    }

    let a: Value = serde_json::from_str(left).map_err(|_| "fictional_json_parse_refused")?;
    let b: Value = serde_json::from_str(right).map_err(|_| "fictional_json_parse_refused")?;
    let summary = match first_diff(&a, &b, "", 0)? {
        Some((pointer, kind)) => format!(
            "Fictional JSON path difference: {pointer} ({kind}). Structural developer hint only; original source bytes unchanged."
        ),
        None => "Fictional JSON path difference: structurally identical; original source bytes may differ.".to_owned(),
    };
    Ok(summary)
}

#[derive(Default)]
pub struct MedOriginNativePreview {
    selected: usize,
    compare_with: usize,
    result: Option<String>,
    preview: Option<String>,
    preview_notice: Option<&'static str>,
    comparison: Option<FictionalComparison>,
}

impl MedOriginNativePreview {
    /// Fail closed if either the trusted raw digest OR the independent
    /// structural outcome differs from the compiled fictional fixture catalog.
    /// A structurally invalid fixture is a correctly identified NEGATIVE test,
    /// not a clinically validated resource.
    pub fn hash_selected(&mut self) -> Result<&str, &'static str> {
        self.result = None;
        self.preview = None;
        self.preview_notice = None;
        self.comparison = None;
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

    /// Expose ONLY source-compiled fictional JSON, after re-verifying the raw
    /// SHA and limited envelope contract for this exact selected fixture.
    /// This neither loads real user files nor exports a resource.
    pub fn preview_selected(&mut self) -> Result<&str, &'static str> {
        // Must reset stale data even when a preceding selection is invalid.
        self.preview = None;
        self.preview_notice = None;
        if self.hash_selected().is_err() {
            return Err("synthetic_verification_failed");
        }
        let fixture = FIXTURES
            .get(self.selected)
            .ok_or("invalid_synthetic_selection")?;
        let payload = match fictional_json_preview_v1(fixture.id) {
            Ok(payload) => payload,
            Err(HashError::PreviewUnavailable) => {
                self.preview_notice =
                    Some("No JSON preview for this raw-byte boundary test fixture.");
                return Err("preview_unavailable");
            }
            Err(_) => {
                self.result = Some("FAIL CLOSED: fictional preview refused".to_owned());
                return Err("synthetic_preview_refused");
            }
        };
        if payload.contract != "medorigin-d0-fictional-json-preview-v1"
            || payload.fixture_id != fixture.id
            || payload.bytes != fixture.bytes
            || payload.sha256_hex != fixture.sha256
            || payload.raw_json.len() != fixture.bytes
            || !payload.synthetic_only
            || payload.release_authorized
        {
            self.result = Some("FAIL CLOSED: fictional preview bytes mismatch".to_owned());
            return Err("synthetic_preview_mismatch");
        }
        self.preview = Some(payload.raw_json.to_owned());
        Ok(self
            .preview
            .as_deref()
            .expect("just assigned bounded fictional JSON"))
    }

    /// A second independent verification, never trusting previously displayed
    /// UI state. The only inputs are source-compiled fictional fixture IDs.
    fn verified_json_for(index: usize) -> Result<&'static str, &'static str> {
        let fixture = FIXTURES.get(index).ok_or("invalid_synthetic_selection")?;
        if fixture.bytes > 2_048 {
            return Err("preview_unavailable");
        }
        let digest =
            hash_fixture_raw_v1(fixture.id, 65_536).map_err(|_| "synthetic_verification_failed")?;
        let envelope = inspect_named_synthetic_fhir_envelope_v1(fixture.id, 65_536)
            .map_err(|_| "synthetic_verification_failed")?;
        let payload = fictional_json_preview_v1(fixture.id).map_err(|_| "preview_unavailable")?;
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
            || payload.contract != "medorigin-d0-fictional-json-preview-v1"
            || payload.fixture_id != fixture.id
            || payload.bytes != fixture.bytes
            || payload.sha256_hex != fixture.sha256
            || payload.raw_json.len() != fixture.bytes
            || !payload.synthetic_only
            || payload.release_authorized
        {
            return Err("synthetic_comparison_mismatch");
        }
        Ok(payload.raw_json)
    }

    /// Compare two distinct, independently reverified source-fixed fictional
    /// JSON texts. Never reads files, copies to clipboard or normalizes bytes.
    pub fn compare_selected(&mut self) -> Result<(), &'static str> {
        self.comparison = None;
        self.preview = None;
        self.preview_notice = None;
        if self.hash_selected().is_err() {
            return Err("synthetic_verification_failed");
        }
        if self.selected == self.compare_with {
            self.result = Some("FAIL CLOSED: choose two distinct fictional fixtures".to_owned());
            return Err("comparison_requires_distinct_fixtures");
        }
        let (Ok(left_json), Ok(right_json)) = (
            Self::verified_json_for(self.selected),
            Self::verified_json_for(self.compare_with),
        ) else {
            self.result = Some("FAIL CLOSED: fictional comparison refused".to_owned());
            return Err("synthetic_comparison_refused");
        };
        let left = FIXTURES[self.selected];
        let right = FIXTURES[self.compare_with];
        let json_path_diff = match fictional_json_path_diff(left_json, right_json) {
            Ok(summary) => summary,
            Err(_) => {
                self.result =
                    Some("FAIL CLOSED: fictional JSON path comparison refused".to_owned());
                return Err("synthetic_json_path_refused");
            }
        };
        self.comparison = Some(FictionalComparison {
            left,
            right,
            left_json,
            right_json,
            byte_diff_summary: fictional_byte_diff_summary(left_json, right_json),
            byte_context: fictional_byte_context(left_json, right_json),
            json_path_diff,
        });
        Ok(())
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
                    self.preview = None;
                    self.preview_notice = None;
                    self.comparison = None;
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
                            self.preview = None;
                            self.preview_notice = None;
                            self.comparison = None;
                        }
                    }
                });
            // An explicit opt-in source-only read-only preview, never a user
            // file import. Preserve existing 4 primary controls and Verify
            // order for UIA, AX and AT-SPI keyboard qualification.
            if ui.button("Inspect fictional JSON (verified, read-only)").clicked() {
                let _ = self.preview_selected();
            }
            if let Some(notice) = self.preview_notice {
                ui.label(notice);
            }
            if let Some(raw) = &self.preview {
                ui.label("Raw fictional source JSON - no normalization or FHIR R4 validation");
                egui::ScrollArea::vertical()
                    .max_height(160.0)
                    .show(ui, |ui| {
                        ui.monospace(raw);
                    });
            }
            ui.separator();
            ui.label("Compare two independently verified fictional JSON sources (read-only):");
            ui.label(format!(
                "Second fictional selection: {}",
                FIXTURES
                    .get(self.compare_with)
                    .map_or("Invalid fictional selection", |fixture| fixture.id)
            ));
            // Use the same accessible button semantics as the original
            // selectors. egui ComboBox did not expose an actionable Windows
            // UIA ExpandCollapsePattern in the real native probe.
            egui::CollapsingHeader::new("Choose second fictional fixture (9)")
                .default_open(false)
                .show(ui, |ui| {
                    for (index, fixture) in FIXTURES.iter().enumerate() {
                        if fixture.bytes <= 2_048
                            && ui
                                .selectable_label(
                                    self.compare_with == index,
                                    format!("Compare: {}", fixture.id),
                                )
                                .clicked()
                        {
                            self.compare_with = index;
                            self.comparison = None;
                        }
                    }
                });
            if ui.button("Compare verified fictional JSON (read-only)").clicked() {
                let _ = self.compare_selected();
            }
            if let Some(comparison) = &self.comparison {
                ui.label("Both sources independently reverified · Negative FHIR statuses are expected test cases, not clinical conclusions");
                ui.monospace(&comparison.byte_diff_summary);
                ui.monospace(&comparison.byte_context);
                ui.monospace(&comparison.json_path_diff);
                ui.columns(2, |columns| {
                    let (left, right) = columns.split_at_mut(1);
                    for (column, fixture, raw) in [
                        (&mut left[0], comparison.left, comparison.left_json),
                        (&mut right[0], comparison.right, comparison.right_json),
                    ] {
                        column.strong(fixture.id);
                        column.label(format!("Fictional envelope: {}", fixture.status));
                        column.monospace(format!("SHA-256: {}", fixture.sha256));
                        egui::ScrollArea::vertical()
                            .max_height(160.0)
                            .show(column, |ui| {
                                ui.monospace(raw);
                            });
                    }
                });
            }
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
    fn nine_fictional_previews_are_raw_exact_verified_and_read_only() {
        let mut app = MedOriginNativePreview::default();
        for (index, fixture) in FIXTURES.iter().enumerate() {
            app.selected = index;
            if [
                "patient-invalid-utf8",
                "patient-over-limit",
                "patient-exact-limit",
            ]
            .contains(&fixture.id)
            {
                assert_eq!(app.preview_selected(), Err("preview_unavailable"));
                assert!(app.preview.is_none());
                assert!(app.preview_notice.is_some());
            } else {
                let json = app.preview_selected().expect("approved fictional JSON");
                assert_eq!(json.len(), fixture.bytes);
                assert!(json.contains("resourceType"));
                assert!(app.preview_notice.is_none());
                assert!(app.result.as_deref().unwrap().contains(fixture.sha256));
            }
        }
    }

    #[test]
    fn invalid_selection_or_new_verification_clears_stale_json_preview() {
        let mut app = MedOriginNativePreview {
            selected: 6, // in-memory fictional bundle
            ..Default::default()
        };
        assert!(app.preview_selected().unwrap().contains("Bundle"));
        assert!(app.preview.is_some());
        let _ = app.hash_selected().expect("same synthetic fixture");
        assert!(app.preview.is_none(), "verification must hide old JSON");
        app.selected = usize::MAX;
        assert_eq!(app.preview_selected(), Err("synthetic_verification_failed"));
        assert!(app.preview.is_none());
        assert!(!app.result.as_deref().unwrap().contains("SHA-256 verified"));
    }

    #[test]
    fn fictional_side_by_side_comparison_reverifies_two_distinct_sources() {
        let mut app = MedOriginNativePreview {
            selected: 0,
            compare_with: 4,
            ..Default::default()
        };
        assert_eq!(app.compare_selected(), Ok(()));
        let pair = app
            .comparison
            .as_ref()
            .expect("two verified fictional texts");
        assert_eq!(pair.left.id, "patient-minimal");
        assert_eq!(pair.right.id, "observation-minimal");
        assert_eq!(pair.left_json.len(), pair.left.bytes);
        assert_eq!(pair.right_json.len(), pair.right.bytes);
        assert!(pair.left_json.contains("Patient"));
        assert!(pair.right_json.contains("Observation"));
        assert!(app.preview.is_none(), "comparison must not reuse preview");

        app.selected = 6;
        app.compare_with = 7;
        assert_eq!(app.compare_selected(), Ok(()));
        let pair = app.comparison.as_ref().unwrap();
        assert_eq!(pair.left.status, "BUNDLE_GRAPH_OK");
        assert_eq!(pair.right.status, "INVALID_REFERENCE");
        assert_ne!(pair.left_json, pair.right_json);
        assert_ne!(pair.left.sha256, pair.right.sha256);
        assert!(
            pair.byte_diff_summary
                .contains("first differing byte offset")
        );
        assert!(
            pair.byte_diff_summary
                .contains("Original source bytes unchanged.")
        );
        assert!(app.hash_selected().is_ok());
        assert!(
            app.comparison.is_none(),
            "new verification clears stale pair"
        );
    }

    #[test]
    fn fictional_hex_context_is_bounded_and_byte_exact() {
        assert_eq!(
            fictional_byte_context("abc", "abc"),
            "Fictional HEX context: identical source bytes"
        );
        let unicode = fictional_byte_context("\u{00E9}X", "\u{00E9}Y");
        assert!(unicode.contains("zero-based byte 2"));
        assert!(unicode.contains("left bytes 0..3 [HEX C3 A9 58]"));
        assert!(unicode.contains("right bytes 0..3 [HEX C3 A9 59]"));
        let inserted = fictional_byte_context("abc", "abXc");
        assert!(inserted.contains("left bytes 0..3 [HEX 61 62 63]"));
        assert!(inserted.contains("right bytes 0..4 [HEX 61 62 58 63]"));
        let long = fictional_byte_context(&("a".repeat(100) + "x"), &("a".repeat(100) + "y"));
        assert!(long.contains("left bytes 92..101"));
        assert!(!long.contains("61 61 61 61 61 61 61 61 61 61"));
    }

    #[test]
    fn fictional_byte_diff_uses_exact_bytes_and_never_overlaps_prefix_and_suffix() {
        assert_eq!(
            fictional_byte_diff_summary("abc", "abc"),
            "Fictional byte comparison: identical (3 bytes)"
        );
        let inserted = fictional_byte_diff_summary("abc", "abXc");
        assert!(inserted.contains("first differing byte offset 2 (zero-based)"));
        assert!(inserted.contains("common suffix 1 bytes"));
        assert!(inserted.contains("left 3 bytes, right 4 bytes"));
        let unicode = fictional_byte_diff_summary("éX", "éY");
        assert!(unicode.contains("first differing byte offset 2 (zero-based)"));
        assert!(unicode.contains("common suffix 0 bytes"));
        let prefix_only = fictional_byte_diff_summary("abc", "abcd");
        assert!(prefix_only.contains("first differing byte offset 3 (zero-based)"));
        assert!(prefix_only.contains("common suffix 0 bytes"));
    }

    #[test]
    fn fictional_comparison_fails_closed_on_boundaries_and_invalid_selection() {
        let mut app = MedOriginNativePreview {
            selected: 0,
            compare_with: 4,
            ..Default::default()
        };
        assert!(app.compare_selected().is_ok());
        for (left, right) in [
            (1, 4),          // invalid UTF-8
            (0, 2),          // over 32 KiB
            (0, 3),          // exact 32 KiB
            (0, 0),          // same fixture
            (0, usize::MAX), // forged secondary index
            (usize::MAX, 4), // forged primary index
        ] {
            app.selected = left;
            app.compare_with = right;
            assert!(app.compare_selected().is_err());
            assert!(app.comparison.is_none(), "never retain stale comparison");
            assert!(app.preview.is_none(), "never retain stale JSON");
            assert!(app.result.as_deref().unwrap().starts_with("FAIL CLOSED"));
        }
    }

    #[test]
    fn fictional_json_path_summary_is_semantic_and_escapes_pointer_segments() {
        let same = fictional_json_path_diff(r#"{"a":1,"b":2}"#, r#"{ "b":2, "a":1 }"#).unwrap();
        assert!(same.contains("structurally identical"));
        let changed = fictional_json_path_diff(
            r#"{"resourceType":"Patient"}"#,
            r#"{"resourceType":"Observation"}"#,
        )
        .unwrap();
        assert!(changed.contains("/resourceType (value differs)"));
        let escaped = fictional_json_path_diff(r#"{"a/b~c":[1,2]}"#, r#"{"a/b~c":[1,3]}"#).unwrap();
        assert!(escaped.contains("/a~1b~0c/1 (value differs)"));
        let missing = fictional_json_path_diff(r#"{"a":1}"#, r#"{"a":1,"b":2}"#).unwrap();
        assert!(missing.contains("/b (field missing on one side)"));
        let array = fictional_json_path_diff(r#"{"a":[1]}"#, r#"{"a":[1,2]}"#).unwrap();
        assert!(array.contains("/a/1 (array length differs)"));
        assert_eq!(
            fictional_json_path_diff("not json", "{}"),
            Err("fictional_json_parse_refused")
        );
    }

    #[test]
    fn fictional_json_path_comparison_is_verified_and_cleared_on_refusal() {
        let mut app = MedOriginNativePreview {
            selected: 0,
            compare_with: 4,
            ..Default::default()
        };
        app.compare_selected().unwrap();
        assert!(
            app.comparison
                .as_ref()
                .unwrap()
                .json_path_diff
                .contains("Fictional JSON path difference: /")
        );
        app.compare_with = usize::MAX;
        assert!(app.compare_selected().is_err());
        assert!(app.comparison.is_none());
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
