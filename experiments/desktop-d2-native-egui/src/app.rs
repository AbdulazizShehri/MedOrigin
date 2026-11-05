// Adapted from emilk/eframe_template under Apache-2.0, see UPSTREAM-NOTICE.md.
// Synthetic-only, in-process native Rust eframe + D0; no browser, EHR, PHI or network.
use crate::core_file_batch::{FictionalCoreFileBatch, admit_fictional_core_file_batch};
use crate::protected_audit::{FictionalProtectedAudit, admit_protected_audit_verification};
use crate::core_provenance::{
    CoreProvenanceReceipt, FictionalCoreInput, PINNED_CORE_CASE_LABELS,
    admit_exact_source_reviewed_external_core_report, inspect_pinned_core_report,
};
use crate::encrypted_readback::{
    FictionalEncryptedReadback, admit_exact_encrypted_readback_projection,
};
use crate::synthetic_bundle::{SyntheticBundlePreview, admit_bounded_synthetic_fhir_bundle};
use crate::workspace_receipt::{
    FictionalEncryptedWorkspaceReceipt, admit_source_pinned_encrypted_workspace_receipt,
    inspect_compiled_encrypted_workspace_receipt,
};
use eframe::egui;
use medorigin_desktop_d0_rust_prototype::{
    HashError, fictional_json_preview_v1, hash_fixture_raw_v1,
    inspect_named_synthetic_fhir_envelope_v1,
};
use sha2::{Digest, Sha256};
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

    fn json_type(value: &Value) -> &'static str {
        match value {
            Value::Null => "null",
            Value::Bool(_) => "boolean",
            Value::Number(_) => "number",
            Value::String(_) => "string",
            Value::Array(_) => "array",
            Value::Object(_) => "object",
        }
    }

    // Only source-compiled, SHA-verified fictional data reaches this function.
    // Keep the UI hint bounded and escape control characters; never print
    // arbitrary nested objects or the complete source into a difference label.
    fn value_hint(value: &Value) -> String {
        match value {
            Value::Null => "null".to_owned(),
            Value::Bool(value) => value.to_string(),
            Value::Number(value) => value.to_string(),
            Value::String(value) => {
                let prefix: String = value.chars().take(48).collect();
                let truncated = if value.chars().count() > 48 {
                    "..."
                } else {
                    ""
                };
                format!("{prefix:?}{truncated}")
            }
            Value::Array(value) => format!("array ({} elements)", value.len()),
            Value::Object(value) => format!("object ({} fields)", value.len()),
        }
    }

    fn first_diff(
        a: &Value,
        b: &Value,
        path: &str,
        depth: usize,
    ) -> Result<Option<(String, String)>, &'static str> {
        if depth > 32 {
            return Err("fictional_json_depth_exceeded");
        }
        match (a, b) {
            (Value::Object(left), Value::Object(right)) => {
                // Compare shared fields before missing fields, sorted by name.
                let mut shared: Vec<_> =
                    left.keys().filter(|key| right.contains_key(*key)).collect();
                shared.sort();
                for key in shared {
                    let next = format!("{path}/{}", pointer_segment(key));
                    if let Some(diff) = first_diff(&left[key], &right[key], &next, depth + 1)? {
                        return Ok(Some(diff));
                    }
                }
                // Preserve direction: missing on left and missing on right
                // have different developer meanings.
                let mut missing: Vec<(&str, bool)> = left
                    .keys()
                    .filter(|key| !right.contains_key(*key))
                    .map(|key| (key.as_str(), false))
                    .chain(
                        right
                            .keys()
                            .filter(|key| !left.contains_key(*key))
                            .map(|key| (key.as_str(), true)),
                    )
                    .collect();
                missing.sort_by(|a, b| a.0.cmp(b.0));
                if let Some((key, missing_on_left)) = missing.first() {
                    let (source, side) = if *missing_on_left {
                        (right, "field missing on left; right")
                    } else {
                        (left, "field missing on right; left")
                    };
                    let value = source
                        .get(*key)
                        .ok_or("fictional_json_missing_field_refused")?;
                    return Ok(Some((
                        format!("{path}/{}", pointer_segment(key)),
                        format!("{side}={}", value_hint(value)),
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
                        format!(
                            "array length differs: left={}, right={}",
                            left.len(),
                            right.len()
                        ),
                    )));
                }
                Ok(None)
            }
            _ if a == b => Ok(None),
            _ => {
                let detail = if std::mem::discriminant(a) == std::mem::discriminant(b) {
                    format!(
                        "value differs: left={}, right={}",
                        value_hint(a),
                        value_hint(b)
                    )
                } else {
                    format!(
                        "JSON type differs: left={}, right={}",
                        json_type(a),
                        json_type(b)
                    )
                };
                Ok(Some((
                    if path.is_empty() {
                        "(root)".to_owned()
                    } else {
                        path.to_owned()
                    },
                    detail,
                )))
            }
        }
    }

    let a: Value = serde_json::from_str(left).map_err(|_| "fictional_json_parse_refused")?;
    let b: Value = serde_json::from_str(right).map_err(|_| "fictional_json_parse_refused")?;
    let summary = match first_diff(&a, &b, "", 0)? {
        Some((pointer, detail)) => format!(
            "Fictional JSON path difference: {pointer} ({detail}). Structural developer hint only; original source bytes unchanged."
        ),
        None => "Fictional JSON path difference: structurally identical; original source bytes may differ.".to_owned(),
    };
    Ok(summary)
}

/// Independently hash the exact UTF-8 bytes displayed or compared by D2.
/// A provider's SHA metadata matching the fixture table is not sufficient:
/// its returned raw string must also match that digest. No normalization,
/// arbitrary input or filesystem access is permitted here.
fn verified_fictional_preview_bytes(fixture: FixtureSpec, raw: &str) -> bool {
    if raw.len() != fixture.bytes || raw.len() > 2_048 {
        return false;
    }
    use std::fmt::Write as _;
    let mut actual = String::with_capacity(64);
    for byte in Sha256::digest(raw.as_bytes()) {
        write!(&mut actual, "{byte:02x}").expect("writing to String is infallible");
    }
    actual == fixture.sha256
}

/// Exact relationship projection of an independently SHA-verified compiled
/// fictional D0 JSON fixture. NOT a general FHIR graph or chronology.
#[derive(Clone, Debug, PartialEq, Eq)]
struct FictionalRelationEdge {
    source_pointer: &'static str,
    target: &'static str,
    relationship: &'static str,
}

#[derive(Clone, Debug)]
struct FictionalRelationView {
    source: FixtureSpec,
    edges: Vec<FictionalRelationEdge>,
}

/// This helper receives only raw bytes returned by verified_json_for() in
/// normal use. Unknown fixtures, unexpected fields, date invention and
/// changed references are rejected, not repaired or clinically interpreted.
fn project_pinned_fictional_relations(
    fixture_id: &str,
    raw: &str,
) -> Result<Vec<FictionalRelationEdge>, &'static str> {
    use serde_json::Value;
    const PATIENT_REF: &str = "Patient/synthetic";
    const PATIENT_URN: &str = "urn:uuid:00000000-0000-4000-8000-000000000001";
    const OBS_URN: &str = "urn:uuid:00000000-0000-4000-8000-000000000002";
    let source: Value = serde_json::from_str(raw).map_err(|_| "fictional_relation_invalid_json")?;
    let value_at = |pointer: &str| {
        source
            .pointer(pointer)
            .and_then(Value::as_str)
            .ok_or("fictional_relation_pointer_missing")
    };
    let check = |pointer: &str, expected: &str| {
        if value_at(pointer)? == expected {
            Ok(())
        } else {
            Err("fictional_relation_changed")
        }
    };
    // None of the current D0 fixtures contain date/time evidence. A revised
    // corpus must be reviewed before attempting chronological ordering.
    let no_dates = |resource: &Value| {
        ![
            "birthDate",
            "effectiveDateTime",
            "effectivePeriod",
            "issued",
            "recordedDate",
        ]
        .iter()
        .any(|field| resource.get(*field).is_some())
    };
    if !no_dates(&source) {
        return Err("fictional_relation_unreviewed_date");
    }
    match fixture_id {
        "observation-minimal" => {
            check("/resourceType", "Observation")?;
            check("/id", "synthetic-observation")?;
            check("/subject/reference", PATIENT_REF)?;
            Ok(vec![FictionalRelationEdge {
                source_pointer: "/subject/reference",
                target: PATIENT_REF,
                relationship: "fictional_subject_reference",
            }])
        }
        "bundle-valid" | "bundle-linked" => {
            check("/resourceType", "Bundle")?;
            check("/id", "synthetic-bundle")?;
            check("/type", "collection")?;
            let entries = source
                .get("entry")
                .and_then(Value::as_array)
                .ok_or("fictional_relation_bundle_missing")?;
            if entries.len() != 2 {
                return Err("fictional_relation_bundle_count_changed");
            }
            check("/entry/0/fullUrl", PATIENT_URN)?;
            check("/entry/1/fullUrl", OBS_URN)?;
            check("/entry/0/resource/resourceType", "Patient")?;
            check("/entry/0/resource/id", "synthetic")?;
            check("/entry/1/resource/resourceType", "Observation")?;
            check("/entry/1/resource/id", "synthetic-observation")?;
            for pointer in ["/entry/0/resource", "/entry/1/resource"] {
                if !no_dates(
                    source
                        .pointer(pointer)
                        .ok_or("fictional_relation_member_missing")?,
                ) {
                    return Err("fictional_relation_unreviewed_date");
                }
            }
            let expected_ref = if fixture_id == "bundle-valid" {
                PATIENT_REF
            } else {
                PATIENT_URN
            };
            check("/entry/1/resource/subject/reference", expected_ref)?;
            Ok(vec![
                FictionalRelationEdge {
                    source_pointer: "/entry/0/resource",
                    target: PATIENT_URN,
                    relationship: "fictional_bundle_patient_member",
                },
                FictionalRelationEdge {
                    source_pointer: "/entry/1/resource",
                    target: OBS_URN,
                    relationship: "fictional_bundle_observation_member",
                },
                FictionalRelationEdge {
                    source_pointer: "/entry/1/resource/subject/reference",
                    target: expected_ref,
                    relationship: "fictional_subject_reference",
                },
            ])
        }
        _ => Err("fictional_relation_fixture_not_approved"),
    }
}

/// In-memory-only, source-pinned fictional case explorer. This is NOT a
/// clinical workspace, authentication layer, clinical audit log or PHI store.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
enum FictionalWorkspaceFilter {
    #[default]
    All,
    ExpectedEnvelopeOk,
    ExpectedNegative,
}

impl FictionalWorkspaceFilter {
    fn label(self) -> &'static str {
        match self {
            Self::All => "All fictional cases",
            Self::ExpectedEnvelopeOk => "Expected-positive developer controls",
            Self::ExpectedNegative => "Expected-negative developer controls",
        }
    }
    fn admits(self, negative: bool) -> bool {
        match self {
            Self::All => true,
            Self::ExpectedEnvelopeOk => !negative,
            Self::ExpectedNegative => negative,
        }
    }
}

/// Read-only fixed resource-type facets. No free-text search field accepts
/// human or patient input: even a fictional worklist is strictly allowlisted.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
enum FictionalResourceTypeFilter {
    #[default]
    All,
    Patient,
    Observation,
    Bundle,
}

impl FictionalResourceTypeFilter {
    fn label(self) -> &'static str {
        match self {
            Self::All => "All resource types",
            Self::Patient => "Patient (fictional)",
            Self::Observation => "Observation (fictional)",
            Self::Bundle => "Bundle (fictional)",
        }
    }

    fn admits(self, resource_type: &str) -> bool {
        match self {
            Self::All => true,
            Self::Patient => resource_type == "Patient",
            Self::Observation => resource_type == "Observation",
            Self::Bundle => resource_type == "Bundle",
        }
    }
}

#[derive(Clone, Copy, Debug)]
struct FictionalWorkspaceSpec {
    fixture_index: usize,
    resource_type: &'static str,
    resource_id: &'static str,
    negative: bool,
    expected_edges: usize,
}

const FICTIONAL_WORKSPACE_CASES: [FictionalWorkspaceSpec; 6] = [
    FictionalWorkspaceSpec {
        fixture_index: 0,
        resource_type: "Patient",
        resource_id: "synthetic",
        negative: false,
        expected_edges: 0,
    },
    FictionalWorkspaceSpec {
        fixture_index: 4,
        resource_type: "Observation",
        resource_id: "synthetic-observation",
        negative: false,
        expected_edges: 1,
    },
    FictionalWorkspaceSpec {
        fixture_index: 5,
        resource_type: "Observation",
        resource_id: "synthetic-observation",
        negative: true,
        expected_edges: 0,
    },
    FictionalWorkspaceSpec {
        fixture_index: 6,
        resource_type: "Bundle",
        resource_id: "synthetic-bundle",
        negative: false,
        expected_edges: 3,
    },
    FictionalWorkspaceSpec {
        fixture_index: 10,
        resource_type: "Bundle",
        resource_id: "synthetic-bundle",
        negative: false,
        expected_edges: 3,
    },
    FictionalWorkspaceSpec {
        fixture_index: 11,
        resource_type: "Bundle",
        resource_id: "synthetic-bundle",
        negative: true,
        expected_edges: 0,
    },
];

#[derive(Clone, Debug)]
struct FictionalWorkspaceDetail {
    fixture: FixtureSpec,
    resource_type: &'static str,
    resource_id: &'static str,
    negative: bool,
    relations: Vec<FictionalRelationEdge>,
}

/// Exact resource-type facets of the already verified fictional Core projection.
/// No free-text entry, patient import or general-purpose query API.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
enum RecoveredResourceTypeFilter {
    #[default]
    All,
    Observation,
    Patient,
    Encounter,
}

impl RecoveredResourceTypeFilter {
    fn label(self) -> &'static str {
        match self {
            Self::All => "All",
            Self::Observation => "Observation",
            Self::Patient => "Patient",
            Self::Encounter => "Encounter",
        }
    }

    fn matches(self, resource: &crate::encrypted_readback::FictionalReadbackResource) -> bool {
        self == Self::All || resource.resource_type == self.label()
    }
}

/// A source-validated *fictional* patient-linked view of exactly three
/// de-identified recovered test identities. No actual clinical chart or time.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct FictionalPatientChart {
    patient: usize,
    observation: usize,
    encounter: usize,
}

fn verified_fictional_patient_chart(
    readback: &FictionalEncryptedReadback,
) -> Result<FictionalPatientChart, &'static str> {
    if readback.resources.len() != 3
        || !readback.audit_chain_verified
        || !readback.encrypted_reopen_verified
    {
        return Err("fictional_patient_chart_source_or_audit_refused");
    }
    let only_type = |kind: &str| -> Result<usize, &'static str> {
        let matching: Vec<_> = readback
            .resources
            .iter()
            .enumerate()
            .filter(|(_, item)| item.resource_type == kind)
            .map(|(index, _)| index)
            .collect();
        if matching.len() != 1 {
            return Err("fictional_patient_chart_type_ambiguous");
        }
        Ok(matching[0])
    };
    let chart = FictionalPatientChart {
        patient: only_type("Patient")?,
        observation: only_type("Observation")?,
        encounter: only_type("Encounter")?,
    };
    let patient = &readback.resources[chart.patient];
    let encounter = &readback.resources[chart.encounter];
    let observation = &readback.resources[chart.observation];

    let exactly_one = |record: &crate::encrypted_readback::FictionalReadbackResource,
                       field: &str,
                       target: &str| {
        record
            .links
            .iter()
            .filter(|edge| edge.field == field && edge.target == target)
            .count()
            == 1
    };
    if !patient.links.is_empty()
        || encounter.links.len() != 1
        || observation.links.len() != 2
        || !exactly_one(encounter, "subject", &patient.full_url)
        || !exactly_one(observation, "subject", &patient.full_url)
        || !exactly_one(observation, "encounter", &encounter.full_url)
    {
        return Err("fictional_patient_chart_unverified_relationship_refused");
    }
    Ok(chart)
}

#[derive(Default)]
pub struct MedOriginNativePreview {
    selected: usize,
    compare_with: usize,
    result: Option<String>,
    preview: Option<String>,
    preview_notice: Option<&'static str>,
    comparison: Option<FictionalComparison>,
    relationships: Option<FictionalRelationView>,
    relationship_notice: Option<&'static str>,
    core_report_selection: usize,
    core_report: Option<CoreProvenanceReceipt>,
    core_file_batch: Option<FictionalCoreFileBatch>,
    // Separate Core #981 *audit-only* protected fictional read-only status.
    protected_audit: Option<FictionalProtectedAudit>,
    // Source-scoped, ephemeral *exploration* of Core redacted import summaries.
    // Never represents patient review, clinical verification or approval.
    core_file_batch_selected: Option<usize>,
    core_file_batch_inspected: Vec<bool>,
    core_file_batch_activity_only: bool,
    core_file_batch_notice: Option<&'static str>,
    core_report_notice: Option<&'static str>,
    external_core_source_visible: bool,
    encrypted_workspace_receipt: Option<FictionalEncryptedWorkspaceReceipt>,
    encrypted_readback: Option<FictionalEncryptedReadback>,
    encrypted_readback_source_external: bool,
    // Separates the source-verified fictional Workspace from developer proof
    // controls. UI-only mode: never changes Core data, keys, privileges or IO.
    focused_workspace_visible: bool,
    synthetic_bundle: Option<SyntheticBundlePreview>,
    synthetic_bundle_selected: Option<usize>,
    synthetic_bundle_history: Vec<usize>,
    // Ephemeral exploration state; opened != clinician-reviewed or approved.
    synthetic_bundle_visited: Vec<bool>,
    synthetic_bundle_patient: Option<usize>,
    synthetic_bundle_type: &'static str,
    synthetic_bundle_notice: Option<&'static str>,
    encrypted_readback_selected: Option<usize>,
    encrypted_readback_history: Vec<usize>,
    encrypted_readback_filter: RecoveredResourceTypeFilter,
    encrypted_readback_query: String,
    // Three source-verified imaginary identities only. In-memory demo UX
    // walkthrough, NOT professional sign-off, triage or clinical review.
    fictional_walkthrough_done: [bool; 3],
    encrypted_readback_notice: Option<&'static str>,
    workspace_report_external: bool,
    workspace_report_notice: Option<&'static str>,
    fictional_workspace_unlocked: bool,
    fictional_workspace_filter: FictionalWorkspaceFilter,
    fictional_workspace_resource_type: FictionalResourceTypeFilter,
    fictional_workspace_selected: Option<usize>,
    fictional_workspace_back: Option<usize>,
    fictional_workspace_detail: Option<FictionalWorkspaceDetail>,
    fictional_workspace_notice: Option<&'static str>,
}

impl MedOriginNativePreview {
    /// Explicit one-shot, bounded external stdin QA transport. The caller is
    /// UNTRUSTED; only the two exact canonical source-compiled fictional
    /// reports are accepted. This never attests freshness or a running Core.
    pub fn from_one_time_fictional_core_stdin(raw: &[u8]) -> Result<Self, &'static str> {
        let receipt = admit_exact_source_reviewed_external_core_report(raw)?;
        Ok(Self {
            core_report_selection: match receipt.case {
                FictionalCoreInput::KnownStructureDefinition => 0,
                FictionalCoreInput::UnknownResourceNegativeControl => 1,
            },
            core_report: Some(receipt),
            external_core_source_visible: true,
            ..Default::default()
        })
    }

    /// Admit an exact nonclinical Core+Workspace encrypted demo summary.
    /// Input is UNTRUSTED and never proves its own producer or freshness.
    pub fn from_one_time_synthetic_workspace_stdin(raw: &[u8]) -> Result<Self, &'static str> {
        let receipt = admit_source_pinned_encrypted_workspace_receipt(raw)?;
        Ok(Self {
            encrypted_workspace_receipt: Some(receipt),
            workspace_report_external: true,
            ..Default::default()
        })
    }

    pub fn inspect_compiled_encrypted_demo(&mut self) -> Result<(), &'static str> {
        self.clear_fictional_output();
        match inspect_compiled_encrypted_workspace_receipt() {
            Ok(receipt) => {
                self.encrypted_workspace_receipt = Some(receipt);
                Ok(())
            }
            Err(_) => {
                self.workspace_report_notice =
                    Some("FAIL CLOSED: encrypted demo evidence modified");
                Err("fictional_encrypted_workspace_evidence_refused")
            }
        }
    }

    pub fn from_one_time_synthetic_encrypted_readback_stdin(
        raw: &[u8],
    ) -> Result<Self, &'static str> {
        let readback = admit_exact_encrypted_readback_projection(raw)?;
        Ok(Self {
            encrypted_readback: Some(readback),
            encrypted_readback_source_external: true,
            ..Default::default()
        })
    }

    /// The independently cold-reopened *fictional audit-only* Core #981
    /// verification status contains NO patient records or clinic credentials.
    pub fn from_one_time_protected_audit_verification_stdin(
        raw: &[u8],
    ) -> Result<Self, &'static str> {
        let audit = admit_protected_audit_verification(raw)?;
        Ok(Self {
            protected_audit: Some(audit),
            ..Default::default()
        })
    }

    pub fn protected_audit_verified_events(&self) -> usize {
        self.protected_audit
            .as_ref()
            .map_or(0, |audit| audit.verified_events)
    }

    /// The real Core #963 receipt contains only redacted counts and SHA anchors.
    /// Do NOT turn this receipt into patient records or confuse it with an
    /// authenticated source or an approved FHIR R4 validator.
    pub fn from_one_time_core_file_batch_receipt_stdin(raw: &[u8]) -> Result<Self, &'static str> {
        let batch = admit_fictional_core_file_batch(raw)?;
        let inspected = vec![false; batch.imports.len()];
        Ok(Self {
            core_file_batch: Some(batch),
            core_file_batch_inspected: inspected,
            ..Default::default()
        })
    }

    pub fn core_file_batch_import_count(&self) -> usize {
        self.core_file_batch.as_ref().map_or(0, |b| b.imports.len())
    }

    /// Only source-projected fictional imports can enter the read-only worklist.
    fn core_batch_visible(&self, index: usize) -> bool {
        self.core_file_batch
            .as_ref()
            .and_then(|batch| batch.imports.get(index))
            .is_some_and(|item| {
                !self.core_file_batch_activity_only || item.timeline_event_count > 0
            })
    }

    fn core_batch_select(&mut self, index: usize) -> Result<(), &'static str> {
        let Some(batch) = self.core_file_batch.as_ref() else {
            return Err("fictional_batch_missing_source");
        };
        if index >= batch.imports.len()
            || self.core_file_batch_inspected.len() != batch.imports.len()
        {
            self.clear_fictional_output();
            return Err("fictional_batch_stale_source_index_or_progress_refused");
        }
        if !self.core_batch_visible(index) {
            self.core_file_batch_selected = None;
            self.core_file_batch_notice =
                Some("Only source imports in the current fictional activity filter can be opened");
            return Err("fictional_batch_hidden_source_refused");
        }
        self.core_file_batch_selected = Some(index);
        self.core_file_batch_inspected[index] = true;
        self.core_file_batch_notice = None;
        Ok(())
    }

    fn core_batch_step(&mut self, forward: bool) -> Result<(), &'static str> {
        let Some(batch) = self.core_file_batch.as_ref() else {
            return Err("fictional_batch_missing_source");
        };
        if self.core_file_batch_inspected.len() != batch.imports.len() {
            self.clear_fictional_output();
            return Err("fictional_batch_stale_progress_refused");
        }
        let visible: Vec<usize> = (0..batch.imports.len())
            .filter(|index| self.core_batch_visible(*index))
            .collect();
        let target = match self.core_file_batch_selected {
            None => {
                if forward {
                    visible.first()
                } else {
                    visible.last()
                }
            }
            Some(current) => {
                let Some(position) = visible.iter().position(|index| *index == current) else {
                    self.core_file_batch_selected = None;
                    self.core_file_batch_notice =
                        Some("Selected import is not visible in the current source-only filter");
                    return Err("fictional_batch_selected_import_hidden_or_stale");
                };
                if forward {
                    visible.get(position + 1)
                } else {
                    position.checked_sub(1).and_then(|index| visible.get(index))
                }
            }
        };
        let Some(target) = target.copied() else {
            self.core_file_batch_notice =
                Some("No more visible fictional imports in this direction");
            return Err("fictional_batch_navigation_end");
        };
        self.core_batch_select(target)
    }

    fn core_batch_next_uninspected(&mut self) -> Result<(), &'static str> {
        let Some(batch) = self.core_file_batch.as_ref() else {
            return Err("fictional_batch_missing_source");
        };
        if self.core_file_batch_inspected.len() != batch.imports.len() {
            self.clear_fictional_output();
            return Err("fictional_batch_stale_progress_refused");
        }
        let target = (0..batch.imports.len()).find(|index| {
            self.core_batch_visible(*index) && !self.core_file_batch_inspected[*index]
        });
        let Some(target) = target else {
            self.core_file_batch_notice =
                Some("All visible fictional imports opened this session; NOT clinical review");
            return Err("fictional_batch_no_uninspected_import");
        };
        self.core_batch_select(target)
    }

    fn core_batch_activity_filter(&mut self, active_only: bool) -> Result<(), &'static str> {
        let Some(batch) = self.core_file_batch.as_ref() else {
            return Err("fictional_batch_missing_source");
        };
        if self.core_file_batch_inspected.len() != batch.imports.len() {
            self.clear_fictional_output();
            return Err("fictional_batch_stale_progress_refused");
        }
        self.core_file_batch_activity_only = active_only;
        if self
            .core_file_batch_selected
            .is_some_and(|index| !self.core_batch_visible(index))
        {
            self.core_file_batch_selected = None;
        }
        self.core_file_batch_notice = None;
        Ok(())
    }

    fn core_batch_reset_exploration(&mut self) -> Result<(), &'static str> {
        let Some(batch) = self.core_file_batch.as_ref() else {
            return Err("fictional_batch_missing_source");
        };
        if self.core_file_batch_inspected.len() != batch.imports.len() {
            self.clear_fictional_output();
            return Err("fictional_batch_stale_progress_refused");
        }
        self.core_file_batch_inspected.fill(false);
        self.core_file_batch_selected = None;
        self.core_file_batch_activity_only = false;
        self.core_file_batch_notice = None;
        Ok(())
    }

    /// Distinct structural FHIR-shaped multi-patient demo, not the SHA-pinned
    /// encrypted Core transport. Strict fake IDs, exact field allowlist,
    /// canonical JSON and complete patient-reference graph; NO PHI fields.
    pub fn from_one_time_synthetic_bundle_stdin(raw: &[u8]) -> Result<Self, &'static str> {
        let bundle = admit_bounded_synthetic_fhir_bundle(raw)?;
        let first_patient = bundle
            .resources
            .iter()
            .position(|r| r.resource_type == "Patient");
        let mut visited = vec![false; bundle.resources.len()];
        if let Some(index) = first_patient {
            visited[index] = true;
        }
        Ok(Self {
            synthetic_bundle: Some(bundle),
            synthetic_bundle_visited: visited,
            synthetic_bundle_patient: first_patient,
            synthetic_bundle_selected: first_patient,
            synthetic_bundle_type: "All",
            ..Default::default()
        })
    }

    /// One-click, compiled, nonclinical demo from the same strict reviewed
    /// fictional fixture. No stdin/file picker, Core process or new network
    /// permission. This is opt-in, never implicit on native default startup.
    fn open_embedded_fictional_bundle_demo(&mut self) -> Result<(), &'static str> {
        const DEMO: &[u8] =
            include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
        let admitted = Self::from_one_time_synthetic_bundle_stdin(DEMO).inspect_err(|_| {
            self.clear_fictional_output();
        })?;
        *self = admitted;
        Ok(())
    }

    pub fn synthetic_bundle_resource_count(&self) -> usize {
        self.synthetic_bundle
            .as_ref()
            .map_or(0, |b| b.resources.len())
    }

    /// Same strict verified fictional source as the developer readback mode,
    /// but open the user-facing source browser FIRST. No alternative import,
    /// elevated permission, clinical use or source authenticity claim.
    pub fn from_one_time_synthetic_focused_readback_stdin(
        raw: &[u8],
    ) -> Result<Self, &'static str> {
        let mut app = Self::from_one_time_synthetic_encrypted_readback_stdin(raw)?;
        app.set_focused_fictional_workspace(true)?;
        Ok(app)
    }

    pub fn focused_fictional_workspace_is_visible(&self) -> bool {
        self.focused_workspace_visible
    }

    pub fn has_external_synthetic_encrypted_readback(&self) -> bool {
        self.encrypted_readback_source_external && self.encrypted_readback.is_some()
    }

    pub fn has_external_fictional_workspace_stdin(&self) -> bool {
        self.workspace_report_external && self.encrypted_workspace_receipt.is_some()
    }

    /// Native navigation through identities actually projected from
    /// encrypted Core memory readback. No arbitrary resource resolver.
    /// Select only the one source-projected, graph-verified fictional Patient
    /// and reset stale filters/selection. This is not a clinical patient chart.
    fn open_recovered_fictional_patient_chart(&mut self) -> Result<(), &'static str> {
        let chart = self
            .encrypted_readback
            .as_ref()
            .ok_or("fictional_patient_chart_no_source")
            .and_then(verified_fictional_patient_chart);
        match chart {
            Ok(chart) => {
                self.encrypted_readback_filter = RecoveredResourceTypeFilter::All;
                self.encrypted_readback_query.clear();
                self.encrypted_readback_selected = Some(chart.patient);
                self.encrypted_readback_history.clear();
                self.encrypted_readback_notice = None;
                Ok(())
            }
            Err(reason) => {
                self.clear_fictional_output();
                self.encrypted_readback_notice =
                    Some("FAIL CLOSED: fictional patient chart graph not verified");
                Err(reason)
            }
        }
    }

    /// Navigate only to one of the two exact, source-verified Patient-related
    /// fictional resources. Never infer medical chronology from graph edges.
    fn open_recovered_fictional_patient_chart_member(
        &mut self,
        target_index: usize,
    ) -> Result<(), &'static str> {
        let verified = (|| {
            let source = self
                .encrypted_readback
                .as_ref()
                .ok_or("fictional_patient_chart_no_source")?;
            let chart = verified_fictional_patient_chart(source)?;
            let current = self
                .encrypted_readback_selected
                .ok_or("fictional_patient_chart_no_selection")?;
            if current != chart.patient
                || (target_index != chart.encounter && target_index != chart.observation)
            {
                return Err("fictional_patient_chart_unapproved_member");
            }
            Ok((current, target_index))
        })();
        match verified {
            Ok((current, target)) => self.navigate_encrypted_readback_resource(current, target),
            Err(reason) => {
                self.clear_fictional_output();
                self.encrypted_readback_notice =
                    Some("FAIL CLOSED: fictional patient chart member not verified");
                Err(reason)
            }
        }
    }

    /// Mark one exact fictional source identity walked through in the current
    /// GUI session. Never writes clinical status, audit, or database records.
    fn mark_selected_fictional_walkthrough(&mut self) -> Result<(), &'static str> {
        let candidate = (|| {
            let readback = self
                .encrypted_readback
                .as_ref()
                .ok_or("fictional_walkthrough_no_source")?;
            verified_fictional_patient_chart(readback)?;
            let index = self
                .encrypted_readback_selected
                .ok_or("fictional_walkthrough_no_selection")?;
            if index >= readback.resources.len() || index >= self.fictional_walkthrough_done.len() {
                return Err("fictional_walkthrough_selected_identity_refused");
            }
            Ok(index)
        })();
        match candidate {
            Ok(index) => {
                self.fictional_walkthrough_done[index] = true;
                self.encrypted_readback_notice = None;
                Ok(())
            }
            Err(reason) => {
                self.clear_fictional_output();
                self.encrypted_readback_notice =
                    Some("FAIL CLOSED: fictional walkthrough source or identity not verified");
                Err(reason)
            }
        }
    }

    /// A bounded source-derived walkthrough order (Patient, Encounter,
    /// Observation). This is not a clinical priority or event chronology.
    fn next_unvisited_fictional_resource(&mut self) -> Result<(), &'static str> {
        let candidate = (|| {
            let readback = self
                .encrypted_readback
                .as_ref()
                .ok_or("fictional_walkthrough_no_source")?;
            let chart = verified_fictional_patient_chart(readback)?;
            if let Some(index) = self.encrypted_readback_selected
                && index >= readback.resources.len()
            {
                return Err("fictional_walkthrough_stale_selection");
            }
            let order = [chart.patient, chart.encounter, chart.observation];
            let start = self
                .encrypted_readback_selected
                .and_then(|index| order.iter().position(|item| *item == index))
                .map_or(0, |index| (index + 1) % order.len());
            Ok((0..order.len())
                .map(|offset| order[(start + offset) % order.len()])
                .find(|index| !self.fictional_walkthrough_done[*index]))
        })();
        match candidate {
            Ok(Some(index)) => {
                self.encrypted_readback_filter = RecoveredResourceTypeFilter::All;
                self.encrypted_readback_query.clear();
                self.encrypted_readback_selected = Some(index);
                // A walkthrough jump is not a verified relationship edge.
                self.encrypted_readback_history.clear();
                self.encrypted_readback_notice = None;
                Ok(())
            }
            Ok(None) => {
                self.encrypted_readback_notice =
                    Some("All three fictional walkthrough steps complete (session only)");
                Err("fictional_walkthrough_all_visited")
            }
            Err(reason) => {
                self.clear_fictional_output();
                self.encrypted_readback_notice =
                    Some("FAIL CLOSED: fictional walkthrough source graph changed");
                Err(reason)
            }
        }
    }

    fn reset_fictional_walkthrough(&mut self) -> Result<(), &'static str> {
        let checked = self
            .encrypted_readback
            .as_ref()
            .ok_or("fictional_walkthrough_no_source")
            .and_then(verified_fictional_patient_chart);
        match checked {
            Ok(_) => {
                self.fictional_walkthrough_done = [false; 3];
                self.encrypted_readback_notice = None;
                Ok(())
            }
            Err(reason) => {
                self.clear_fictional_output();
                self.encrypted_readback_notice =
                    Some("FAIL CLOSED: fictional walkthrough reset source refused");
                Err(reason)
            }
        }
    }

    fn set_recovered_type_filter(&mut self, filter: RecoveredResourceTypeFilter) {
        self.encrypted_readback_filter = filter;
        self.encrypted_readback_selected = None;
        self.encrypted_readback_history.clear();
        self.encrypted_readback_notice = None;
    }

    // Ephemeral search over ONLY redacted source-derived identities, never
    // patient values, clinical observations, raw FHIR, or other file content.
    // Reject non-ASCII/control input and bound memory to one short token.
    fn set_recovered_search_query(&mut self, input: &str) -> Result<(), &'static str> {
        let normalized = input.trim().to_ascii_lowercase();
        if normalized.len() > 64
            || !normalized
                .bytes()
                .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-' || b == b':')
        {
            self.clear_fictional_output();
            self.encrypted_readback_notice =
                Some("FAIL CLOSED: unreviewed fictional search input refused");
            return Err("fictional_search_unreviewed_characters_or_length");
        }
        self.encrypted_readback_query = normalized;
        self.encrypted_readback_selected = None;
        self.encrypted_readback_history.clear();
        self.encrypted_readback_notice = None;
        Ok(())
    }

    fn recovered_search_matches(
        &self,
        resource: &crate::encrypted_readback::FictionalReadbackResource,
    ) -> bool {
        if !self.encrypted_readback_filter.matches(resource) {
            return false;
        }
        let query = self.encrypted_readback_query.as_str();
        query.is_empty()
            || resource.resource_type.to_ascii_lowercase().contains(query)
            || resource.resource_id.to_ascii_lowercase().contains(query)
            || resource.full_url.to_ascii_lowercase().contains(query)
    }

    fn recovered_visible_count(&self) -> usize {
        self.encrypted_readback
            .as_ref()
            .map(|r| {
                r.resources
                    .iter()
                    .filter(|item| self.recovered_search_matches(item))
                    .count()
            })
            .unwrap_or(0)
    }

    fn select_encrypted_readback_resource(&mut self, index: usize) -> Result<(), &'static str> {
        let count = self
            .encrypted_readback
            .as_ref()
            .map(|readback| readback.resources.len())
            .ok_or("encrypted_readback_not_loaded")?;
        if index >= count {
            self.clear_fictional_output();
            return Err("encrypted_readback_unknown_resource");
        }
        if !self.recovered_search_matches(
            &self
                .encrypted_readback
                .as_ref()
                .ok_or("encrypted_readback_not_loaded")?
                .resources[index],
        ) {
            self.clear_fictional_output();
            return Err("encrypted_readback_filtered_resource_refused");
        }
        self.encrypted_readback_selected = Some(index);
        self.encrypted_readback_history.clear();
        self.encrypted_readback_notice = None;
        Ok(())
    }

    fn follow_encrypted_readback_link(&mut self, link_index: usize) -> Result<(), &'static str> {
        let next = (|| {
            let readback = self
                .encrypted_readback
                .as_ref()
                .ok_or("encrypted_readback_not_loaded")?;
            let current = self
                .encrypted_readback_selected
                .ok_or("encrypted_readback_no_selection")?;
            let record = readback
                .resources
                .get(current)
                .ok_or("encrypted_readback_unknown_resource")?;
            let target = &record
                .links
                .get(link_index)
                .ok_or("encrypted_readback_unknown_link")?
                .target;
            let position = readback
                .resources
                .iter()
                .position(|other| other.full_url == *target)
                .ok_or("encrypted_readback_dangling_link")?;
            Ok::<_, &'static str>((current, position))
        })();
        let (current, position) = match next {
            Ok(next) => next,
            Err(reason) => {
                self.clear_fictional_output();
                self.encrypted_readback_notice =
                    Some("FAIL CLOSED: encrypted fictional readback reference rejected");
                return Err(reason);
            }
        };
        self.navigate_encrypted_readback_resource(current, position)
    }

    /// Incoming relationships are derived ONLY from the same decrypted,
    /// pinned Core projection. A forged or stale edge clears all evidence.
    fn follow_encrypted_readback_incoming(
        &mut self,
        source_index: usize,
        link_index: usize,
    ) -> Result<(), &'static str> {
        let incoming = (|| {
            let readback = self
                .encrypted_readback
                .as_ref()
                .ok_or("encrypted_readback_not_loaded")?;
            let current = self
                .encrypted_readback_selected
                .ok_or("encrypted_readback_no_selection")?;
            let target = readback
                .resources
                .get(current)
                .ok_or("encrypted_readback_unknown_resource")?;
            let source = readback
                .resources
                .get(source_index)
                .ok_or("encrypted_readback_unknown_incoming_resource")?;
            let link = source
                .links
                .get(link_index)
                .ok_or("encrypted_readback_unknown_incoming_link")?;
            if link.target != target.full_url {
                return Err("encrypted_readback_incoming_edge_mismatch");
            }
            Ok::<_, &'static str>(current)
        })();
        match incoming {
            Ok(current) => self.navigate_encrypted_readback_resource(current, source_index),
            Err(reason) => {
                self.clear_fictional_output();
                self.encrypted_readback_notice =
                    Some("FAIL CLOSED: encrypted fictional incoming reference rejected");
                Err(reason)
            }
        }
    }

    fn navigate_encrypted_readback_resource(
        &mut self,
        current: usize,
        position: usize,
    ) -> Result<(), &'static str> {
        // Bounded, source-only navigation history; no persistent record state.
        if self.encrypted_readback_history.len() >= 16 {
            self.clear_fictional_output();
            self.encrypted_readback_notice =
                Some("FAIL CLOSED: fictional navigation history limit reached");
            return Err("encrypted_readback_navigation_limit");
        }
        self.encrypted_readback_history.push(current);
        // Relationship navigation can traverse types outside the chosen facet;
        // reset to All so the active source-derived record remains visible.
        self.encrypted_readback_filter = RecoveredResourceTypeFilter::All;
        self.encrypted_readback_query.clear();
        self.encrypted_readback_selected = Some(position);
        self.encrypted_readback_notice = None;
        Ok(())
    }

    /// Jump to an earlier already-visited verified fictional identity.
    /// Breadcrumb jumps truncate the path rather than inventing a new edge.
    fn jump_encrypted_readback_history(&mut self, step: usize) -> Result<(), &'static str> {
        let selected = self.encrypted_readback_selected;
        let target = self.encrypted_readback_history.get(step).copied();
        let valid = self.encrypted_readback.as_ref().is_some_and(|r| {
            selected.is_some_and(|index| index < r.resources.len())
                && target.is_some_and(|index| index < r.resources.len())
                && self
                    .encrypted_readback_history
                    .iter()
                    .all(|index| *index < r.resources.len())
        });
        if !valid {
            self.clear_fictional_output();
            self.encrypted_readback_notice =
                Some("FAIL CLOSED: fictional breadcrumb outside verified history");
            return Err("encrypted_readback_breadcrumb_refused");
        }
        let previous = target.ok_or("encrypted_readback_breadcrumb_refused")?;
        self.encrypted_readback_history.truncate(step);
        self.encrypted_readback_selected = Some(previous);
        self.encrypted_readback_filter = RecoveredResourceTypeFilter::All;
        self.encrypted_readback_query.clear();
        self.encrypted_readback_notice = None;
        Ok(())
    }

    fn back_encrypted_readback_resource(&mut self) -> Result<(), &'static str> {
        let previous = self
            .encrypted_readback_history
            .pop()
            .ok_or("encrypted_readback_no_previous")?;
        if self
            .encrypted_readback
            .as_ref()
            .and_then(|r| r.resources.get(previous))
            .is_none()
        {
            self.clear_fictional_output();
            return Err("encrypted_readback_previous_refused");
        }
        self.encrypted_readback_selected = Some(previous);
        Ok(())
    }

    /// Read-only source marker for the strict one-shot synthetic stdin path.
    pub fn has_external_fictional_core_stdin(&self) -> bool {
        self.external_core_source_visible && self.core_report.is_some()
    }

    /// Remove all previously rendered synthetic content while keeping only
    /// allowlisted selection indices. This is not secure memory erasure.
    pub fn clear_fictional_output(&mut self) {
        self.result = None;
        self.preview = None;
        self.preview_notice = None;
        self.comparison = None;
        self.relationships = None;
        self.relationship_notice = None;
        self.core_report = None;
        self.core_file_batch = None;
        self.protected_audit = None;
        self.core_file_batch_selected = None;
        self.core_file_batch_inspected.clear();
        self.core_file_batch_activity_only = false;
        self.core_file_batch_notice = None;
        self.core_report_notice = None;
        self.external_core_source_visible = false;
        self.encrypted_workspace_receipt = None;
        self.encrypted_readback = None;
        self.encrypted_readback_source_external = false;
        self.focused_workspace_visible = false;
        self.synthetic_bundle = None;
        self.synthetic_bundle_selected = None;
        self.synthetic_bundle_history.clear();
        self.synthetic_bundle_visited.clear();
        self.synthetic_bundle_patient = None;
        self.synthetic_bundle_type = "";
        self.synthetic_bundle_notice = None;
        self.encrypted_readback_selected = None;
        self.encrypted_readback_history.clear();
        self.encrypted_readback_filter = RecoveredResourceTypeFilter::All;
        self.encrypted_readback_query.clear();
        self.fictional_walkthrough_done = [false; 3];
        self.encrypted_readback_notice = None;
        self.workspace_report_external = false;
        self.workspace_report_notice = None;
        self.fictional_workspace_selected = None;
        self.fictional_workspace_back = None;
        self.fictional_workspace_detail = None;
        self.fictional_workspace_notice = None;
    }

    /// Fail closed if either the trusted raw digest OR the independent
    /// structural outcome differs from the compiled fictional fixture catalog.
    /// A structurally invalid fixture is a correctly identified NEGATIVE test,
    /// not a clinically validated resource.
    pub fn hash_selected(&mut self) -> Result<&str, &'static str> {
        self.result = None;
        self.preview = None;
        self.preview_notice = None;
        self.comparison = None;
        self.relationships = None;
        self.relationship_notice = None;
        self.core_report = None;
        self.core_file_batch = None;
        self.protected_audit = None;
        self.core_file_batch_selected = None;
        self.core_file_batch_inspected.clear();
        self.core_file_batch_activity_only = false;
        self.core_file_batch_notice = None;
        self.core_report_notice = None;
        self.external_core_source_visible = false;
        self.encrypted_workspace_receipt = None;
        self.encrypted_readback = None;
        self.encrypted_readback_source_external = false;
        self.focused_workspace_visible = false;
        self.synthetic_bundle = None;
        self.synthetic_bundle_selected = None;
        self.synthetic_bundle_history.clear();
        self.synthetic_bundle_visited.clear();
        self.synthetic_bundle_patient = None;
        self.synthetic_bundle_type = "";
        self.synthetic_bundle_notice = None;
        self.encrypted_readback_selected = None;
        self.encrypted_readback_history.clear();
        self.encrypted_readback_filter = RecoveredResourceTypeFilter::All;
        self.encrypted_readback_query.clear();
        self.fictional_walkthrough_done = [false; 3];
        self.encrypted_readback_notice = None;
        self.workspace_report_external = false;
        self.workspace_report_notice = None;
        self.fictional_workspace_selected = None;
        self.fictional_workspace_back = None;
        self.fictional_workspace_detail = None;
        self.fictional_workspace_notice = None;
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
            || !verified_fictional_preview_bytes(*fixture, payload.raw_json)
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
            || !verified_fictional_preview_bytes(*fixture, payload.raw_json)
            || !payload.synthetic_only
            || payload.release_authorized
        {
            return Err("synthetic_comparison_mismatch");
        }
        Ok(payload.raw_json)
    }

    /// Inspect one of three approved source-compiled fictional relations,
    /// using the existing independent raw SHA + D0 envelope verification.
    /// A changed/invalid fixture clears previous evidence before refusal.
    pub fn inspect_selected_relationships(&mut self) -> Result<(), &'static str> {
        self.clear_fictional_output();
        let fixture = match FIXTURES.get(self.selected) {
            Some(fixture) => *fixture,
            None => {
                self.relationship_notice = Some("FAIL CLOSED: invalid fictional selection");
                return Err("invalid_synthetic_selection");
            }
        };
        if !matches!(
            fixture.id,
            "observation-minimal" | "bundle-valid" | "bundle-linked"
        ) {
            self.relationship_notice = Some(
                "Relationship inspection unavailable: this fictional source is not in the reviewed three-source graph",
            );
            return Err("fictional_relation_fixture_not_approved");
        }
        let raw = match Self::verified_json_for(self.selected) {
            Ok(raw) => raw,
            Err(_) => {
                self.relationship_notice =
                    Some("FAIL CLOSED: fictional source digest or structure refused");
                return Err("fictional_relation_verification_refused");
            }
        };
        let edges = match project_pinned_fictional_relations(fixture.id, raw) {
            Ok(edges) if !edges.is_empty() && edges.len() <= 3 => edges,
            _ => {
                self.relationship_notice =
                    Some("FAIL CLOSED: fictional relation or source pointer changed");
                return Err("fictional_relation_projection_refused");
            }
        };
        self.relationships = Some(FictionalRelationView {
            source: fixture,
            edges,
        });
        Ok(())
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

impl MedOriginNativePreview {
    /// Show source-pinned Python Core provenance from the two fixed fictional
    /// QA reports; this deliberately does not launch Python or load a file.
    pub fn inspect_selected_core_receipt(&mut self) -> Result<(), &'static str> {
        self.clear_fictional_output();
        match inspect_pinned_core_report(self.core_report_selection) {
            Ok(receipt) => {
                self.core_report = Some(receipt);
                Ok(())
            }
            Err(_) => {
                self.core_report_notice =
                    Some("FAIL CLOSED: unapproved or changed synthetic Core report");
                Err("core_report_inspection_refused")
            }
        }
    }
}

impl MedOriginNativePreview {
    /// An explicit, local, fictional test intent toggle. This is NOT user
    /// authentication or patient consent. Never persists across restarts.
    fn enter_fictional_workspace(&mut self) {
        self.clear_fictional_output();
        self.fictional_workspace_unlocked = true;
        self.fictional_workspace_filter = FictionalWorkspaceFilter::All;
        self.fictional_workspace_resource_type = FictionalResourceTypeFilter::All;
    }

    fn close_fictional_workspace(&mut self) {
        self.clear_fictional_output();
        self.fictional_workspace_unlocked = false;
        self.fictional_workspace_filter = FictionalWorkspaceFilter::All;
        self.fictional_workspace_resource_type = FictionalResourceTypeFilter::All;
    }

    fn filter_fictional_workspace(&mut self, filter: FictionalWorkspaceFilter) {
        self.clear_fictional_output();
        self.fictional_workspace_filter = filter;
    }

    fn filter_fictional_resource_type(&mut self, filter: FictionalResourceTypeFilter) {
        self.clear_fictional_output();
        self.fictional_workspace_resource_type = filter;
    }

    fn admits_fictional_case(&self, spec: FictionalWorkspaceSpec) -> bool {
        self.fictional_workspace_filter.admits(spec.negative)
            && self
                .fictional_workspace_resource_type
                .admits(spec.resource_type)
    }

    /// A bounded native developer workflow. A case is never a path, record
    /// entered by a user, EHR document, or the result of medical validation.
    fn open_fictional_workspace_case(&mut self, case_index: usize) -> Result<(), &'static str> {
        self.clear_fictional_output();
        if !self.fictional_workspace_unlocked {
            self.fictional_workspace_notice = Some("FAIL CLOSED: fictional workspace is closed");
            return Err("fictional_workspace_closed");
        }
        let Some(spec) = FICTIONAL_WORKSPACE_CASES.get(case_index).copied() else {
            self.fictional_workspace_notice = Some("FAIL CLOSED: unapproved fictional case");
            return Err("fictional_workspace_case_not_allowed");
        };
        if !self.admits_fictional_case(spec) {
            self.fictional_workspace_notice =
                Some("FAIL CLOSED: fictional case not in selected filter");
            return Err("fictional_workspace_case_filtered_out");
        }
        let fixture = FIXTURES
            .get(spec.fixture_index)
            .copied()
            .ok_or("fictional_workspace_index_not_allowed")?;
        let raw = match Self::verified_json_for(spec.fixture_index) {
            Ok(raw) => raw,
            Err(_) => {
                self.fictional_workspace_notice =
                    Some("FAIL CLOSED: fictional source integrity refused");
                return Err("fictional_workspace_source_unverified");
            }
        };
        let parsed: serde_json::Value =
            serde_json::from_str(raw).map_err(|_| "fictional_workspace_invalid_json")?;
        let expected_status = match (spec.negative, spec.resource_type) {
            (true, _) => "INVALID_REFERENCE",
            (false, "Bundle") => "BUNDLE_GRAPH_OK",
            (false, _) => "FHIR_ENVELOPE_OK",
        };
        if parsed
            .get("resourceType")
            .and_then(serde_json::Value::as_str)
            != Some(spec.resource_type)
            || parsed.get("id").and_then(serde_json::Value::as_str) != Some(spec.resource_id)
            || fixture.status != expected_status
        {
            self.fictional_workspace_notice =
                Some("FAIL CLOSED: fictional resource identity or status changed");
            return Err("fictional_workspace_resource_mismatch");
        }
        let relations = if spec.expected_edges == 0 {
            Vec::new()
        } else {
            match project_pinned_fictional_relations(fixture.id, raw) {
                Ok(edges) if edges.len() == spec.expected_edges => edges,
                _ => {
                    self.fictional_workspace_notice =
                        Some("FAIL CLOSED: fictional source relationships changed");
                    return Err("fictional_workspace_relationship_refused");
                }
            }
        };
        self.fictional_workspace_selected = Some(case_index);
        self.fictional_workspace_detail = Some(FictionalWorkspaceDetail {
            fixture,
            resource_type: spec.resource_type,
            resource_id: spec.resource_id,
            negative: spec.negative,
            relations,
        });
        Ok(())
    }

    /// Follow ONLY a relation whose exact source SHA/envelope and fixed graph
    /// have been independently verified again. This is a native user flow,
    /// never a generic FHIR resolver or patient-record navigation.
    fn follow_fictional_relation(&mut self, edge_index: usize) -> Result<(), &'static str> {
        let target = (|| {
            if !self.fictional_workspace_unlocked {
                return Err("fictional_workspace_closed");
            }
            let source_index = self
                .fictional_workspace_selected
                .ok_or("fictional_workspace_source_not_selected")?;
            let spec = FICTIONAL_WORKSPACE_CASES
                .get(source_index)
                .copied()
                .ok_or("fictional_workspace_source_not_approved")?;
            if !self.admits_fictional_case(spec) {
                return Err("fictional_workspace_source_filtered_out");
            }
            let detail = self
                .fictional_workspace_detail
                .as_ref()
                .ok_or("fictional_workspace_source_not_open")?;
            let fixture = FIXTURES
                .get(spec.fixture_index)
                .ok_or("fictional_workspace_source_not_approved")?;
            if detail.fixture.sha256 != fixture.sha256 || detail.fixture.id != fixture.id {
                return Err("fictional_workspace_source_not_verified");
            }
            let raw = Self::verified_json_for(spec.fixture_index)?;
            let edges = project_pinned_fictional_relations(fixture.id, raw)?;
            if edges != detail.relations {
                return Err("fictional_workspace_relation_graph_changed");
            }
            let edge = edges
                .get(edge_index)
                .ok_or("fictional_workspace_relation_not_approved")?;
            let target_index = match (edge.relationship, edge.target) {
                ("fictional_subject_reference", "Patient/synthetic")
                | (
                    "fictional_subject_reference",
                    "urn:uuid:00000000-0000-4000-8000-000000000001",
                )
                | (
                    "fictional_bundle_patient_member",
                    "urn:uuid:00000000-0000-4000-8000-000000000001",
                ) => 0,
                (
                    "fictional_bundle_observation_member",
                    "urn:uuid:00000000-0000-4000-8000-000000000002",
                ) => 1,
                _ => return Err("fictional_workspace_relation_target_not_approved"),
            };
            let target_spec = FICTIONAL_WORKSPACE_CASES
                .get(target_index)
                .copied()
                .ok_or("fictional_workspace_relation_target_not_approved")?;
            if target_spec.negative || !self.admits_fictional_case(target_spec) {
                return Err("fictional_workspace_relation_target_filtered_out");
            }
            Ok((source_index, target_index))
        })();
        let (source_index, target_index) = match target {
            Ok(target) => target,
            Err(reason) => {
                self.clear_fictional_output();
                self.fictional_workspace_notice = Some(
                    "FAIL CLOSED: fictional linked reference is unapproved or hidden by the current filter",
                );
                return Err(reason);
            }
        };
        self.open_fictional_workspace_case(target_index)?;
        self.fictional_workspace_back = Some(source_index);
        Ok(())
    }

    fn back_to_previous_fictional_case(&mut self) -> Result<(), &'static str> {
        let Some(previous) = self.fictional_workspace_back.take() else {
            self.clear_fictional_output();
            self.fictional_workspace_notice = Some("FAIL CLOSED: no previous fictional case");
            return Err("fictional_workspace_no_previous_case");
        };
        self.open_fictional_workspace_case(previous)
    }
}

// The focused native screen keeps one trustworthy source-to-view mapping.
// It never reads files, spawns Core, uses the network or accepts patient input.
impl MedOriginNativePreview {
    fn set_focused_fictional_workspace(&mut self, visible: bool) -> Result<(), &'static str> {
        if visible {
            let admitted = self
                .encrypted_readback
                .as_ref()
                .ok_or("focused_workspace_no_verified_source")
                .and_then(verified_fictional_patient_chart);
            if let Err(reason) = admitted {
                self.clear_fictional_output();
                self.encrypted_readback_notice =
                    Some("FAIL CLOSED: focused fictional Workspace source graph refused");
                return Err(reason);
            }
        }
        self.focused_workspace_visible = visible;
        Ok(())
    }

    fn focused_workspace_ui(&mut self, ui: &mut egui::Ui) {
        ui.heading("MedOrigin focused Workspace");
        ui.strong("Imaginary Core records only. No clinical use, treatment, diagnosis or PHI.");
        let mut leave = false;
        let mut clear = false;
        ui.horizontal(|ui| {
            if ui.button("Focus: Return to developer evidence").clicked() {
                leave = true;
            }
            if ui.button("Focus: Clear fictional session").clicked() {
                clear = true;
            }
        });
        if leave {
            let _ = self.set_focused_fictional_workspace(false);
            return;
        }
        if clear {
            self.clear_fictional_output();
            return;
        }
        let (chart, readback) = match self.encrypted_readback.as_ref() {
            None => {
                ui.label("No verified fictional encrypted Workspace is connected.");
                ui.label("There is no file, patient import or external connection in this view.");
                return;
            }
            Some(readback) => match verified_fictional_patient_chart(readback) {
                Ok(chart) => (chart, readback),
                Err(_) => {
                    self.clear_fictional_output();
                    self.encrypted_readback_notice =
                        Some("FAIL CLOSED: focused fictional Workspace graph changed");
                    ui.label("FAIL CLOSED: source graph could not be verified.");
                    return;
                }
            },
        };
        let resources = readback.resources.clone();
        let source_sha = readback.source_content_sha256.clone();
        let reopened = readback.encrypted_reopen_verified;
        let audited = readback.audit_chain_verified;
        let persistent = readback.persistent_test_vault_reopened;
        let selected = self.encrypted_readback_selected;
        let history_len = self.encrypted_readback_history.len();
        let visited = self.fictional_walkthrough_done;
        let notice = self.encrypted_readback_notice;

        ui.group(|ui| {
            ui.strong("Verified local fictional Workspace");
            ui.label(format!(
                "3 fictional identities | encrypted reopen: {reopened} | audit: {audited}"
            ));
            ui.label(format!(
                "Source: {}",
                if persistent {
                    "Cold-reopened persistent DPAPI QA test vault"
                } else {
                    "Ephemeral encrypted QA test vault, removed after readback"
                }
            ));
            ui.label("Source and freshness are not independently authenticated for clinical use.");
        });
        ui.separator();

        enum FocusAction {
            OpenPatient,
            OpenMember(usize),
            Back,
            Next,
            Mark,
            Reset,
            SetType(RecoveredResourceTypeFilter),
            Search(&'static str),
            Select(usize),
            FollowOutgoing(usize),
            FollowIncoming(usize, usize),
            JumpHistory(usize),
        }
        let mut action: Option<FocusAction> = None;
        ui.heading("Fictional patient context");
        ui.label("Patient, Encounter and Observation shown in source graph order, NOT time order.");
        ui.horizontal_wrapped(|ui| {
            if ui.button("Focus: Open Patient").clicked() {
                action = Some(FocusAction::OpenPatient);
            }
            for index in [chart.encounter, chart.observation] {
                let member = &resources[index];
                if ui
                    .button(format!("Focus: Open {}", member.resource_type))
                    .clicked()
                {
                    action = Some(FocusAction::OpenMember(index));
                }
            }
        });
        ui.separator();
        ui.heading("Source-verified resource browser");
        ui.label("Choose a reviewed resource type or identity keyword; there is no free-text patient input.");
        ui.horizontal_wrapped(|ui| {
            for kind in [
                RecoveredResourceTypeFilter::All,
                RecoveredResourceTypeFilter::Patient,
                RecoveredResourceTypeFilter::Encounter,
                RecoveredResourceTypeFilter::Observation,
            ] {
                if ui.button(format!("Focus: Type {}", kind.label())).clicked() {
                    action = Some(FocusAction::SetType(kind));
                }
            }
        });
        ui.horizontal_wrapped(|ui| {
            for (label, query) in [
                ("All", ""),
                ("Patient", "patient"),
                ("Encounter", "encounter"),
                ("Observation", "observation"),
            ] {
                if ui.button(format!("Focus: Find {label}")).clicked() {
                    action = Some(FocusAction::Search(query));
                }
            }
        });
        ui.label(format!(
            "Focus: Active type {} | identity keyword {}",
            self.encrypted_readback_filter.label(),
            if self.encrypted_readback_query.is_empty() {
                "All"
            } else {
                self.encrypted_readback_query.as_str()
            }
        ));
        ui.strong(format!(
            "Focus: {} of 3 source-verified fictional resources visible",
            self.recovered_visible_count()
        ));
        let mut visible = 0usize;
        for (index, resource) in resources.iter().enumerate() {
            if !self.recovered_search_matches(resource) {
                continue;
            }
            visible += 1;
            if ui
                .button(format!(
                    "Focus: Inspect {}/{}",
                    resource.resource_type, resource.resource_id
                ))
                .clicked()
            {
                action = Some(FocusAction::Select(index));
            }
        }
        if visible == 0 {
            ui.label("No fictional resources match the chosen type and identity keyword.");
        }
        ui.separator();
        ui.strong(format!(
            "Fictional walkthrough: {} of 3 visited this session",
            visited.iter().filter(|done| **done).count()
        ));
        ui.horizontal_wrapped(|ui| {
            if ui.button("Focus: Next unvisited").clicked() {
                action = Some(FocusAction::Next);
            }
            if ui.button("Focus: Reset visits").clicked() {
                action = Some(FocusAction::Reset);
            }
        });
        if let Some(index) = selected
            && let Some(resource) = resources.get(index)
        {
            ui.group(|ui| {
                ui.strong(format!(
                    "Focused fictional record: {}/{}",
                    resource.resource_type, resource.resource_id
                ));
                ui.monospace(format!("Verified source reference: {}", resource.full_url));
                ui.label(format!(
                    "Session visit status: {}",
                    if visited[index] {
                        "visited"
                    } else {
                        "not visited"
                    }
                ));
                if !visited[index] && ui.button("Focus: Mark visited (demo only)").clicked() {
                    action = Some(FocusAction::Mark);
                }
                let incoming_count = resources
                    .iter()
                    .flat_map(|source| source.links.iter())
                    .filter(|link| link.target == resource.full_url)
                    .count();
                ui.strong(format!(
                    "Focus: {} outgoing and {} incoming source links",
                    resource.links.len(),
                    incoming_count
                ));
                for (link_index, link) in resource.links.iter().enumerate() {
                    if let Some(destination) = resources
                        .iter()
                        .find(|candidate| candidate.full_url == link.target)
                    {
                        if ui
                            .button(format!(
                                "Focus: Follow outgoing {} to {}/{}",
                                link.field, destination.resource_type, destination.resource_id
                            ))
                            .clicked()
                        {
                            action = Some(FocusAction::FollowOutgoing(link_index));
                        }
                    } else {
                        // Never invent a destination when a source edge is missing.
                        ui.label("FAIL CLOSED: source-projected outgoing link unresolved");
                    }
                }
                for (source_index, source) in resources.iter().enumerate() {
                    for (link_index, link) in source.links.iter().enumerate() {
                        if link.target == resource.full_url
                            && ui
                                .button(format!(
                                    "Focus: Open incoming {}/{} via {}",
                                    source.resource_type, source.resource_id, link.field
                                ))
                                .clicked()
                        {
                            action = Some(FocusAction::FollowIncoming(source_index, link_index));
                        }
                    }
                }
                if history_len > 0 {
                    ui.strong(format!(
                        "Focus: Verified navigation trail {} of 16 steps",
                        history_len
                    ));
                    for (step, previous_index) in self.encrypted_readback_history.iter().enumerate()
                    {
                        if let Some(previous) = resources.get(*previous_index)
                            && ui
                                .button(format!(
                                    "Focus: Jump history {}: {}/{}",
                                    step + 1,
                                    previous.resource_type,
                                    previous.resource_id
                                ))
                                .clicked()
                        {
                            action = Some(FocusAction::JumpHistory(step));
                        }
                    }
                    if ui.button("Focus: Back along verified path").clicked() {
                        action = Some(FocusAction::Back);
                    }
                }
                ui.label("No clinical note, event date, order, diagnosis or status was inferred.");
            });
        } else {
            ui.label("Select a fictional resource to view its verified identity and references.");
        }
        if let Some(notice) = notice {
            ui.label(notice);
        }
        ui.collapsing("Source verification information", |ui| {
            ui.monospace(format!("Original synthetic Bundle SHA-256: {source_sha}"));
            ui.label(
                "Identity and links are admitted from an exact source-reviewed Core projection.",
            );
        });
        match action {
            Some(FocusAction::OpenPatient) => {
                let _ = self.open_recovered_fictional_patient_chart();
            }
            Some(FocusAction::OpenMember(index)) => {
                if self.open_recovered_fictional_patient_chart().is_ok() {
                    let _ = self.open_recovered_fictional_patient_chart_member(index);
                }
            }
            Some(FocusAction::Back) => {
                let _ = self.back_encrypted_readback_resource();
            }
            Some(FocusAction::Next) => {
                let _ = self.next_unvisited_fictional_resource();
            }
            Some(FocusAction::Mark) => {
                let _ = self.mark_selected_fictional_walkthrough();
            }
            Some(FocusAction::Reset) => {
                let _ = self.reset_fictional_walkthrough();
            }
            Some(FocusAction::SetType(kind)) => {
                self.set_recovered_type_filter(kind);
            }
            Some(FocusAction::Search(query)) => {
                let _ = self.set_recovered_search_query(query);
            }
            Some(FocusAction::Select(index)) => {
                let _ = self.select_encrypted_readback_resource(index);
            }
            Some(FocusAction::FollowOutgoing(link_index)) => {
                let _ = self.follow_encrypted_readback_link(link_index);
            }
            Some(FocusAction::FollowIncoming(source_index, link_index)) => {
                let _ = self.follow_encrypted_readback_incoming(source_index, link_index);
            }
            Some(FocusAction::JumpHistory(step)) => {
                let _ = self.jump_encrypted_readback_history(step);
            }
            None => {}
        }
    }
}

// A second, independent STRUCTURAL ONLY multi-patient FHIR-shaped preview.
// It cannot be promoted to the SHA-pinned encrypted Core readback, has no
// clinical fields or free-text import, and has no filesystem/network access.
impl MedOriginNativePreview {
    fn bundle_visible(&self, index: usize) -> bool {
        let Some(bundle) = self.synthetic_bundle.as_ref() else {
            return false;
        };
        let Some(resource) = bundle.resources.get(index) else {
            return false;
        };
        (self.synthetic_bundle_type == "All"
            || self.synthetic_bundle_type == resource.resource_type)
            && self
                .synthetic_bundle_patient
                .is_none_or(|patient| bundle.owner_patient(index) == Some(patient))
    }

    fn bundle_select(&mut self, index: usize) -> Result<(), &'static str> {
        if !self.bundle_visible(index) {
            self.clear_fictional_output();
            return Err("synthetic_bundle_hidden_or_unknown_selection");
        }
        let expected = self
            .synthetic_bundle
            .as_ref()
            .map_or(0, |bundle| bundle.resources.len());
        if self.synthetic_bundle_visited.len() != expected {
            self.clear_fictional_output();
            return Err("synthetic_bundle_exploration_state_refused");
        }
        self.synthetic_bundle_selected = Some(index);
        self.synthetic_bundle_visited[index] = true;
        self.synthetic_bundle_history.clear();
        self.synthetic_bundle_notice = None;
        Ok(())
    }

    fn bundle_set_patient(&mut self, patient: Option<usize>) -> Result<(), &'static str> {
        if let Some(index) = patient
            && !self.synthetic_bundle.as_ref().is_some_and(|bundle| {
                bundle
                    .resources
                    .get(index)
                    .is_some_and(|resource| resource.resource_type == "Patient")
            })
        {
            self.clear_fictional_output();
            return Err("synthetic_bundle_patient_group_refused");
        }
        self.synthetic_bundle_patient = patient;
        self.synthetic_bundle_type = "All";
        self.synthetic_bundle_selected = None;
        self.synthetic_bundle_history.clear();
        self.synthetic_bundle_notice = None;
        Ok(())
    }

    // Fast, bounded navigation for up to 16 fake patient groups. Only actual
    // Patient resources from the admitted source may become a group.
    fn bundle_step_patient_group(&mut self, forward: bool) -> Result<(), &'static str> {
        let bundle = self
            .synthetic_bundle
            .as_ref()
            .ok_or("synthetic_bundle_missing")?;
        let patients: Vec<usize> = bundle
            .resources
            .iter()
            .enumerate()
            .filter_map(|(index, record)| (record.resource_type == "Patient").then_some(index))
            .collect();
        if patients.len() != bundle.patient_count || patients.is_empty() {
            self.clear_fictional_output();
            return Err("synthetic_bundle_patient_groups_invalid");
        }
        let target = match self.synthetic_bundle_patient {
            None if forward => patients.first(),
            None => patients.last(),
            Some(current) => {
                let Some(position) = patients.iter().position(|index| *index == current) else {
                    self.clear_fictional_output();
                    return Err("synthetic_bundle_unknown_current_group");
                };
                if forward {
                    patients.get(position + 1)
                } else {
                    position
                        .checked_sub(1)
                        .and_then(|index| patients.get(index))
                }
            }
        };
        let Some(&index) = target else {
            return Err("synthetic_bundle_patient_group_boundary");
        };
        self.bundle_set_patient(Some(index))
    }

    fn bundle_set_type(&mut self, kind: &'static str) -> Result<(), &'static str> {
        if !["All", "Patient", "Encounter", "Observation"].contains(&kind) {
            self.clear_fictional_output();
            return Err("synthetic_bundle_unknown_facet");
        }
        self.synthetic_bundle_type = kind;
        self.synthetic_bundle_selected = None;
        self.synthetic_bundle_history.clear();
        self.synthetic_bundle_notice = None;
        Ok(())
    }

    // Session-only exploration, not clinical sign-off or persistent review.
    // Patient and type facets are composed with these source-derived IDs.
    fn bundle_open_next_unexplored(&mut self) -> Result<(), &'static str> {
        let bundle = self
            .synthetic_bundle
            .as_ref()
            .ok_or("synthetic_bundle_missing")?;
        if self.synthetic_bundle_visited.len() != bundle.resources.len() {
            self.clear_fictional_output();
            return Err("synthetic_bundle_exploration_state_refused");
        }
        let next = (0..bundle.resources.len())
            .find(|index| self.bundle_visible(*index) && !self.synthetic_bundle_visited[*index]);
        let Some(index) = next else {
            return Err("synthetic_bundle_no_unexplored_visible_records");
        };
        self.bundle_select(index)
    }

    fn bundle_reset_exploration(&mut self) -> Result<(), &'static str> {
        let bundle = self
            .synthetic_bundle
            .as_ref()
            .ok_or("synthetic_bundle_missing")?;
        if self.synthetic_bundle_visited.len() != bundle.resources.len() {
            self.clear_fictional_output();
            return Err("synthetic_bundle_exploration_state_refused");
        }
        self.synthetic_bundle_visited.fill(false);
        self.synthetic_bundle_selected = None;
        self.synthetic_bundle_history.clear();
        self.synthetic_bundle_notice = None;
        Ok(())
    }

    // Walk only the *currently visible* fictional worklist, never an
    // unrelated patient group or a hidden type facet. Direct worklist
    // selection resets graph history, just like clicking a record.
    fn bundle_step_visible(&mut self, forward: bool) -> Result<(), &'static str> {
        let bundle = self
            .synthetic_bundle
            .as_ref()
            .ok_or("synthetic_bundle_missing")?;
        let available: Vec<usize> = (0..bundle.resources.len())
            .filter(|index| self.bundle_visible(*index))
            .collect();
        let target = match self.synthetic_bundle_selected {
            Some(current) => {
                let Some(position) = available.iter().position(|index| *index == current) else {
                    self.clear_fictional_output();
                    return Err("synthetic_bundle_stale_worklist_selection");
                };
                if forward {
                    available.get(position + 1)
                } else {
                    position
                        .checked_sub(1)
                        .and_then(|index| available.get(index))
                }
            }
            None if forward => available.first(),
            None => available.last(),
        };
        let Some(&target) = target else {
            return Err("synthetic_bundle_worklist_boundary");
        };
        self.bundle_select(target)
    }

    fn bundle_move(&mut self, index: usize) -> Result<(), &'static str> {
        let Some(bundle) = self.synthetic_bundle.as_ref() else {
            return Err("synthetic_bundle_missing");
        };
        let destination = bundle.owner_patient(index);
        if index >= bundle.resources.len()
            || destination.is_none()
            || self.synthetic_bundle_history.len() >= 24
        {
            self.clear_fictional_output();
            return Err("synthetic_bundle_history_or_destination_refused");
        }
        let Some(current) = self.synthetic_bundle_selected else {
            self.clear_fictional_output();
            return Err("synthetic_bundle_no_current_resource");
        };
        if current >= bundle.resources.len() {
            self.clear_fictional_output();
            return Err("synthetic_bundle_stale_current_resource");
        }
        self.synthetic_bundle_history.push(current);
        self.synthetic_bundle_patient = destination;
        self.synthetic_bundle_type = "All";
        self.synthetic_bundle_selected = Some(index);
        if self.synthetic_bundle_visited.len() != bundle.resources.len() {
            self.clear_fictional_output();
            return Err("synthetic_bundle_exploration_state_refused");
        }
        self.synthetic_bundle_visited[index] = true;
        self.synthetic_bundle_notice = None;
        Ok(())
    }

    fn bundle_follow_outgoing(&mut self, link_index: usize) -> Result<(), &'static str> {
        let destination = (|| {
            let bundle = self.synthetic_bundle.as_ref()?;
            let current = bundle.resources.get(self.synthetic_bundle_selected?)?;
            let link = current.links.get(link_index)?;
            bundle.index_for(&link.target)
        })();
        match destination {
            Some(index) => self.bundle_move(index),
            None => {
                self.clear_fictional_output();
                Err("synthetic_bundle_outgoing_reference_refused")
            }
        }
    }

    fn bundle_follow_incoming(
        &mut self,
        source_index: usize,
        link_index: usize,
    ) -> Result<(), &'static str> {
        let matches = self.synthetic_bundle.as_ref().is_some_and(|bundle| {
            self.synthetic_bundle_selected
                .and_then(|target| bundle.resources.get(target))
                .is_some_and(|target| {
                    bundle
                        .resources
                        .get(source_index)
                        .and_then(|source| source.links.get(link_index))
                        .is_some_and(|edge| edge.target == target.full_url)
                })
        });
        if !matches {
            self.clear_fictional_output();
            return Err("synthetic_bundle_incoming_reference_refused");
        }
        self.bundle_move(source_index)
    }

    fn bundle_back(&mut self) -> Result<(), &'static str> {
        let Some(previous) = self.synthetic_bundle_history.pop() else {
            return Err("synthetic_bundle_no_history");
        };
        let dest = self
            .synthetic_bundle
            .as_ref()
            .and_then(|bundle| bundle.owner_patient(previous));
        match dest {
            Some(owner) => {
                self.synthetic_bundle_selected = Some(previous);
                self.synthetic_bundle_patient = Some(owner);
                self.synthetic_bundle_type = "All";
                Ok(())
            }
            None => {
                self.clear_fictional_output();
                Err("synthetic_bundle_stale_history_refused")
            }
        }
    }

    fn synthetic_bundle_ui(&mut self, ui: &mut egui::Ui) {
        let Some(bundle) = self.synthetic_bundle.clone() else {
            return;
        };
        // Never index per-record progress until it matches the admitted source.
        if self.synthetic_bundle_visited.len() != bundle.resources.len() {
            self.clear_fictional_output();
            return;
        }
        enum Action {
            Clear,
            Patient(Option<usize>),
            PatientStep(bool),
            Type(&'static str),
            Select(usize),
            Step(bool),
            NextUnexplored,
            ResetExploration,
            Follow(usize),
            Incoming(usize, usize),
            Back,
        }
        let mut next: Option<Action> = None;
        egui::ScrollArea::vertical().show(ui, |ui| {
            ui.heading("MedOrigin — Fictional Multi-Patient Workspace");
            ui.strong("STRUCTURAL DEMO ONLY — no clinical content, patient identity, EHR or PHI.");
            ui.label(format!(
                "{} imaginary source-only records across {} fictional patients",
                bundle.resources.len(), bundle.patient_count
            ));
            ui.label("Read-only FHIR-shaped Bundle. No encrypted Core connection or authenticated sender.");
            if ui.button("Bundle: Clear fictional records").clicked() {
                next = Some(Action::Clear);
            }
            ui.separator();
            ui.strong("Fictional patient groups");
            let group_label = self
                .synthetic_bundle_patient
                .and_then(|index| bundle.resources.get(index))
                .map_or("All imaginary patients", |patient| patient.resource_id.as_str());
            ui.label(format!("Bundle: Active fictional patient group: {group_label}"));
            ui.horizontal_wrapped(|ui| {
                if ui.button("Bundle: Previous patient group").clicked() {
                    next = Some(Action::PatientStep(false));
                }
                if ui.button("Bundle: Next patient group").clicked() {
                    next = Some(Action::PatientStep(true));
                }
                if ui.button("Bundle: All patients").clicked() {
                    next = Some(Action::Patient(None));
                }
                if bundle.patient_count <= 4 {
                    for (index, record) in bundle.resources.iter().enumerate() {
                        if record.resource_type == "Patient"
                            && ui
                                .button(format!("Bundle: Patient {}", record.resource_id))
                                .clicked()
                        {
                            next = Some(Action::Patient(Some(index)));
                        }
                    }
                }
            });
            // Avoid rendering sixteen patient buttons in the primary toolbar.
            // All source-derived groups remain available on demand.
            if bundle.patient_count > 4 {
                ui.collapsing("Bundle: Choose fictional patient by ID", |ui| {
                    ui.horizontal_wrapped(|ui| {
                        for (index, record) in bundle.resources.iter().enumerate() {
                            if record.resource_type == "Patient"
                                && ui
                                    .button(format!("Bundle: Patient {}", record.resource_id))
                                    .clicked()
                            {
                                next = Some(Action::Patient(Some(index)));
                            }
                        }
                    });
                });
            }
            ui.strong("Resource types");
            ui.horizontal_wrapped(|ui| {
                for kind in ["All", "Patient", "Encounter", "Observation"] {
                    if ui.button(format!("Bundle: Type {kind}")).clicked() {
                        next = Some(Action::Type(kind));
                    }
                }
            });
            let visible = (0..bundle.resources.len())
                .filter(|index| self.bundle_visible(*index))
                .count();
            ui.strong(format!(
                "Bundle: {} of {} fictional resources visible",
                visible, bundle.resources.len()
            ));
            let visited_visible = (0..bundle.resources.len())
                .filter(|index| self.bundle_visible(*index) && self.synthetic_bundle_visited[*index])
                .count();
            ui.label(format!(
                "Bundle exploration: {} of {} visible fictional records opened (session only, NOT review)",
                visited_visible, visible
            ));
            ui.horizontal(|ui| {
                if ui
                    .add_enabled(
                        visible > visited_visible,
                        egui::Button::new("Bundle: Open next unexplored visible record"),
                    )
                    .clicked()
                {
                    next = Some(Action::NextUnexplored);
                }
                if ui
                    .add_enabled(
                        self.synthetic_bundle_visited.iter().any(|was_opened| *was_opened),
                        egui::Button::new("Bundle: Reset session exploration"),
                    )
                    .clicked()
                {
                    next = Some(Action::ResetExploration);
                }
            });
            if visible > 0 {
                ui.horizontal(|ui| {
                    if ui.button("Bundle: Previous visible record").clicked() {
                        next = Some(Action::Step(false));
                    }
                    if ui.button("Bundle: Next visible record").clicked() {
                        next = Some(Action::Step(true));
                    }
                });
            }
            for (index, resource) in bundle.resources.iter().enumerate() {
                if self.bundle_visible(index)
                    && ui
                        .button(format!(
                            "Bundle: Open {}/{}",
                            resource.resource_type, resource.resource_id
                        ))
                        .clicked()
                {
                    next = Some(Action::Select(index));
                }
            }
            if visible == 0 {
                ui.label("No fictional resources for this patient group and type.");
            }
            ui.separator();
            if let Some(index) = self.synthetic_bundle_selected
                && let Some(current) = bundle.resources.get(index)
            {
                ui.strong(format!(
                    "Bundle record: {}/{}",
                    current.resource_type, current.resource_id
                ));
                ui.monospace(format!("Verified fictional URN: {}", current.full_url));
                let incoming = bundle.resources.iter()
                    .flat_map(|resource| resource.links.iter())
                    .filter(|link| link.target == current.full_url)
                    .count();
                ui.label(format!(
                    "Bundle: {} outgoing and {} incoming local references",
                    current.links.len(), incoming
                ));
                for (link_index, link) in current.links.iter().enumerate() {
                    if let Some(target) = bundle.index_for(&link.target)
                        && let Some(resource) = bundle.resources.get(target)
                        && ui
                            .button(format!(
                                "Bundle: Follow {} to {}/{}",
                                link.field, resource.resource_type, resource.resource_id
                            ))
                            .clicked()
                    {
                        next = Some(Action::Follow(link_index));
                    }
                }
                for (source_index, source) in bundle.resources.iter().enumerate() {
                    for (link_index, link) in source.links.iter().enumerate() {
                        if link.target == current.full_url
                            && ui
                                .button(format!(
                                    "Bundle: Incoming {}/{} via {}",
                                    source.resource_type, source.resource_id, link.field
                                ))
                                .clicked()
                        {
                            next = Some(Action::Incoming(source_index, link_index));
                        }
                    }
                }
                if !self.synthetic_bundle_history.is_empty() {
                    ui.label(format!(
                        "Bundle: {} of 24 navigation steps",
                        self.synthetic_bundle_history.len()
                    ));
                    if ui.button("Bundle: Back to previous resource").clicked() {
                        next = Some(Action::Back);
                    }
                }
                ui.label("No clinical values, names, dates, codes or notes accepted in this preview.");
            } else {
                ui.label("Choose a fictional resource from the reviewed patient group.");
            }
            if let Some(notice) = self.synthetic_bundle_notice {
                ui.label(notice);
            }
            ui.collapsing("Structural source evidence (not identity proof)", |ui| {
                ui.monospace(format!("Canonical synthetic Bundle SHA-256: {}", bundle.sha256));
                ui.label("Source input is untrusted and no FHIR R4 profile conformance is asserted.");
            });
        });
        match next {
            Some(Action::Clear) => self.clear_fictional_output(),
            Some(Action::Patient(index)) => {
                let _ = self.bundle_set_patient(index);
            }
            Some(Action::PatientStep(forward)) => {
                let _ = self.bundle_step_patient_group(forward);
            }
            Some(Action::Type(kind)) => {
                let _ = self.bundle_set_type(kind);
            }
            Some(Action::Select(index)) => {
                let _ = self.bundle_select(index);
            }
            Some(Action::Step(forward)) => {
                let _ = self.bundle_step_visible(forward);
            }
            Some(Action::NextUnexplored) => {
                let _ = self.bundle_open_next_unexplored();
            }
            Some(Action::ResetExploration) => {
                let _ = self.bundle_reset_exploration();
            }
            Some(Action::Follow(index)) => {
                let _ = self.bundle_follow_outgoing(index);
            }
            Some(Action::Incoming(source, link)) => {
                let _ = self.bundle_follow_incoming(source, link);
            }
            Some(Action::Back) => {
                let _ = self.bundle_back();
            }
            None => {}
        }
    }
}

impl MedOriginNativePreview {
    fn protected_audit_ui(&mut self, ui: &mut egui::Ui) {
        let Some(audit) = self.protected_audit.clone() else {
            return;
        };
        egui::ScrollArea::vertical().show(ui, |ui| {
            ui.heading("MedOrigin — Protected fictional Workspace status");
            ui.strong("Windows Credential Manager-backed audit verification (DEVELOPER QA ONLY)");
            ui.label("A separate Core process reported an anchored cold-reopen of an encrypted fictional Workspace.");
            ui.strong(format!(
                "Protected audit: {} independently anchored fictional event verified",
                audit.verified_events
            ));
            ui.label("Audit anchor matched. Root credential was NOT deleted. Encrypted store remains on disk.");
            ui.label("NO patient records were imported. No clinical FHIR validation, access roles or production key custody.");
            ui.label("This per-launch HMAC result is not a signed Core identity or an authorization to use patient data.");
            ui.collapsing("Protected audit: Report fingerprint (not signer attestation)", |ui| {
                ui.monospace(format!(
                    "Redacted verification receipt SHA-256: {}",
                    audit.receipt_sha256
                ));
            });
            if ui.button("Protected audit: Clear verification result").clicked() {
                self.clear_fictional_output();
            }
            ui.label("Keyboard: Tab / Shift+Tab to navigate, Space to select, Escape to clear.");
        });
    }

    fn core_file_batch_ui(&mut self, ui: &mut egui::Ui) {
        let Some(batch) = self.core_file_batch.clone() else {
            return;
        };
        enum Action {
            Clear,
            Select(usize),
            Step(bool),
            NextUninspected,
            ActivityOnly(bool),
            Reset,
        }
        let mut action = None;
        egui::ScrollArea::vertical().show(ui, |ui| {
            ui.heading("MedOrigin - Core encrypted fictional file batch");
            ui.strong("REDACTED RECEIPT ONLY - no patient chart, imported clinical record or PHI.");
            ui.label("Source-shaped Core v1 report; transport sender and freshness NOT authenticated.");
            ui.label("Source reports actual ephemeral encrypted Workspace close/reopen and audit, not independently re-executed inside this Desktop.");
            ui.label(format!(
                "Core: {} independent fictional imports; {} total resources; {} reconstructed timeline events",
                batch.imports.len(), batch.resource_count, batch.timeline_event_count
            ));
            ui.label("Every import has one separately scoped imaginary patient. No cross-import identity joining.");
            ui.label("No FHIR R4 conformance, release approval, clinical storage, production key custody or real patient use.");
            if batch.official_r4_structure_checked {
                ui.strong(format!(
                    "Official R4: {} of {} invented files structurally assessed (NOT FHIR validated)",
                    batch.imports.len(), batch.imports.len()
                ));
                ui.label("Offline official HL7 R4 v4.0.1 JSON Schema structure-only preflight was reported BEFORE the ephemeral encrypted import. No profiles, terminology or clinical approval.");
            } else {
                ui.label("Official R4: no source-reported structural preflight in this legacy receipt.");
            }
            if ui.button("Core batch: Clear redacted receipt").clicked() {
                action = Some(Action::Clear);
            }
            ui.separator();
            let visible = (0..batch.imports.len())
                .filter(|index| self.core_batch_visible(*index)).count();
            let inspected = (0..batch.imports.len())
                .filter(|index| self.core_batch_visible(*index)
                    && self.core_file_batch_inspected.get(*index) == Some(&true))
                .count();
            ui.strong(format!(
                "Core batch exploration: {} of {} visible fictional imports opened (session only, NOT clinical review)",
                inspected, visible
            ));
            ui.horizontal_wrapped(|ui| {
                if ui.button("Core batch: Previous visible import").clicked() {
                    action = Some(Action::Step(false));
                }
                if ui.button("Core batch: Next visible import").clicked() {
                    action = Some(Action::Step(true));
                }
                if ui.button("Core batch: Open next unexplored import").clicked() {
                    action = Some(Action::NextUninspected);
                }
            });
            ui.horizontal_wrapped(|ui| {
                if self.core_file_batch_activity_only {
                    if ui.button("Core batch: Show all imports").clicked() {
                        action = Some(Action::ActivityOnly(false));
                    }
                } else if ui.button("Core batch: Only imports with activity").clicked() {
                    action = Some(Action::ActivityOnly(true));
                }
                if ui.button("Core batch: Reset session exploration").clicked() {
                    action = Some(Action::Reset);
                }
            });
            if let Some(message) = self.core_file_batch_notice {
                ui.label(message);
            }
            ui.separator();
            ui.columns(2, |columns| {
                columns[0].strong("Source-scoped fictional encrypted import summaries");
                for (index, source) in batch.imports.iter().enumerate() {
                    if !self.core_batch_visible(index) {
                        continue;
                    }
                    columns[0].group(|ui| {
                        ui.strong(format!(
                            "Core batch: Import {} - {} source resources, {} verified timeline events",
                            source.ordinal, source.resource_count, source.timeline_event_count
                        ));
                        ui.label(if self.core_file_batch_selected == Some(index) {
                            "Selected import (imaginary source only)"
                        } else if self.core_file_batch_inspected.get(index) == Some(&true) {
                            "Opened this session (NOT clinical review)"
                        } else {
                            "Not opened this session"
                        });
                        if ui.button(format!("Core batch: Open import {}", source.ordinal)).clicked() {
                            action = Some(Action::Select(index));
                        }
                    });
                }
                columns[1].strong("Fictional source details (read-only)");
                if let Some(index) = self.core_file_batch_selected {
                    if self.core_batch_visible(index)
                        && self.core_file_batch_inspected.get(index) == Some(&true)
                    {
                        if let Some(source) = batch.imports.get(index) {
                            columns[1].heading(format!("Core batch: Selected import {}", source.ordinal));
                            columns[1].label(format!("Core batch: Selected source resources: {}", source.resource_count));
                            columns[1].label(format!(
                                "Core batch: Selected fictional timeline events: {}",
                                source.timeline_event_count
                            ));
                            columns[1].label("Source-scoped summary only. No clinical values, patient name or encounter identity.");
                            if batch.official_r4_structure_checked {
                                columns[1].strong(format!(
                                    "Core batch: Import {} R4 structure: source-reported checked, NOT FHIR validated",
                                    source.ordinal
                                ));
                            } else {
                                columns[1].label(format!(
                                    "Core batch: Import {} R4 structure: not assessed in legacy receipt",
                                    source.ordinal
                                ));
                            }
                            columns[1].collapsing(
                                format!("Core batch: Audit anchors for import {}", source.ordinal),
                                |ui| {
                                    ui.monospace(format!("Source SHA-256: {}", source.source_sha256));
                                    ui.monospace(format!("Import audit SHA-256: {}", source.audit_sha256));
                                    ui.label("Reported hashes, NOT sender attestation or signed medical review.");
                                },
                            );
                        }
                    } else {
                        columns[1].label("Selected fictional source is hidden; open a visible import.");
                    }
                } else {
                    columns[1].label("Core batch: No fictional import opened this session");
                }
            });
            ui.separator();
            ui.collapsing("Core batch: Report fingerprint (not attestation)", |ui| {
                ui.monospace(format!("Canonical receipt SHA-256: {}", batch.receipt_sha256));
                ui.monospace(format!("Last import audit SHA-256: {}", batch.audit_head_sha256));
                ui.label("Hashes identify reported bytes only; they do not prove the source process or real patients.");
            });
        });
        match action {
            Some(Action::Clear) => self.clear_fictional_output(),
            Some(Action::Select(index)) => {
                let _ = self.core_batch_select(index);
            }
            Some(Action::Step(forward)) => {
                let _ = self.core_batch_step(forward);
            }
            Some(Action::NextUninspected) => {
                let _ = self.core_batch_next_uninspected();
            }
            Some(Action::ActivityOnly(only)) => {
                let _ = self.core_batch_activity_filter(only);
            }
            Some(Action::Reset) => {
                let _ = self.core_batch_reset_exploration();
            }
            None => {}
        }
    }
}

impl eframe::App for MedOriginNativePreview {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        if ui.input(|input| input.key_pressed(egui::Key::Escape)) {
            self.clear_fictional_output();
        }
        if self.protected_audit.is_some() {
            egui::CentralPanel::default().show(ui, |ui| self.protected_audit_ui(ui));
            return;
        }
        if self.core_file_batch.is_some() {
            egui::CentralPanel::default().show(ui, |ui| self.core_file_batch_ui(ui));
            return;
        }
        if self.synthetic_bundle.is_some() {
            egui::CentralPanel::default().show(ui, |ui| self.synthetic_bundle_ui(ui));
            return;
        }
        if self.focused_workspace_visible {
            egui::CentralPanel::default().show(ui, |ui| self.focused_workspace_ui(ui));
            return;
        }
        egui::CentralPanel::default().show(ui, |ui| {
            ui.heading("MedOrigin — Native Rust Experiment");
            ui.strong("Synthetic developer preview only · No EHR · No clinical use");
            ui.label("No browser engine, IPC server, Python worker, filesystem input or model is used in this proof of concept.");
            // This top-level native home is directly usable without scrolling
            // through historical developer fixtures. It exposes no PHI and
            // cannot create a patient, write to SQLite, or launch Core.
            let mut open_home_chart = false;
            let mut walkthrough_next = false;
            let mut walkthrough_reset = false;
            ui.group(|ui| {
                ui.heading("Workspace home: fictional Core source only");
                if let Some(readback) = &self.encrypted_readback {
                    ui.strong(format!(
                        "Verified fictional resources: {} (read-only)",
                        readback.resources.len()
                    ));
                    ui.label(format!(
                        "Workspace source: {}",
                        if readback.persistent_test_vault_reopened {
                            "Cold-reopened persistent QA encrypted test vault"
                        } else {
                            "Reopened ephemeral encrypted test vault (removed after QA)"
                        }
                    ));
                    ui.label(format!(
                        "Encrypted reopen: {} | Audit: {}",
                        readback.encrypted_reopen_verified, readback.audit_chain_verified
                    ));
                    ui.label("Only source-approved imaginary FHIR-shaped identities; no real patient data.");
                    if ui.button("Open workspace home: fictional patient chart").clicked() {
                        open_home_chart = true;
                    }
                    if ui.button("Open focused fictional Workspace").clicked() {
                        let _ = self.set_focused_fictional_workspace(true);
                    }
                    ui.separator();
                    ui.strong(format!(
                        "Fictional session walkthrough: {} of 3 identities visited",
                        self.fictional_walkthrough_done.iter().filter(|done| **done).count()
                    ));
                    ui.label("Walkthrough means only a fictional demo navigation step; NOT clinician review, diagnosis or signed approval.");
                    if ui.button("Open next unvisited fictional identity").clicked() {
                        walkthrough_next = true;
                    }
                    if ui.button("Reset fictional walkthrough (session only)").clicked() {
                        walkthrough_reset = true;
                    }
                } else {
                    ui.label("No verified encrypted Core Workspace is attached to this GUI session.");
                    ui.label("Launch the separate fictional-only portable Core demo to display verified identities.");
                }
            });
            if open_home_chart {
                let _ = self.open_recovered_fictional_patient_chart();
            }
            if walkthrough_next {
                let _ = self.next_unvisited_fictional_resource();
            }
            if walkthrough_reset {
                let _ = self.reset_fictional_walkthrough();
            }
            ui.separator();
            // Keep all four original controls visible in the same order.
            // This retains the testable AX/UIA keyboard contract from D2.
            ui.label("Choose one of four fictional, in-memory fixtures:");
            for (index, fixture) in FIXTURES[..PRIMARY_FIXTURE_COUNT].iter().enumerate() {
                if ui.selectable_label(self.selected == index, format!("{} ({} bytes)", fixture.id, fixture.bytes)).clicked() {
                    self.selected = index;
                    self.clear_fictional_output();
                }
            }
            if ui.button("Verify synthetic SHA-256").clicked() {
                let _ = self.hash_selected();
            }
            if self.encrypted_readback.is_none() {
                ui.label("Explore the compiled, source-reviewed fictional Bundle without importing any files.");
                if ui
                    .button("Open built-in two-patient fictional demo (NO PHI)")
                    .clicked()
                {
                    let _ = self.open_embedded_fictional_bundle_demo();
                    return;
                }
            }
            if let Some(result) = &self.result {
                // Preserve the original standalone UIA/AX SHA text node. The
                // FHIR status is a distinct accessible node for screen readers.
                for line in result.lines() {
                    ui.monospace(line);
                }
            }
            // Real, canonical reports emitted by pinned Python Core for TWO
            // fictional QA cases, embedded as build-time bytes. All admission
            // is reverified locally on click; NO live Core worker or file IO.
            egui::CollapsingHeader::new("Core provenance: two fictional reports (NOT validated)")
                .default_open(self.external_core_source_visible)
                .show(ui, |ui| {
                    ui.strong("Source-compiled Python Core QA receipts. NOT live or clinical.");
                    for (index, label) in PINNED_CORE_CASE_LABELS.iter().enumerate() {
                        if ui
                            .selectable_label(self.core_report_selection == index, *label)
                            .clicked()
                        {
                            self.core_report_selection = index;
                            self.clear_fictional_output();
                        }
                    }
                    if ui
                        .button("Inspect Core synthetic provenance (read-only)")
                        .clicked()
                    {
                        let _ = self.inspect_selected_core_receipt();
                    }
                    if let Some(notice) = self.core_report_notice {
                        ui.label(notice);
                    }
                    if let Some(receipt) = &self.core_report {
                        ui.monospace(format!("Core case: {:?}", receipt.case));
                        ui.monospace(format!("Source report SHA-256: {}", receipt.report_sha256));
                        ui.strong(format!("Core status: {}", receipt.status));
                        ui.strong(receipt.disclosure);
                        if self.external_core_source_visible {
                            ui.strong("One-shot external stdin synthetic Core report accepted (exact source hash). GUI does not authenticate its origin or freshness.");
                        }
                        ui.label("Not a live Python Core connection, full R4 validator, EHR import or patient workspace.");
                    }
                });
            // Only aggregate counts from a bounded, source-compiled, nonclinical
            // encrypted Workspace demo. Never any FHIR resource or secret.
            egui::CollapsingHeader::new("Encrypted Workspace proof — synthetic only (NO PHI)")
                .default_open(self.workspace_report_external)
                .show(ui, |ui| {
                    ui.strong("Ephemeral AES-GCM synthetic import and audit QA, NOT clinical storage");
                    if ui.button("Inspect compiled encrypted Workspace demo receipt").clicked() {
                        let _ = self.inspect_compiled_encrypted_demo();
                    }
                    if let Some(notice) = self.workspace_report_notice {
                        ui.label(notice);
                    }
                    if let Some(receipt) = &self.encrypted_workspace_receipt {
                        ui.monospace(format!("Workspace demo SHA-256: {}", receipt.report_sha256));
                        ui.strong("Encrypted synthetic import result: PASS (source-pinned QA)");
                        ui.label(format!("Fictional resources: {}", receipt.resource_count));
                        ui.label(format!("Fictional provenance records: {}", receipt.provenance_records));
                        ui.label(format!("Audit events: {}", receipt.audit_events));
                        ui.label(format!("Verified encrypted reopen: {}", receipt.verified_reopen));
                        ui.label(format!("Temporary encrypted store removed: {}", receipt.ephemeral_store_removed));
                        ui.strong(receipt.disclosure);
                        if self.workspace_report_external {
                            ui.label("One-shot external synthetic Workspace summary. Exact bytes only; source and freshness NOT authenticated by GUI.");
                        } else {
                            ui.label("Embedded source fixture: the GUI has NOT run an encrypted Workspace itself.");
                        }
                        if ui.button("Clear encrypted Workspace receipt").clicked() {
                            self.clear_fictional_output();
                        }
                    }
                });
            // Source-bound result of actual decrypted Core Workspace memory
            // readback, not the six separate D0 compiled navigation fixtures.
            egui::CollapsingHeader::new("Encrypted Core readback — three recovered fictional resources")
                .default_open(self.encrypted_readback_source_external)
                .show(ui, |ui| {
                    ui.strong("Fictional AES-GCM Core readback · NOT patient records or clinical validation");
                    ui.label("This native app does not launch Core or authenticate the source of stdin.");
                    let mut select = None;
                    let mut follow = None;
                    let mut incoming = None;
                    let mut breadcrumb_jump = None;
                    let mut chart_open = false;
                    let mut chart_member = None;
                    let mut mark_walkthrough = false;
                    let mut filter_change = None;
                    let mut search_change: Option<String> = None;
                    if let Some(readback) = &self.encrypted_readback {
                        ui.label(format!("Recovered fictional resource count: {}", readback.resources.len()));
                        ui.monospace(format!("Encrypted readback SHA-256: {}", readback.report_sha256));
                        ui.monospace(format!("Original source Bundle SHA-256: {}", readback.source_content_sha256));
                        ui.label(format!("Encrypted store reopened: {}", readback.encrypted_reopen_verified));
                        ui.label(format!("Audit chain verified: {}", readback.audit_chain_verified));
                        ui.label(format!("Ephemeral encrypted store removed: {}", readback.ephemeral_store_removed));
                        ui.label(format!("Persistent fictional QA vault reopened: {}", readback.persistent_test_vault_reopened));
                        ui.strong(readback.disclosure);
                        ui.horizontal_wrapped(|ui| {
                            ui.label("Recovered resource type (fixed fictional only):");
                            for facet in [
                                RecoveredResourceTypeFilter::All,
                                RecoveredResourceTypeFilter::Observation,
                                RecoveredResourceTypeFilter::Patient,
                                RecoveredResourceTypeFilter::Encounter,
                            ] {
                                if ui.button(format!("Filter recovered resource type: {}", facet.label())).clicked() {
                                    filter_change = Some(facet);
                                }
                            }
                        });
                        if ui.button("Open recovered fictional patient chart").clicked() {
                            chart_open = true;
                        }
                        ui.label("Patient-linked fictional chart: reviewed graph only, no dates, diagnosis or clinical timeline.");
                        ui.label(format!("Active recovered type: {}", self.encrypted_readback_filter.label()));
                        ui.horizontal_wrapped(|ui| {
                            ui.label("Search recovered fictional type/ID (ASCII only):");
                            let mut input = self.encrypted_readback_query.clone();
                            if ui.add(
                                egui::TextEdit::singleline(&mut input)
                                    .hint_text("fictional-patient-001")
                                    .desired_width(220.0),
                            ).changed() {
                                search_change = Some(input);
                            }
                            if ui.button("Search recovered source: Patient").clicked() {
                                search_change = Some("patient".to_owned());
                            }
                            if ui.button("Search recovered source: Encounter").clicked() {
                                search_change = Some("encounter".to_owned());
                            }
                            if ui.button("Clear recovered search").clicked() {
                                search_change = Some(String::new());
                            }
                        });
                        ui.label("In-memory search of three fictional source identities only. Never enter real patient information.");
                        ui.label(format!(
                            "Active recovered search: {}",
                            if self.encrypted_readback_query.is_empty() {
                                "All fictional IDs"
                            } else {
                                self.encrypted_readback_query.as_str()
                            }
                        ));
                        ui.label(format!(
                            "Recovered fictional worklist: {} of {} source-derived resources visible",
                            self.recovered_visible_count(), readback.resources.len()
                        ));
                        for (index, resource) in readback.resources.iter().enumerate() {
                            if self.recovered_search_matches(resource)
                                && ui.button(format!(
                                    "Open recovered fictional resource: {}/{}",
                                    resource.resource_type, resource.resource_id
                                )).clicked() {
                                select = Some(index);
                            }
                        }
                        if let Some(index) = self.encrypted_readback_selected
                            && let Some(resource) = readback.resources.get(index)
                        {
                                ui.strong(format!(
                                    "Recovered fictional record: {}/{}",
                                    resource.resource_type, resource.resource_id
                                ));
                                ui.monospace(format!("Recovered entry reference: {}", resource.full_url));
                                ui.label(format!(
                                    "Fictional walkthrough status: {}",
                                    if self.fictional_walkthrough_done[index] {
                                        "visited this session"
                                    } else {
                                        "not visited"
                                    }
                                ));
                                if !self.fictional_walkthrough_done[index]
                                    && ui.button("Mark fictional identity visited (demo only)").clicked()
                                {
                                    mark_walkthrough = true;
                                }
                                let incoming_count = readback.resources.iter()
                                    .flat_map(|source| source.links.iter())
                                    .filter(|edge| edge.target == resource.full_url)
                                    .count();
                                ui.strong("Recovered fictional relationship inspector");
                                ui.label(format!(
                                    "Verified fictional references: {} outgoing, {} incoming",
                                    resource.links.len(), incoming_count
                                ));
                                if !self.encrypted_readback_history.is_empty() {
                                    ui.label(format!(
                                        "Recovered fictional navigation trail: {} previous verified steps",
                                        self.encrypted_readback_history.len()
                                    ));
                                    for (step, previous_index) in
                                        self.encrypted_readback_history.iter().enumerate()
                                    {
                                        if let Some(previous) = readback.resources.get(*previous_index)
                                            && ui.button(format!(
                                                "Jump recovered history step {}: {}/{}",
                                                step + 1,
                                                previous.resource_type,
                                                previous.resource_id
                                            )).clicked()
                                        {
                                            breadcrumb_jump = Some(step);
                                        }
                                    }
                                }
                                if resource.resource_type == "Patient" {
                                    match verified_fictional_patient_chart(readback) {
                                        Ok(chart) if chart.patient == index => {
                                            ui.strong("Fictional patient chart: source-verified relationships");
                                            ui.label("Associated fictional resources: 1 Encounter, 1 Observation");
                                            ui.label("No clinical chronology, medications, diagnoses or outcomes are available.");
                                            for member in [chart.encounter, chart.observation] {
                                                let related = &readback.resources[member];
                                                if ui.button(format!(
                                                    "Open patient chart member: {}/{}",
                                                    related.resource_type, related.resource_id
                                                )).clicked() {
                                                    chart_member = Some(member);
                                                }
                                            }
                                        }
                                        _ => {
                                            ui.label("Fictional patient chart not available: source graph verification failed");
                                        }
                                    }
                                }
                                for (link_index, link) in resource.links.iter().enumerate() {
                                    if ui.button(format!(
                                        "Follow recovered fictional {} -> {}",
                                        link.field, link.target
                                    )).clicked() {
                                        follow = Some(link_index);
                                    }
                                }
                                // These reverse edges are computed from the
                                // actually decrypted fictional Core projection.
                                // No independent patient database is queried.
                                for (source_index, source) in readback.resources.iter().enumerate() {
                                    for (link_index, link) in source.links.iter().enumerate() {
                                        if link.target == resource.full_url
                                            && ui.button(format!(
                                                "Open recovered incoming {}/{} via {}",
                                                source.resource_type, source.resource_id, link.field
                                            )).clicked()
                                        {
                                            incoming = Some((source_index, link_index));
                                        }
                                    }
                                }
                        }
                    } else {
                        ui.label("No encrypted Core readback loaded. Explicit fictional-only startup receipt is required.");
                    }
                    if let Some(notice) = self.encrypted_readback_notice {
                        ui.label(notice);
                    }
                    if let Some(facet) = filter_change {
                        self.set_recovered_type_filter(facet);
                    }
                    if let Some(query) = search_change {
                        let _ = self.set_recovered_search_query(&query);
                    }
                    if let Some(index) = select {
                        let _ = self.select_encrypted_readback_resource(index);
                    }
                    if chart_open {
                        let _ = self.open_recovered_fictional_patient_chart();
                    }
                    if let Some(index) = chart_member {
                        let _ = self.open_recovered_fictional_patient_chart_member(index);
                    }
                    if mark_walkthrough {
                        let _ = self.mark_selected_fictional_walkthrough();
                    }
                    if let Some(index) = follow {
                        let _ = self.follow_encrypted_readback_link(index);
                    }
                    if let Some((source_index, link_index)) = incoming {
                        let _ = self.follow_encrypted_readback_incoming(source_index, link_index);
                    }
                    if let Some(step) = breadcrumb_jump {
                        let _ = self.jump_encrypted_readback_history(step);
                    }
                    if !self.encrypted_readback_history.is_empty()
                        && ui.button("Back to previous recovered fictional record").clicked()
                    {
                        let _ = self.back_encrypted_readback_resource();
                    }
                    if self.encrypted_readback.is_some()
                        && ui.button("Clear encrypted Core readback display").clicked()
                    {
                        self.clear_fictional_output();
                    }
                });
            // Actual native resource-type facets and approved relationship
            // navigation, limited to six source-compiled fictional controls.
            // No clinical records, free-text entry, import, persistence or network.
            egui::CollapsingHeader::new("Fictional Workspace — six source-verified cases (NO PHI)")
                .default_open(false)
                .show(ui, |ui| {
                    ui.strong("In-memory developer case explorer · not a clinical workspace");
                    ui.label("No patient import, login, EHR, persistence, clinical validation or real consent.");
                    if !self.fictional_workspace_unlocked {
                        if ui.button("Enter fictional workspace (synthetic only)").clicked() {
                            self.enter_fictional_workspace();
                        }
                    } else {
                        if ui.button("Close fictional workspace and clear details").clicked() {
                            self.close_fictional_workspace();
                        } else {
                            ui.horizontal_wrapped(|ui| {
                                ui.label("Status:");
                                for filter in [
                                    FictionalWorkspaceFilter::All,
                                    FictionalWorkspaceFilter::ExpectedEnvelopeOk,
                                    FictionalWorkspaceFilter::ExpectedNegative,
                                ] {
                                    if ui
                                        .selectable_label(
                                            self.fictional_workspace_filter == filter,
                                            filter.label(),
                                        )
                                        .clicked()
                                    {
                                        self.filter_fictional_workspace(filter);
                                    }
                                }
                            });
                            ui.horizontal_wrapped(|ui| {
                                ui.label("Resource type (fictional only):");
                                for filter in [
                                    FictionalResourceTypeFilter::All,
                                    FictionalResourceTypeFilter::Patient,
                                    FictionalResourceTypeFilter::Observation,
                                    FictionalResourceTypeFilter::Bundle,
                                ] {
                                    if ui
                                        .selectable_label(
                                            self.fictional_workspace_resource_type == filter,
                                            filter.label(),
                                        )
                                        .clicked()
                                    {
                                        self.filter_fictional_resource_type(filter);
                                    }
                                }
                            });
                            let visible_count = FICTIONAL_WORKSPACE_CASES
                                .iter()
                                .filter(|case| self.admits_fictional_case(**case))
                                .count();
                            ui.label(format!(
                                "Fictional worklist: {visible_count} of 6 fixed source cases visible"
                            ));
                            for (index, spec) in FICTIONAL_WORKSPACE_CASES.iter().enumerate() {
                                if !self.admits_fictional_case(*spec) {
                                    continue;
                                }
                                let fixture = FIXTURES[spec.fixture_index];
                                if ui
                                    .selectable_label(
                                        self.fictional_workspace_selected == Some(index),
                                        format!(
                                            "Open fictional case: {} [{}]",
                                            fixture.id,
                                            if spec.negative { "expected-negative" } else { "expected-positive" }
                                        ),
                                    )
                                    .clicked()
                                {
                                    let _ = self.open_fictional_workspace_case(index);
                                }
                            }
                            if let Some(notice) = self.fictional_workspace_notice {
                                ui.label(notice);
                            }
                            let mut follow_edge = None;
                            if let Some(detail) = &self.fictional_workspace_detail {
                                ui.separator();
                                ui.strong(format!("Fictional case: {}", detail.fixture.id));
                                ui.label(format!(
                                    "Source resource: {}/{}",
                                    detail.resource_type,
                                    detail.resource_id
                                ));
                                ui.monospace(format!("Source SHA-256: {}", detail.fixture.sha256));
                                ui.strong(format!(
                                    "Expected developer envelope status: {}",
                                    detail.fixture.status
                                ));
                                if detail.negative {
                                    ui.label("Expected-negative developer control: deliberately malformed reference.");
                                } else {
                                    ui.label("Expected-positive envelope test only: NOT FHIR R4 validation.");
                                }
                                ui.label("Source-bound fictional relationship pointers (no event dates):");
                                if detail.relations.is_empty() {
                                    ui.label("No approved relationship projection for this case.");
                                } else {
                                    for (edge_index, relation) in detail.relations.iter().enumerate() {
                                        ui.monospace(format!(
                                            "{} -> {} ({})",
                                            relation.source_pointer,
                                            relation.target,
                                            relation.relationship
                                        ));
                                        if ui
                                            .button(format!(
                                                "Follow fictional reference: {}",
                                                relation.target
                                            ))
                                            .clicked()
                                        {
                                            follow_edge = Some(edge_index);
                                        }
                                    }
                                }
                                ui.strong("Clinical data: PROHIBITED · FHIR R4: NOT VALIDATED");
                            }
                            if let Some(edge_index) = follow_edge {
                                let _ = self.follow_fictional_relation(edge_index);
                            }
                            if self.fictional_workspace_back.is_some()
                                && ui.button("Back to previous fictional case").clicked()
                            {
                                let _ = self.back_to_previous_fictional_case();
                            }
                        }
                    }
                });
            egui::CollapsingHeader::new("Additional fictional FHIR/Bundle cases (8)")
                .default_open(false)
                .show(ui, |ui| {
                    for (offset, fixture) in FIXTURES[PRIMARY_FIXTURE_COUNT..].iter().enumerate() {
                        let index = PRIMARY_FIXTURE_COUNT + offset;
                        if ui.selectable_label(self.selected == index, format!("{} ({} bytes)", fixture.id, fixture.bytes)).clicked() {
                            self.selected = index;
                            self.clear_fictional_output();
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
                            self.clear_fictional_output();
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
            ui.label("Browserless provenance: exact pinned fictional references (no date fields)");
            if ui
                .button("Inspect verified fictional relationships (read-only)")
                .clicked()
            {
                let _ = self.inspect_selected_relationships();
            }
            if let Some(notice) = self.relationship_notice {
                ui.label(notice);
            }
            if let Some(view) = &self.relationships {
                ui.strong("FICTIONAL RELATIONSHIPS VERIFIED - NOT FHIR OR CLINICAL VALIDATION");
                ui.monospace(format!(
                    "Source fixture: {} ({} bytes)",
                    view.source.id, view.source.bytes
                ));
                ui.monospace(format!("Source SHA-256: {}", view.source.sha256));
                ui.label("No recorded event dates in these source files; chronology unavailable.");
                for edge in &view.edges {
                    ui.monospace(format!(
                        "JSON pointer {} -> {} ({})",
                        edge.source_pointer, edge.target, edge.relationship
                    ));
                }
            }
            if ui.button("Clear fictional output (Escape)").clicked() {
                self.clear_fictional_output();
            }
            ui.label("Keyboard: Tab/Shift+Tab to navigate, Space to activate, Escape to clear synthetic output.");
            ui.separator();
            ui.separator();
            ui.label("FHIR structural checks only · Release: NO-GO · Network isolation: UNQUALIFIED · PHI: PROHIBITED");
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn protected_audit_result_opens_only_verified_readonly_status_and_clear() {
        use serde_json::json;
        let mut raw = serde_json::to_vec(&json!({
            "schema":"medorigin-core-windows-synthetic-protected-audit-preview/v1",
            "status":"FICTIONAL_WINDOWS_PROTECTED_AUDIT_PREVIEW_ONLY",
            "operation":"verify",
            "verified_audit_events":1,
            "audit_head_sha256":null,
            "anchor_matched":true,
            "protected_credential_destroyed":false,
            "encrypted_workspace_store_preserved":false,
            "patient_data_admitted":false,
            "fhir_r4_conformance_validated":false,
            "clinical_use_authorized":false,
            "production_key_provider_selected":false,
            "publication_authorized":false
        }))
        .unwrap();
        raw.push(b'\n');
        let mut app =
            MedOriginNativePreview::from_one_time_protected_audit_verification_stdin(&raw)
                .unwrap();
        assert_eq!(app.protected_audit_verified_events(), 1);
        assert_eq!(app.core_file_batch_import_count(), 0);
        assert_eq!(app.synthetic_bundle_resource_count(), 0);
        assert!(!app.has_external_synthetic_encrypted_readback());
        app.clear_fictional_output();
        assert_eq!(app.protected_audit_verified_events(), 0);
        raw.extend_from_slice(b" ");
        assert!(
            MedOriginNativePreview::from_one_time_protected_audit_verification_stdin(&raw)
                .is_err()
        );
    }

    const CORE_FILE_BATCH_REAL: &[u8] = include_bytes!(
        "../fixtures/core/core963-real-encrypted-fictional-file-batch-redacted.json"
    );

    #[test]
    fn source_run_core_file_batch_has_real_import_worklist_and_session_only_progress() {
        let mut app = MedOriginNativePreview::from_one_time_core_file_batch_receipt_stdin(
            CORE_FILE_BATCH_REAL,
        )
        .expect("exact actual encrypted source-run Core receipt");
        assert_eq!(app.core_file_batch_import_count(), 2);
        assert_eq!(app.core_file_batch_selected, None);
        assert_eq!(app.core_file_batch_inspected, [false, false]);
        assert_eq!(app.core_batch_step(true), Ok(()));
        assert_eq!(app.core_file_batch_selected, Some(0));
        assert_eq!(app.core_file_batch_inspected, [true, false]);
        assert_eq!(app.core_batch_next_uninspected(), Ok(()));
        assert_eq!(app.core_file_batch_selected, Some(1));
        assert_eq!(app.core_file_batch_inspected, [true, true]);
        assert_eq!(
            app.core_batch_next_uninspected(),
            Err("fictional_batch_no_uninspected_import")
        );
        assert!(app.core_file_batch.is_some());
        assert_eq!(
            app.core_batch_step(true),
            Err("fictional_batch_navigation_end")
        );
        assert_eq!(app.core_file_batch_selected, Some(1));
        assert_eq!(app.core_batch_step(false), Ok(()));
        assert_eq!(app.core_file_batch_selected, Some(0));
        assert_eq!(app.core_batch_reset_exploration(), Ok(()));
        assert_eq!(app.core_file_batch_selected, None);
        assert_eq!(app.core_file_batch_inspected, [false, false]);
        assert_eq!(app.core_file_batch.as_ref().unwrap().resource_count, 6);
        app.clear_fictional_output();
        assert_eq!(app.core_file_batch_import_count(), 0);
        assert_eq!(app.core_file_batch_selected, None);
        assert!(app.core_file_batch_inspected.is_empty());
        assert_eq!(
            app.core_batch_step(true),
            Err("fictional_batch_missing_source")
        );
    }

    #[test]
    fn official_r4_structural_gate_and_source_worklist_are_one_fail_closed_session() {
        // Construct only a canonical synthetic projection of the independently
        // source-run legacy receipt; the exact newer official-gate source run
        // is separately verified on the owner Windows host in real UIAutomation.
        let mut value: serde_json::Value = serde_json::from_slice(CORE_FILE_BATCH_REAL).unwrap();
        value["official_r4_structural_gate"] = serde_json::json!({
            "schema": "medorigin-core-fictional-file-official-r4-structural-gate/v1",
            "status": "OFFICIAL_R4_JSON_SCHEMA_STRUCTURE_ONLY_NOT_VALIDATED",
            "official_r4_archive_sha256":
                "75e5560da3cf503895a44c8ca7af17a83b4cca6c2cb5ba1883d2aec0d1cb5ac6",
            "source_count": 2,
            "structural_not_validated_count": 2,
            "structural_invalid_count": 0,
            "fhir_r4_conformance_validated": false,
            "terminology_profiles_invariants_verified": false,
            "clinical_use_authorized": false,
            "publication_authorized": false
        });
        let mut raw = serde_json::to_vec(&value).unwrap();
        raw.push(b'\n');
        let mut app =
            MedOriginNativePreview::from_one_time_core_file_batch_receipt_stdin(&raw).unwrap();
        assert!(
            app.core_file_batch
                .as_ref()
                .unwrap()
                .official_r4_structure_checked
        );
        assert_eq!(app.core_file_batch_selected, None);
        assert_eq!(app.core_batch_next_uninspected(), Ok(()));
        assert_eq!(app.core_file_batch_selected, Some(0));
        assert_eq!(app.core_batch_step(true), Ok(()));
        assert_eq!(app.core_file_batch_selected, Some(1));
        assert_eq!(app.core_file_batch_inspected, [true, true]);
        assert_eq!(app.core_batch_activity_filter(true), Ok(()));
        assert_eq!(app.core_batch_reset_exploration(), Ok(()));
        assert!(
            app.core_file_batch
                .as_ref()
                .unwrap()
                .official_r4_structure_checked
        );
        assert_eq!(app.core_file_batch_inspected, [false, false]);
        app.clear_fictional_output();
        assert_eq!(app.core_file_batch_import_count(), 0);
        assert!(app.core_file_batch_inspected.is_empty());

        for (field, bad) in [
            ("structural_invalid_count", serde_json::json!(1)),
            ("structural_not_validated_count", serde_json::json!(1)),
            ("source_count", serde_json::json!(3)),
            ("clinical_use_authorized", serde_json::json!(true)),
            ("fhir_r4_conformance_validated", serde_json::json!(true)),
        ] {
            let mut rejected = value.clone();
            rejected["official_r4_structural_gate"][field] = bad;
            let mut candidate = serde_json::to_vec(&rejected).unwrap();
            candidate.push(b'\n');
            assert!(
                MedOriginNativePreview::from_one_time_core_file_batch_receipt_stdin(&candidate)
                    .is_err(),
                "forged official gate: {field}"
            );
        }
    }

    #[test]
    fn core_file_batch_activity_only_filter_refuses_zero_activity_and_hidden_selection() {
        // Change only invented counts to simulate a patient-only second import.
        // The independently source-projected app never receives patient fields.
        let mut value: serde_json::Value = serde_json::from_slice(CORE_FILE_BATCH_REAL).unwrap();
        value["imports"][1]["verified_timeline_event_count"] = serde_json::json!(0);
        value["verified_timeline_event_count"] = serde_json::json!(2);
        let mut bytes = serde_json::to_vec(&value).unwrap();
        bytes.push(b'\n');
        let mut app =
            MedOriginNativePreview::from_one_time_core_file_batch_receipt_stdin(&bytes).unwrap();
        assert_eq!(app.core_batch_select(1), Ok(()));
        assert_eq!(app.core_file_batch_selected, Some(1));
        assert_eq!(app.core_batch_activity_filter(true), Ok(()));
        assert_eq!(app.core_file_batch_selected, None);
        assert!(app.core_batch_visible(0));
        assert!(!app.core_batch_visible(1));
        assert_eq!(
            app.core_batch_select(1),
            Err("fictional_batch_hidden_source_refused")
        );
        assert_eq!(app.core_file_batch_selected, None);
        assert_eq!(app.core_batch_next_uninspected(), Ok(()));
        assert_eq!(app.core_file_batch_selected, Some(0));
        assert_eq!(
            app.core_batch_step(true),
            Err("fictional_batch_navigation_end")
        );
        assert!(app.core_file_batch.is_some());
        assert_eq!(app.core_batch_activity_filter(false), Ok(()));
        assert!(app.core_batch_visible(1));
        assert_eq!(app.core_batch_step(true), Ok(()));
        assert_eq!(app.core_file_batch_selected, Some(1));
    }

    #[test]
    fn core_file_batch_stale_index_and_corrupted_session_bookkeeping_fail_closed() {
        let mut app = MedOriginNativePreview::from_one_time_core_file_batch_receipt_stdin(
            CORE_FILE_BATCH_REAL,
        )
        .unwrap();
        assert_eq!(
            app.core_batch_select(usize::MAX),
            Err("fictional_batch_stale_source_index_or_progress_refused")
        );
        assert!(app.core_file_batch.is_none());
        assert!(app.core_file_batch_inspected.is_empty());
        let mut app = MedOriginNativePreview::from_one_time_core_file_batch_receipt_stdin(
            CORE_FILE_BATCH_REAL,
        )
        .unwrap();
        app.core_file_batch_inspected.pop();
        assert_eq!(
            app.core_batch_next_uninspected(),
            Err("fictional_batch_stale_progress_refused")
        );
        assert!(app.core_file_batch.is_none());
        let mut app = MedOriginNativePreview::from_one_time_core_file_batch_receipt_stdin(
            CORE_FILE_BATCH_REAL,
        )
        .unwrap();
        app.core_file_batch_selected = Some(usize::MAX);
        assert_eq!(
            app.core_batch_step(true),
            Err("fictional_batch_selected_import_hidden_or_stale")
        );
        assert_eq!(app.core_file_batch_selected, None);
        assert!(app.core_file_batch.is_some());
        app.hash_selected().unwrap();
        assert!(
            app.core_file_batch.is_none(),
            "switching to other fixture must clear batch"
        );
    }

    #[test]
    fn core_file_batch_four_source_capacity_navigates_without_cross_source_identity() {
        // Synthetic in-test extension of the real redacted receipt; never
        // authenticates a Core run, patient identity or clinical review.
        let mut value: serde_json::Value = serde_json::from_slice(CORE_FILE_BATCH_REAL).unwrap();
        for i in 2..4usize {
            let mut source = value["imports"][0].clone();
            source["import_ordinal"] = serde_json::json!(i + 1);
            source["source_content_sha256"] = serde_json::json!(format!("{:064x}", 1024 + i));
            source["import_audit_event_digest"] = serde_json::json!(format!("{:064x}", 2048 + i));
            value["imports"].as_array_mut().unwrap().push(source);
        }
        value["import_count"] = serde_json::json!(4);
        value["resource_count"] = serde_json::json!(12);
        value["verified_timeline_event_count"] = serde_json::json!(8);
        value["verified_audit_events"] = serde_json::json!(4);
        value["current_audit_head_digest"] =
            value["imports"][3]["import_audit_event_digest"].clone();
        let mut bytes = serde_json::to_vec(&value).unwrap();
        bytes.push(b'\n');
        let mut app =
            MedOriginNativePreview::from_one_time_core_file_batch_receipt_stdin(&bytes).unwrap();
        assert_eq!(app.core_file_batch_import_count(), 4);
        for index in 0..4 {
            assert_eq!(app.core_batch_next_uninspected(), Ok(()));
            assert_eq!(app.core_file_batch_selected, Some(index));
            assert!(app.core_file_batch_inspected[index]);
            assert_eq!(
                app.core_file_batch.as_ref().unwrap().imports[index].ordinal,
                index + 1
            );
        }
        assert_eq!(app.core_file_batch_inspected, [true; 4]);
        assert_eq!(
            app.core_batch_step(true),
            Err("fictional_batch_navigation_end")
        );
        assert_eq!(app.core_batch_step(false), Ok(()));
        assert_eq!(app.core_file_batch_selected, Some(2));
        assert_eq!(app.core_batch_reset_exploration(), Ok(()));
        assert_eq!(app.core_file_batch_inspected, [false; 4]);
    }

    #[test]
    fn bounded_multi_patient_navigation_refuses_step_twenty_five_and_clears_source() {
        let raw = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        for _ in 0..12 {
            app.bundle_follow_incoming(1, 0).unwrap();
            app.bundle_follow_outgoing(0).unwrap();
        }
        assert_eq!(app.synthetic_bundle_history.len(), 24);
        assert_eq!(
            app.bundle_follow_incoming(1, 0),
            Err("synthetic_bundle_history_or_destination_refused")
        );
        assert!(app.synthetic_bundle.is_none());
        assert!(app.synthetic_bundle_history.is_empty());
    }

    #[test]
    fn fictional_group_shortcuts_are_bounded_and_cannot_switch_to_unknown_patient() {
        let raw = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        assert_eq!(
            app.bundle_step_patient_group(false),
            Err("synthetic_bundle_patient_group_boundary")
        );
        assert_eq!(app.synthetic_bundle_patient, Some(0));
        app.bundle_step_patient_group(true).unwrap();
        assert_eq!(app.synthetic_bundle_patient, Some(4));
        assert_eq!(app.synthetic_bundle_selected, None);
        assert_eq!(
            app.bundle_step_patient_group(true),
            Err("synthetic_bundle_patient_group_boundary")
        );
        assert!(app.synthetic_bundle.is_some());
        app.bundle_set_patient(None).unwrap();
        app.bundle_step_patient_group(false).unwrap();
        assert_eq!(app.synthetic_bundle_patient, Some(4));
        app.bundle_step_patient_group(false).unwrap();
        assert_eq!(app.synthetic_bundle_patient, Some(0));
        app.bundle_set_patient(None).unwrap();
        app.bundle_step_patient_group(true).unwrap();
        assert_eq!(app.synthetic_bundle_patient, Some(0));
        app.synthetic_bundle_patient = Some(usize::MAX);
        assert_eq!(
            app.bundle_step_patient_group(true),
            Err("synthetic_bundle_unknown_current_group")
        );
        assert!(app.synthetic_bundle.is_none());
    }

    #[test]
    fn all_sixteen_fictional_patient_groups_are_navigable_at_capacity() {
        let mut entries = Vec::new();
        let urn = |i: usize| format!("urn:uuid:00000000-0000-4000-8000-{i:012}");
        for patient in 1..=16 {
            let patient_url = urn(patient);
            let encounter_url = urn(patient + 16);
            entries.push(serde_json::json!({
                "fullUrl": patient_url,
                "resource": {"id":format!("fictional-patient-{patient:03}"),"resourceType":"Patient"}
            }));
            entries.push(serde_json::json!({
                "fullUrl": encounter_url,
                "resource":{"id":format!("fictional-encounter-{patient:03}"),"resourceType":"Encounter",
                    "subject":{"reference":patient_url}}
            }));
            entries.push(serde_json::json!({
                "fullUrl":urn(patient+32),
                "resource":{"id":format!("fictional-observation-{patient:03}"),"resourceType":"Observation",
                    "subject":{"reference":patient_url},"encounter":{"reference":encounter_url}}
            }));
        }
        let raw = serde_json::to_vec(&serde_json::json!({
            "entry":entries,
            "meta":{"tag":[{"code":"fictional-structural-demo-no-phi",
                "system":"https://medorigin.si/synthetic-only"}]},
            "resourceType":"Bundle",
            "type":"collection"
        }))
        .unwrap();
        assert_eq!(
            raw,
            include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle-48.json").to_vec()
        );
        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(&raw).unwrap();
        assert_eq!(app.synthetic_bundle_resource_count(), 48);
        assert_eq!(app.synthetic_bundle_visited.len(), 48);
        assert_eq!(app.synthetic_bundle_patient, Some(0));
        for patient in 2..=16 {
            app.bundle_step_patient_group(true).unwrap();
            assert_eq!(app.synthetic_bundle_patient, Some((patient - 1) * 3));
        }
        assert_eq!(
            app.bundle_step_patient_group(true),
            Err("synthetic_bundle_patient_group_boundary")
        );
        assert!(app.synthetic_bundle.is_some());
        app.bundle_set_type("Observation").unwrap();
        app.bundle_open_next_unexplored().unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(47));
        assert_eq!(
            app.synthetic_bundle_visited.iter().filter(|b| **b).count(),
            2
        );
        app.bundle_set_patient(None).unwrap();
        assert_eq!(app.synthetic_bundle_patient, None);
        app.bundle_step_patient_group(false).unwrap();
        assert_eq!(app.synthetic_bundle_patient, Some(45));
        app.bundle_step_patient_group(false).unwrap();
        assert_eq!(app.synthetic_bundle_patient, Some(42));
        app.clear_fictional_output();
        assert!(app.synthetic_bundle_visited.is_empty());
    }

    #[test]
    fn fictional_exploration_tracks_only_opened_visible_records_and_resets_in_session() {
        let raw = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        assert_eq!(app.synthetic_bundle_visited.len(), 8);
        assert_eq!(
            app.synthetic_bundle_visited
                .iter()
                .filter(|opened| **opened)
                .count(),
            1
        );
        assert!(app.synthetic_bundle_visited[0]);
        app.bundle_open_next_unexplored().unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(1));
        app.bundle_open_next_unexplored().unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(2));
        app.bundle_follow_outgoing(1).unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(1));
        assert_eq!(app.synthetic_bundle_history.len(), 1);
        assert_eq!(
            app.synthetic_bundle_visited
                .iter()
                .filter(|opened| **opened)
                .count(),
            3
        );
        app.bundle_set_patient(Some(4)).unwrap();
        app.bundle_set_type("Observation").unwrap();
        assert_eq!(app.synthetic_bundle_selected, None);
        app.bundle_open_next_unexplored().unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(6));
        app.bundle_open_next_unexplored().unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(7));
        assert_eq!(
            app.bundle_open_next_unexplored(),
            Err("synthetic_bundle_no_unexplored_visible_records")
        );
        assert_eq!(app.synthetic_bundle_selected, Some(7));
        assert!(!app.synthetic_bundle_visited[4]);
        assert!(!app.synthetic_bundle_visited[5]);
        app.bundle_reset_exploration().unwrap();
        assert_eq!(app.synthetic_bundle_selected, None);
        assert!(app.synthetic_bundle_history.is_empty());
        assert!(
            app.synthetic_bundle_visited
                .iter()
                .all(|was_opened| !was_opened)
        );
        assert!(!app.bundle_visible(2));
        app.bundle_open_next_unexplored().unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(6));
        app.bundle_set_patient(None).unwrap();
        assert!(app.synthetic_bundle_visited[6]);
        app.clear_fictional_output();
        assert!(app.synthetic_bundle_visited.is_empty());
        assert!(app.synthetic_bundle.is_none());
    }

    #[test]
    fn fictional_exploration_refuses_mutated_progress_array_without_leaking_source() {
        let raw = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        app.synthetic_bundle_visited.pop();
        assert_eq!(
            app.bundle_open_next_unexplored(),
            Err("synthetic_bundle_exploration_state_refused")
        );
        assert!(app.synthetic_bundle.is_none());
        assert!(app.synthetic_bundle_visited.is_empty());
        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        app.synthetic_bundle_visited.pop();
        assert_eq!(
            app.bundle_select(1),
            Err("synthetic_bundle_exploration_state_refused")
        );
        assert!(app.synthetic_bundle.is_none());
    }

    #[test]
    fn no_arg_native_home_opens_compiled_dummy_bundle_only_after_explicit_action() {
        let mut app = MedOriginNativePreview::default();
        assert_eq!(app.synthetic_bundle_resource_count(), 0);
        assert!(app.encrypted_readback.is_none());
        app.open_embedded_fictional_bundle_demo().unwrap();
        assert_eq!(app.synthetic_bundle_resource_count(), 8);
        assert_eq!(app.synthetic_bundle_selected, Some(0));
        assert_eq!(app.synthetic_bundle_patient, Some(0));
        assert!(!app.has_external_synthetic_encrypted_readback());
        app.bundle_step_visible(true).unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(1));
        app.clear_fictional_output();
        assert_eq!(app.synthetic_bundle_resource_count(), 0);
        assert!(app.synthetic_bundle_history.is_empty());
    }

    #[test]
    fn visible_worklist_step_stays_inside_patient_and_type_and_refuses_stale_selection() {
        let raw = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(0));
        assert_eq!(
            app.bundle_step_visible(false),
            Err("synthetic_bundle_worklist_boundary")
        );
        assert_eq!(app.synthetic_bundle_selected, Some(0));
        app.bundle_step_visible(true).unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(1));
        assert!(app.synthetic_bundle_history.is_empty());

        app.bundle_set_patient(Some(4)).unwrap();
        app.bundle_set_type("Observation").unwrap();
        app.bundle_step_visible(true).unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(6));
        app.bundle_step_visible(true).unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(7));
        assert_eq!(
            app.bundle_step_visible(true),
            Err("synthetic_bundle_worklist_boundary")
        );
        assert_eq!(app.synthetic_bundle_selected, Some(7));
        app.bundle_step_visible(false).unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(6));
        assert!(app.synthetic_bundle_history.is_empty());
        assert!(!app.bundle_visible(2));

        // Simulated stale index from another patient cannot be walked into,
        // and invalid state is cleared rather than retaining any record.
        app.synthetic_bundle_selected = Some(2);
        assert_eq!(
            app.bundle_step_visible(true),
            Err("synthetic_bundle_stale_worklist_selection")
        );
        assert!(app.synthetic_bundle.is_none());
        assert!(app.synthetic_bundle_history.is_empty());
    }

    #[test]
    fn bounded_fictional_multi_patient_bundle_is_a_distinct_ui_mode() {
        let raw = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        assert_eq!(app.synthetic_bundle_resource_count(), 8);
        assert_eq!(app.synthetic_bundle_patient, Some(0));
        assert_eq!(app.synthetic_bundle_selected, Some(0));
        assert!(app.synthetic_bundle.is_some());
        assert!(!app.has_external_synthetic_encrypted_readback());

        app.bundle_follow_incoming(1, 0).unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(1));
        assert_eq!(app.synthetic_bundle_history, vec![0]);
        app.bundle_follow_outgoing(0).unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(0));
        app.bundle_back().unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(1));
        app.bundle_back().unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(0));
        assert!(app.synthetic_bundle_history.is_empty());

        app.bundle_set_patient(Some(4)).unwrap();
        assert_eq!(app.synthetic_bundle_patient, Some(4));
        assert_eq!(app.synthetic_bundle_selected, None);
        app.bundle_set_type("Observation").unwrap();
        assert!(!app.bundle_visible(2));
        assert!(app.bundle_visible(6));
        assert!(app.bundle_visible(7));
        app.bundle_select(6).unwrap();
        app.bundle_follow_outgoing(1).unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(5));
        assert_eq!(app.synthetic_bundle_patient, Some(4));
        app.bundle_back().unwrap();
        assert_eq!(app.synthetic_bundle_selected, Some(6));
        app.bundle_set_patient(None).unwrap();
        app.bundle_set_type("All").unwrap();
        assert!((0..8).all(|index| app.bundle_visible(index)));
        app.clear_fictional_output();
        assert_eq!(app.synthetic_bundle_resource_count(), 0);
        assert!(app.synthetic_bundle_history.is_empty());
    }

    #[test]
    fn bounded_fictional_bundle_refuses_hidden_groups_stale_links_and_invalid_history() {
        let raw = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        assert_eq!(
            app.bundle_select(7),
            Err("synthetic_bundle_hidden_or_unknown_selection")
        );
        assert_eq!(app.synthetic_bundle_resource_count(), 0);

        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        assert_eq!(
            app.bundle_set_patient(Some(2)),
            Err("synthetic_bundle_patient_group_refused")
        );
        assert_eq!(app.synthetic_bundle_resource_count(), 0);

        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        assert_eq!(
            app.bundle_set_type("MedicationRequest"),
            Err("synthetic_bundle_unknown_facet")
        );
        assert_eq!(app.synthetic_bundle_resource_count(), 0);

        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        assert_eq!(
            app.bundle_follow_incoming(5, 0),
            Err("synthetic_bundle_incoming_reference_refused")
        );
        assert_eq!(app.synthetic_bundle_resource_count(), 0);

        let mut app = MedOriginNativePreview::from_one_time_synthetic_bundle_stdin(raw).unwrap();
        assert_eq!(app.bundle_back(), Err("synthetic_bundle_no_history"));
        assert_eq!(app.synthetic_bundle_resource_count(), 8);
        app.synthetic_bundle_history.push(usize::MAX);
        assert_eq!(
            app.bundle_back(),
            Err("synthetic_bundle_stale_history_refused")
        );
        assert_eq!(app.synthetic_bundle_resource_count(), 0);
    }

    #[test]
    fn focused_relationship_navigation_reuses_source_links_and_bounded_breadcrumbs() {
        for raw in [
            include_bytes!("../fixtures/core/encrypted-readback-projection.json").as_slice(),
            include_bytes!("../fixtures/core/encrypted-persistent-readback-projection.json")
                .as_slice(),
        ] {
            let mut app =
                MedOriginNativePreview::from_one_time_synthetic_focused_readback_stdin(raw)
                    .unwrap();
            app.open_recovered_fictional_patient_chart().unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(1));
            app.follow_encrypted_readback_incoming(2, 0).unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(2)); // Encounter.subject
            assert_eq!(app.encrypted_readback_history, vec![1]);
            app.follow_encrypted_readback_link(0).unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(1)); // Patient
            assert_eq!(app.encrypted_readback_history, vec![1, 2]);
            app.jump_encrypted_readback_history(1).unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(2));
            assert_eq!(app.encrypted_readback_history, vec![1]);
            app.back_encrypted_readback_resource().unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(1));
            assert!(app.encrypted_readback_history.is_empty());
            app.follow_encrypted_readback_incoming(0, 0).unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(0)); // Observation.subject
            app.follow_encrypted_readback_link(1).unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(2)); // Observation.encounter
            assert_eq!(app.encrypted_readback_history, vec![1, 0]);
            app.jump_encrypted_readback_history(0).unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(1));
            assert!(app.encrypted_readback_history.is_empty());
            assert_eq!(app.recovered_visible_count(), 3);
            assert!(app.focused_workspace_visible);
            assert!(app.has_external_synthetic_encrypted_readback());
        }
    }

    #[test]
    fn focused_relationship_rejects_mutated_source_and_breadcrumb_reuse_after_filter() {
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_focused_readback_stdin(raw).unwrap();
        app.open_recovered_fictional_patient_chart().unwrap();
        app.follow_encrypted_readback_incoming(2, 0).unwrap();
        app.set_recovered_type_filter(RecoveredResourceTypeFilter::Patient);
        assert!(app.encrypted_readback_history.is_empty());
        assert!(app.encrypted_readback_selected.is_none());
        assert_eq!(
            app.jump_encrypted_readback_history(0),
            Err("encrypted_readback_breadcrumb_refused")
        );
        assert!(app.encrypted_readback.is_none());
        assert!(!app.focused_workspace_visible);

        let mut forged =
            MedOriginNativePreview::from_one_time_synthetic_focused_readback_stdin(raw).unwrap();
        forged.open_recovered_fictional_patient_chart().unwrap();
        // Reverse-edge mismatch cannot navigate to an unrelated source identity.
        assert_eq!(
            forged.follow_encrypted_readback_incoming(0, 1),
            Err("encrypted_readback_incoming_edge_mismatch")
        );
        assert!(!forged.focused_workspace_visible);
        assert!(forged.encrypted_readback.is_none());
    }

    #[test]
    fn direct_focused_startup_admits_only_two_independent_source_reviewed_fictional_projections() {
        for raw in [
            include_bytes!("../fixtures/core/encrypted-readback-projection.json").as_slice(),
            include_bytes!("../fixtures/core/encrypted-persistent-readback-projection.json")
                .as_slice(),
        ] {
            let mut app =
                MedOriginNativePreview::from_one_time_synthetic_focused_readback_stdin(raw)
                    .unwrap();
            assert!(app.focused_fictional_workspace_is_visible());
            assert!(app.has_external_synthetic_encrypted_readback());
            assert_eq!(app.recovered_visible_count(), 3);
            app.open_recovered_fictional_patient_chart().unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(1));
            app.clear_fictional_output();
            assert!(!app.focused_fictional_workspace_is_visible());
            assert!(!app.has_external_synthetic_encrypted_readback());
        }
        for bad in [
            b"{}".to_vec(),
            [
                include_bytes!("../fixtures/core/encrypted-readback-projection.json").as_slice(),
                b" ",
            ]
            .concat(),
        ] {
            assert!(
                MedOriginNativePreview::from_one_time_synthetic_focused_readback_stdin(&bad)
                    .is_err()
            );
        }
    }

    #[test]
    fn focused_browser_filters_source_verified_resources_and_refuses_hidden_selection() {
        for raw in [
            include_bytes!("../fixtures/core/encrypted-readback-projection.json").as_slice(),
            include_bytes!("../fixtures/core/encrypted-persistent-readback-projection.json")
                .as_slice(),
        ] {
            let mut app =
                MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw)
                    .unwrap();
            app.set_focused_fictional_workspace(true).unwrap();
            assert_eq!(app.recovered_visible_count(), 3);
            app.set_recovered_type_filter(RecoveredResourceTypeFilter::Patient);
            assert_eq!(app.recovered_visible_count(), 1);
            app.set_recovered_search_query("encounter").unwrap();
            assert_eq!(app.recovered_visible_count(), 0);
            assert_eq!(app.encrypted_readback_selected, None);
            assert!(app.encrypted_readback.is_some());
            app.set_recovered_type_filter(RecoveredResourceTypeFilter::Encounter);
            assert_eq!(app.recovered_visible_count(), 1);
            let chart =
                verified_fictional_patient_chart(app.encrypted_readback.as_ref().unwrap()).unwrap();
            app.select_encrypted_readback_resource(chart.encounter)
                .unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(chart.encounter));
            app.set_recovered_search_query("patient").unwrap();
            assert_eq!(app.recovered_visible_count(), 0);
            assert_eq!(app.encrypted_readback_selected, None);
            app.set_recovered_type_filter(RecoveredResourceTypeFilter::All);
            assert_eq!(app.recovered_visible_count(), 1);
            app.select_encrypted_readback_resource(chart.patient)
                .unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(chart.patient));
            app.set_recovered_search_query("").unwrap();
            assert_eq!(app.recovered_visible_count(), 3);
            app.set_focused_fictional_workspace(false).unwrap();
            assert!(app.encrypted_readback.is_some());
            app.set_focused_fictional_workspace(true).unwrap();
            assert_eq!(app.recovered_visible_count(), 3);
            assert_eq!(app.encrypted_readback_selected, None);
        }
    }

    #[test]
    fn focused_browser_source_type_and_search_guards_fail_closed_for_hidden_and_invalid_data() {
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.set_focused_fictional_workspace(true).unwrap();
        app.set_recovered_type_filter(RecoveredResourceTypeFilter::Patient);
        let chart =
            verified_fictional_patient_chart(app.encrypted_readback.as_ref().unwrap()).unwrap();
        assert_eq!(
            app.select_encrypted_readback_resource(chart.observation),
            Err("encrypted_readback_filtered_resource_refused")
        );
        assert!(!app.focused_workspace_visible);
        assert!(app.encrypted_readback.is_none());

        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.set_focused_fictional_workspace(true).unwrap();
        assert_eq!(
            app.set_recovered_search_query("real patient@example.com"),
            Err("fictional_search_unreviewed_characters_or_length")
        );
        assert!(!app.focused_workspace_visible);
        assert!(app.encrypted_readback.is_none());
        assert_eq!(app.recovered_visible_count(), 0);
    }

    #[test]
    fn focused_workspace_switch_preserves_verified_source_and_never_promotes_clinical_use() {
        for raw in [
            include_bytes!("../fixtures/core/encrypted-readback-projection.json").as_slice(),
            include_bytes!("../fixtures/core/encrypted-persistent-readback-projection.json")
                .as_slice(),
        ] {
            let mut app =
                MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw)
                    .unwrap();
            assert!(!app.focused_workspace_visible);
            app.set_focused_fictional_workspace(true).unwrap();
            assert!(app.focused_workspace_visible);
            assert!(
                app.encrypted_readback
                    .as_ref()
                    .unwrap()
                    .audit_chain_verified
            );
            app.open_recovered_fictional_patient_chart().unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(1));
            let chart =
                verified_fictional_patient_chart(app.encrypted_readback.as_ref().unwrap()).unwrap();
            app.open_recovered_fictional_patient_chart_member(chart.encounter)
                .unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(chart.encounter));
            app.back_encrypted_readback_resource().unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(chart.patient));
            app.set_focused_fictional_workspace(false).unwrap();
            assert!(!app.focused_workspace_visible);
            assert!(app.encrypted_readback.is_some());
            app.set_focused_fictional_workspace(true).unwrap();
            app.clear_fictional_output();
            assert!(!app.focused_workspace_visible);
            assert!(app.encrypted_readback.is_none());
            assert_eq!(app.fictional_walkthrough_done, [false; 3]);
        }
    }

    #[test]
    fn focused_workspace_refuses_no_source_or_mutated_fictional_graph() {
        let mut empty = MedOriginNativePreview::default();
        assert_eq!(
            empty.set_focused_fictional_workspace(true),
            Err("focused_workspace_no_verified_source")
        );
        assert!(!empty.focused_workspace_visible);
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut forged =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        forged.encrypted_readback.as_mut().unwrap().resources[0].links[1].target =
            "urn:uuid:00000000-0000-4000-8000-000000000002".to_owned();
        assert_eq!(
            forged.set_focused_fictional_workspace(true),
            Err("fictional_patient_chart_unverified_relationship_refused")
        );
        assert!(!forged.focused_workspace_visible);
        assert!(forged.encrypted_readback.is_none());
    }

    #[test]
    fn fictional_session_walkthrough_visits_three_actual_core_identities_once() {
        for raw in [
            include_bytes!("../fixtures/core/encrypted-readback-projection.json").as_slice(),
            include_bytes!("../fixtures/core/encrypted-persistent-readback-projection.json")
                .as_slice(),
        ] {
            let mut app =
                MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw)
                    .unwrap();
            assert_eq!(app.fictional_walkthrough_done, [false; 3]);
            app.next_unvisited_fictional_resource().unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(1)); // fictional Patient
            app.mark_selected_fictional_walkthrough().unwrap();
            assert_eq!(app.fictional_walkthrough_done, [false, true, false]);
            app.set_recovered_search_query("encounter").unwrap();
            assert_eq!(app.fictional_walkthrough_done, [false, true, false]);
            app.next_unvisited_fictional_resource().unwrap();
            assert!(app.encrypted_readback_query.is_empty());
            assert_eq!(app.encrypted_readback_selected, Some(2)); // fictional Encounter
            app.mark_selected_fictional_walkthrough().unwrap();
            app.next_unvisited_fictional_resource().unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(0)); // fictional Observation
            app.mark_selected_fictional_walkthrough().unwrap();
            assert_eq!(app.fictional_walkthrough_done, [true; 3]);
            assert_eq!(
                app.next_unvisited_fictional_resource(),
                Err("fictional_walkthrough_all_visited")
            );
            assert_eq!(app.encrypted_readback_selected, Some(0));
            assert!(app.encrypted_readback_history.is_empty());
            assert!(app.encrypted_readback.is_some());
            assert_eq!(
                app.encrypted_readback_notice,
                Some("All three fictional walkthrough steps complete (session only)")
            );
            app.reset_fictional_walkthrough().unwrap();
            assert_eq!(app.fictional_walkthrough_done, [false; 3]);
            assert!(app.encrypted_readback_notice.is_none());
            app.next_unvisited_fictional_resource().unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(1));
            app.clear_fictional_output();
            assert_eq!(app.fictional_walkthrough_done, [false; 3]);
            assert!(app.encrypted_readback.is_none());
        }
    }

    #[test]
    fn fictional_walkthrough_rejects_unverified_graph_stale_index_and_no_selection() {
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        assert_eq!(
            app.mark_selected_fictional_walkthrough(),
            Err("fictional_walkthrough_no_selection")
        );
        assert!(app.encrypted_readback.is_none());
        assert_eq!(app.fictional_walkthrough_done, [false; 3]);
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.encrypted_readback_selected = Some(usize::MAX);
        assert_eq!(
            app.next_unvisited_fictional_resource(),
            Err("fictional_walkthrough_stale_selection")
        );
        assert!(app.encrypted_readback.is_none());
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.open_recovered_fictional_patient_chart().unwrap();
        app.mark_selected_fictional_walkthrough().unwrap();
        app.encrypted_readback.as_mut().unwrap().resources[0].links[1].target =
            "urn:uuid:00000000-0000-4000-8000-000000000002".to_owned();
        assert_eq!(
            app.next_unvisited_fictional_resource(),
            Err("fictional_patient_chart_unverified_relationship_refused")
        );
        assert!(app.encrypted_readback.is_none());
        assert_eq!(app.fictional_walkthrough_done, [false; 3]);
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.open_recovered_fictional_patient_chart().unwrap();
        app.mark_selected_fictional_walkthrough().unwrap();
        app.hash_selected().unwrap();
        assert!(app.encrypted_readback.is_none());
        assert_eq!(app.fictional_walkthrough_done, [false; 3]);
    }

    #[test]
    fn fictional_patient_chart_reconciles_source_verified_encounter_observation_and_back() {
        for raw in [
            include_bytes!("../fixtures/core/encrypted-readback-projection.json").as_slice(),
            include_bytes!("../fixtures/core/encrypted-persistent-readback-projection.json")
                .as_slice(),
        ] {
            let mut app =
                MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw)
                    .unwrap();
            let chart = verified_fictional_patient_chart(app.encrypted_readback.as_ref().unwrap())
                .expect("actual decrypted fictional Core graph");
            assert_eq!(
                chart,
                FictionalPatientChart {
                    observation: 0,
                    patient: 1,
                    encounter: 2,
                }
            );
            app.set_recovered_type_filter(RecoveredResourceTypeFilter::Observation);
            app.set_recovered_search_query("observation").unwrap();
            assert_eq!(app.recovered_visible_count(), 1);
            app.open_recovered_fictional_patient_chart().unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(chart.patient));
            assert_eq!(
                app.encrypted_readback_filter,
                RecoveredResourceTypeFilter::All
            );
            assert!(app.encrypted_readback_query.is_empty());
            assert!(app.encrypted_readback_history.is_empty());
            app.open_recovered_fictional_patient_chart_member(chart.encounter)
                .unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(chart.encounter));
            assert_eq!(app.encrypted_readback_history, vec![chart.patient]);
            app.back_encrypted_readback_resource().unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(chart.patient));
            app.open_recovered_fictional_patient_chart_member(chart.observation)
                .unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(chart.observation));
            assert_eq!(app.encrypted_readback_history, vec![chart.patient]);
            app.back_encrypted_readback_resource().unwrap();
            assert_eq!(app.encrypted_readback_selected, Some(chart.patient));
            assert_eq!(
                app.open_recovered_fictional_patient_chart_member(chart.patient),
                Err("fictional_patient_chart_unapproved_member")
            );
            assert!(app.encrypted_readback.is_none());
            assert!(app.encrypted_readback_selected.is_none());
            assert!(app.encrypted_readback_history.is_empty());
        }
    }

    #[test]
    fn fictional_patient_chart_refuses_forged_relationships_and_missing_members() {
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.encrypted_readback.as_mut().unwrap().resources[0].links[1].target =
            "urn:uuid:00000000-0000-4000-8000-000000000002".to_owned();
        assert_eq!(
            app.open_recovered_fictional_patient_chart(),
            Err("fictional_patient_chart_unverified_relationship_refused")
        );
        assert!(app.encrypted_readback.is_none());

        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.encrypted_readback.as_mut().unwrap().resources[2].resource_type =
            "Observation".to_owned();
        assert_eq!(
            app.open_recovered_fictional_patient_chart(),
            Err("fictional_patient_chart_type_ambiguous")
        );
        assert!(app.encrypted_readback.is_none());

        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        assert_eq!(
            app.open_recovered_fictional_patient_chart_member(0),
            Err("fictional_patient_chart_no_selection")
        );
        assert!(app.encrypted_readback.is_none());
    }

    #[test]
    fn recovered_encrypted_core_resources_have_live_source_projected_navigation() {
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut app = MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw)
            .expect("only source-approved real encrypted fictional Core readback");
        assert!(app.has_external_synthetic_encrypted_readback());
        assert_eq!(app.encrypted_readback.as_ref().unwrap().resources.len(), 3);
        app.select_encrypted_readback_resource(0).unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(0));
        app.follow_encrypted_readback_link(0).unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(1)); // recovered Patient
        assert_eq!(app.encrypted_readback_history, vec![0]);
        app.back_encrypted_readback_resource().unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(0));
        assert!(app.encrypted_readback_history.is_empty());
        app.follow_encrypted_readback_link(1).unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(2)); // recovered Encounter
        app.follow_encrypted_readback_link(0).unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(1)); // recovered Patient
        assert_eq!(app.encrypted_readback_history, vec![0, 2]);
        app.back_encrypted_readback_resource().unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(2)); // multi-hop back to Encounter
        assert_eq!(app.encrypted_readback_history, vec![0]);
        app.back_encrypted_readback_resource().unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(0)); // then Observation
        assert!(app.encrypted_readback_history.is_empty());
    }

    #[test]
    fn recovered_fictional_inspector_breadcrumbs_jump_only_to_verified_ancestors() {
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.select_encrypted_readback_resource(0).unwrap(); // Observation
        app.follow_encrypted_readback_link(1).unwrap(); // Encounter
        app.follow_encrypted_readback_link(0).unwrap(); // Patient
        assert_eq!(app.encrypted_readback_history, vec![0, 2]);
        assert_eq!(app.encrypted_readback_selected, Some(1));
        app.jump_encrypted_readback_history(1).unwrap(); // Encounter
        assert_eq!(app.encrypted_readback_history, vec![0]);
        assert_eq!(app.encrypted_readback_selected, Some(2));
        app.jump_encrypted_readback_history(0).unwrap(); // Observation
        assert!(app.encrypted_readback_history.is_empty());
        assert_eq!(app.encrypted_readback_selected, Some(0));

        // An invented step is not a valid breadcrumb; fail closed.
        assert_eq!(
            app.jump_encrypted_readback_history(0),
            Err("encrypted_readback_breadcrumb_refused")
        );
        assert!(app.encrypted_readback.is_none());
        assert!(app.encrypted_readback_selected.is_none());
        assert!(app.encrypted_readback_history.is_empty());

        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.select_encrypted_readback_resource(0).unwrap();
        app.follow_encrypted_readback_link(0).unwrap();
        app.encrypted_readback_history.push(usize::MAX);
        assert_eq!(
            app.jump_encrypted_readback_history(0),
            Err("encrypted_readback_breadcrumb_refused")
        );
        assert!(app.encrypted_readback.is_none());
        assert!(app.encrypted_readback_history.is_empty());

        // Searching or filtering hides breadcrumbs and must never leave a
        // history shortcut attached to a different fictional selection.
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.select_encrypted_readback_resource(0).unwrap();
        app.follow_encrypted_readback_link(0).unwrap();
        app.set_recovered_search_query("patient").unwrap();
        assert!(app.encrypted_readback_selected.is_none());
        assert!(app.encrypted_readback_history.is_empty());
        app.select_encrypted_readback_resource(1).unwrap();
        app.set_recovered_type_filter(RecoveredResourceTypeFilter::Encounter);
        assert!(app.encrypted_readback_history.is_empty());
        assert!(app.encrypted_readback_selected.is_none());
    }

    #[test]
    fn incoming_core_relationships_navigate_only_verified_decrypted_edges() {
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.select_encrypted_readback_resource(1).unwrap(); // Patient
        app.follow_encrypted_readback_incoming(2, 0).unwrap(); // Encounter.subject
        assert_eq!(app.encrypted_readback_selected, Some(2));
        app.follow_encrypted_readback_incoming(0, 1).unwrap(); // Observation.encounter
        assert_eq!(app.encrypted_readback_selected, Some(0));
        assert_eq!(app.encrypted_readback_history, vec![1, 2]);
        app.back_encrypted_readback_resource().unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(2));
        app.back_encrypted_readback_resource().unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(1));
        assert!(app.encrypted_readback_history.is_empty());
    }

    #[test]
    fn decrypted_core_facet_counts_and_hidden_selection_fail_closed() {
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        assert_eq!(app.recovered_visible_count(), 3);
        for (facet, expected) in [
            (RecoveredResourceTypeFilter::Patient, 1),
            (RecoveredResourceTypeFilter::Encounter, 1),
            (RecoveredResourceTypeFilter::Observation, 1),
            (RecoveredResourceTypeFilter::All, 3),
        ] {
            app.set_recovered_type_filter(facet);
            assert_eq!(app.recovered_visible_count(), expected);
            assert!(app.encrypted_readback_selected.is_none());
            assert!(app.encrypted_readback_history.is_empty());
        }
        app.set_recovered_type_filter(RecoveredResourceTypeFilter::Patient);
        app.select_encrypted_readback_resource(1).unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(1));
        app.follow_encrypted_readback_incoming(2, 0).unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(2));
        assert_eq!(
            app.encrypted_readback_filter,
            RecoveredResourceTypeFilter::All
        );

        app.set_recovered_type_filter(RecoveredResourceTypeFilter::Patient);
        assert_eq!(
            app.select_encrypted_readback_resource(0),
            Err("encrypted_readback_filtered_resource_refused")
        );
        assert!(app.encrypted_readback.is_none());
        assert_eq!(app.recovered_visible_count(), 0);
        assert_eq!(
            app.encrypted_readback_filter,
            RecoveredResourceTypeFilter::All
        );
    }

    #[test]
    fn recovered_core_search_composes_with_type_facets_and_clears_stale_selection() {
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.select_encrypted_readback_resource(0).unwrap();
        app.set_recovered_search_query("  PATIENT  ").unwrap();
        assert_eq!(app.encrypted_readback_query, "patient");
        assert_eq!(app.recovered_visible_count(), 1);
        assert!(app.encrypted_readback_selected.is_none());
        assert!(app.encrypted_readback_history.is_empty());
        assert_eq!(
            app.select_encrypted_readback_resource(0),
            Err("encrypted_readback_filtered_resource_refused")
        );
        assert!(app.encrypted_readback.is_none());
        assert!(app.encrypted_readback_query.is_empty());

        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.set_recovered_search_query("fictional-observation-001")
            .unwrap();
        assert_eq!(app.recovered_visible_count(), 1);
        app.select_encrypted_readback_resource(0).unwrap();
        app.follow_encrypted_readback_link(0).unwrap();
        assert_eq!(app.encrypted_readback_selected, Some(1));
        assert!(app.encrypted_readback_query.is_empty());
        assert_eq!(app.recovered_visible_count(), 3);
        assert_eq!(app.encrypted_readback_history, vec![0]);

        app.set_recovered_type_filter(RecoveredResourceTypeFilter::Encounter);
        assert!(app.encrypted_readback_history.is_empty());
        assert!(app.encrypted_readback_selected.is_none());
        assert_eq!(app.recovered_visible_count(), 1);
        app.set_recovered_search_query("patient").unwrap();
        assert_eq!(app.recovered_visible_count(), 0);
        assert!(app.encrypted_readback.is_some());
        app.set_recovered_search_query("FICTIONAL-ENCOUNTER")
            .unwrap();
        assert_eq!(app.recovered_visible_count(), 1);
        app.set_recovered_search_query("").unwrap();
        assert_eq!(app.recovered_visible_count(), 1);
        assert!(app.encrypted_readback_query.is_empty());

        assert_eq!(
            app.set_recovered_search_query("unreviewed:patient-data/real-name"),
            Err("fictional_search_unreviewed_characters_or_length")
        );
        assert!(app.encrypted_readback.is_none());
        assert!(app.encrypted_readback_query.is_empty());
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        assert!(app.set_recovered_search_query(&"x".repeat(65)).is_err());
        assert!(app.encrypted_readback.is_none());
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        assert!(app.set_recovered_search_query("مريض").is_err());
        assert!(app.encrypted_readback.is_none());
    }

    #[test]
    fn mismatched_incoming_edge_and_unbounded_history_fail_closed() {
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.select_encrypted_readback_resource(1).unwrap(); // Patient
        assert_eq!(
            app.follow_encrypted_readback_incoming(0, 1), // Observation.encounter != Patient
            Err("encrypted_readback_incoming_edge_mismatch")
        );
        assert!(app.encrypted_readback.is_none());
        assert!(app.encrypted_readback_history.is_empty());

        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.select_encrypted_readback_resource(1).unwrap();
        for _ in 0..8 {
            app.follow_encrypted_readback_incoming(0, 0).unwrap(); // Patient -> Observation
            app.follow_encrypted_readback_link(0).unwrap(); // Observation -> Patient
        }
        assert_eq!(app.encrypted_readback_history.len(), 16);
        assert_eq!(
            app.follow_encrypted_readback_incoming(0, 0),
            Err("encrypted_readback_navigation_limit")
        );
        assert!(app.encrypted_readback.is_none());
        assert!(app.encrypted_readback_history.is_empty());
    }

    #[test]
    fn recovered_encrypted_core_unknown_and_stale_selection_fail_closed() {
        let raw = include_bytes!("../fixtures/core/encrypted-readback-projection.json");
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        assert_eq!(
            app.follow_encrypted_readback_link(0),
            Err("encrypted_readback_no_selection")
        );
        assert!(!app.has_external_synthetic_encrypted_readback());
        assert!(app.encrypted_readback.is_none());
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        assert_eq!(
            app.select_encrypted_readback_resource(usize::MAX),
            Err("encrypted_readback_unknown_resource")
        );
        assert!(!app.has_external_synthetic_encrypted_readback());
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.select_encrypted_readback_resource(1).unwrap(); // recovered Patient has no links
        assert_eq!(
            app.follow_encrypted_readback_link(0),
            Err("encrypted_readback_unknown_link")
        );
        assert!(app.encrypted_readback.is_none());
        let mut app =
            MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(raw).unwrap();
        app.select_encrypted_readback_resource(0).unwrap();
        app.follow_encrypted_readback_link(0).unwrap();
        app.clear_fictional_output();
        assert!(app.encrypted_readback.is_none());
        assert!(app.encrypted_readback_history.is_empty());
        assert!(!app.has_external_synthetic_encrypted_readback());
    }

    #[test]
    fn fictional_resource_type_facets_show_only_exact_allowlisted_cases() {
        let mut app = MedOriginNativePreview::default();
        app.enter_fictional_workspace();
        for (filter, indexes) in [
            (FictionalResourceTypeFilter::Patient, vec![0usize]),
            (FictionalResourceTypeFilter::Observation, vec![1, 2]),
            (FictionalResourceTypeFilter::Bundle, vec![3, 4, 5]),
            (FictionalResourceTypeFilter::All, vec![0, 1, 2, 3, 4, 5]),
        ] {
            app.filter_fictional_resource_type(filter);
            let visible: Vec<usize> = FICTIONAL_WORKSPACE_CASES
                .iter()
                .enumerate()
                .filter(|(_, spec)| app.admits_fictional_case(**spec))
                .map(|(index, _)| index)
                .collect();
            assert_eq!(visible, indexes);
            for index in 0..FICTIONAL_WORKSPACE_CASES.len() {
                if indexes.contains(&index) {
                    app.open_fictional_workspace_case(index).unwrap();
                } else {
                    assert_eq!(
                        app.open_fictional_workspace_case(index),
                        Err("fictional_workspace_case_filtered_out")
                    );
                    assert!(app.fictional_workspace_detail.is_none());
                }
            }
        }
        app.filter_fictional_resource_type(FictionalResourceTypeFilter::Observation);
        app.filter_fictional_workspace(FictionalWorkspaceFilter::ExpectedNegative);
        assert_eq!(
            (0..6)
                .filter(|index| app.admits_fictional_case(FICTIONAL_WORKSPACE_CASES[*index]))
                .collect::<Vec<_>>(),
            vec![2]
        );
        app.close_fictional_workspace();
        assert_eq!(
            app.fictional_workspace_resource_type,
            FictionalResourceTypeFilter::All
        );
        assert!(!app.fictional_workspace_unlocked);
    }

    #[test]
    fn native_fictional_reference_navigation_follows_reviewed_source_and_back() {
        let mut app = MedOriginNativePreview::default();
        app.enter_fictional_workspace();
        app.open_fictional_workspace_case(1).unwrap();
        app.follow_fictional_relation(0).unwrap();
        assert_eq!(app.fictional_workspace_selected, Some(0));
        assert_eq!(app.fictional_workspace_back, Some(1));
        assert_eq!(
            app.fictional_workspace_detail.as_ref().unwrap().fixture.id,
            "patient-minimal"
        );
        app.back_to_previous_fictional_case().unwrap();
        assert_eq!(app.fictional_workspace_selected, Some(1));
        assert!(app.fictional_workspace_back.is_none());

        app.open_fictional_workspace_case(3).unwrap();
        app.follow_fictional_relation(0).unwrap(); // source-pinned Bundle Patient member
        assert_eq!(app.fictional_workspace_selected, Some(0));
        app.back_to_previous_fictional_case().unwrap();
        assert_eq!(app.fictional_workspace_selected, Some(3));
        app.follow_fictional_relation(1).unwrap(); // source-pinned Bundle Observation member
        assert_eq!(app.fictional_workspace_selected, Some(1));
        app.back_to_previous_fictional_case().unwrap();
        assert_eq!(app.fictional_workspace_selected, Some(3));
        app.open_fictional_workspace_case(4).unwrap();
        app.follow_fictional_relation(2).unwrap(); // UUID patient subject
        assert_eq!(app.fictional_workspace_selected, Some(0));
    }

    #[test]
    fn navigation_refuses_hidden_targets_unknown_edges_and_stale_details() {
        let mut app = MedOriginNativePreview::default();
        app.enter_fictional_workspace();
        app.filter_fictional_resource_type(FictionalResourceTypeFilter::Bundle);
        app.open_fictional_workspace_case(3).unwrap();
        assert_eq!(
            app.follow_fictional_relation(0),
            Err("fictional_workspace_relation_target_filtered_out")
        );
        assert!(app.fictional_workspace_detail.is_none());
        assert!(app.fictional_workspace_back.is_none());
        assert!(app.fictional_workspace_notice.is_some());
        app.filter_fictional_resource_type(FictionalResourceTypeFilter::All);
        app.open_fictional_workspace_case(5).unwrap();
        assert_eq!(
            app.follow_fictional_relation(0),
            Err("fictional_relation_fixture_not_approved")
        );
        assert!(app.fictional_workspace_detail.is_none());

        app.open_fictional_workspace_case(3).unwrap();
        assert_eq!(
            app.follow_fictional_relation(usize::MAX),
            Err("fictional_workspace_relation_not_approved")
        );
        assert!(app.fictional_workspace_selected.is_none());
        app.open_fictional_workspace_case(3).unwrap();
        app.clear_fictional_output();
        assert_eq!(
            app.follow_fictional_relation(0),
            Err("fictional_workspace_source_not_selected")
        );
        assert!(app.fictional_workspace_detail.is_none());
        app.close_fictional_workspace();
        assert_eq!(
            app.follow_fictional_relation(0),
            Err("fictional_workspace_closed")
        );
    }

    #[test]
    fn fictional_back_is_one_step_and_never_survives_clear_filter_or_close() {
        let mut app = MedOriginNativePreview::default();
        app.enter_fictional_workspace();
        assert_eq!(
            app.back_to_previous_fictional_case(),
            Err("fictional_workspace_no_previous_case")
        );
        app.open_fictional_workspace_case(1).unwrap();
        app.follow_fictional_relation(0).unwrap();
        app.back_to_previous_fictional_case().unwrap();
        assert_eq!(
            app.back_to_previous_fictional_case(),
            Err("fictional_workspace_no_previous_case")
        );
        app.open_fictional_workspace_case(1).unwrap();
        app.follow_fictional_relation(0).unwrap();
        app.filter_fictional_workspace(FictionalWorkspaceFilter::ExpectedNegative);
        assert!(app.fictional_workspace_back.is_none());
        assert!(app.fictional_workspace_detail.is_none());
        app.filter_fictional_workspace(FictionalWorkspaceFilter::All);
        app.open_fictional_workspace_case(1).unwrap();
        app.follow_fictional_relation(0).unwrap();
        app.close_fictional_workspace();
        assert!(app.fictional_workspace_back.is_none());
        assert!(app.fictional_workspace_detail.is_none());
    }

    #[test]
    fn encrypted_workspace_receipt_clear_switch_and_embedded_mode_never_retain_external_claim() {
        let source = include_bytes!("../fixtures/core/workspace-ephemeral-demo.json");
        let mut app = MedOriginNativePreview::from_one_time_synthetic_workspace_stdin(source)
            .expect("only fixed fictional source metadata is admitted");
        assert!(app.has_external_fictional_workspace_stdin());
        assert_eq!(
            app.encrypted_workspace_receipt
                .as_ref()
                .unwrap()
                .resource_count,
            3
        );
        assert!(app.core_report.is_none());
        app.clear_fictional_output();
        assert!(!app.has_external_fictional_workspace_stdin());
        assert!(app.encrypted_workspace_receipt.is_none());
        app.inspect_compiled_encrypted_demo().unwrap();
        assert!(!app.has_external_fictional_workspace_stdin());
        assert_eq!(
            app.encrypted_workspace_receipt
                .as_ref()
                .unwrap()
                .audit_events,
            1
        );
        app.inspect_selected_core_receipt().unwrap();
        assert!(app.encrypted_workspace_receipt.is_none());
        assert!(!app.has_external_fictional_workspace_stdin());
        app.inspect_compiled_encrypted_demo().unwrap();
        app.hash_selected().unwrap();
        assert!(app.encrypted_workspace_receipt.is_none());
    }

    #[test]
    fn external_one_shot_core_report_clears_on_other_native_actions() {
        let known = include_bytes!("../fixtures/core/known-structure-definition.json");
        let negative = include_bytes!("../fixtures/core/unknown-fictional-negative.json");
        for (raw, expected_selection) in [(known.as_slice(), 0usize), (negative.as_slice(), 1usize)]
        {
            let mut app = MedOriginNativePreview::from_one_time_fictional_core_stdin(raw)
                .expect("exact canonical fictional source bytes");
            assert!(app.has_external_fictional_core_stdin());
            assert_eq!(app.core_report_selection, expected_selection);
            assert_eq!(app.core_report.as_ref().unwrap().status, "not_validated");
            app.clear_fictional_output();
            assert!(!app.has_external_fictional_core_stdin());
            assert!(app.core_report.is_none());
            // Embedded source viewer must never inherit the external marker.
            app.inspect_selected_core_receipt().unwrap();
            assert!(!app.has_external_fictional_core_stdin());
            assert!(app.core_report.is_some());
            app.hash_selected().unwrap();
            assert!(app.core_report.is_none());
        }
    }

    #[test]
    fn fictional_workspace_is_closed_by_default_and_denies_case_opening() {
        let mut app = MedOriginNativePreview::default();
        assert!(!app.fictional_workspace_unlocked);
        assert_eq!(
            app.open_fictional_workspace_case(0),
            Err("fictional_workspace_closed")
        );
        assert!(app.fictional_workspace_detail.is_none());
        assert!(app.fictional_workspace_notice.is_some());
    }

    #[test]
    fn fictional_workspace_all_six_source_pinned_cases_have_exact_identity_and_graph() {
        let mut app = MedOriginNativePreview::default();
        app.enter_fictional_workspace();
        let mut cases = HashSet::new();
        for (case_index, spec) in FICTIONAL_WORKSPACE_CASES.iter().enumerate() {
            assert!(
                cases.insert(spec.fixture_index),
                "duplicate fictional source"
            );
            app.open_fictional_workspace_case(case_index)
                .expect("only fixed source-compiled fictional inputs allowed");
            let detail = app
                .fictional_workspace_detail
                .as_ref()
                .expect("verified fictional detail");
            assert_eq!(detail.fixture.id, FIXTURES[spec.fixture_index].id);
            assert_eq!(detail.fixture.sha256, FIXTURES[spec.fixture_index].sha256);
            assert_eq!(detail.resource_type, spec.resource_type);
            assert_eq!(detail.resource_id, spec.resource_id);
            assert_eq!(detail.negative, spec.negative);
            assert_eq!(detail.relations.len(), spec.expected_edges);
            assert_eq!(app.fictional_workspace_selected, Some(case_index));
            assert!(app.fictional_workspace_notice.is_none());
            assert!(app.preview.is_none());
            assert!(app.core_report.is_none());
            assert!(app.result.is_none());
        }
        assert_eq!(cases.len(), 6);
    }

    #[test]
    fn fictional_workspace_filter_refuses_hidden_cases_and_clears_stale_evidence() {
        let mut app = MedOriginNativePreview::default();
        app.enter_fictional_workspace();
        app.open_fictional_workspace_case(1).unwrap();
        assert!(app.fictional_workspace_detail.is_some());
        app.filter_fictional_workspace(FictionalWorkspaceFilter::ExpectedNegative);
        assert!(app.fictional_workspace_detail.is_none());
        assert!(app.fictional_workspace_selected.is_none());
        assert_eq!(
            app.open_fictional_workspace_case(1),
            Err("fictional_workspace_case_filtered_out")
        );
        assert!(app.fictional_workspace_detail.is_none());
        assert!(app.fictional_workspace_notice.is_some());
        for index in [2usize, 5] {
            app.open_fictional_workspace_case(index)
                .expect("two source-reviewed negative controls");
            assert!(app.fictional_workspace_detail.as_ref().unwrap().negative);
        }
        app.filter_fictional_workspace(FictionalWorkspaceFilter::ExpectedEnvelopeOk);
        assert!(app.fictional_workspace_detail.is_none());
        for index in [0usize, 1, 3, 4] {
            app.open_fictional_workspace_case(index).unwrap();
            assert!(!app.fictional_workspace_detail.as_ref().unwrap().negative);
        }
        assert_eq!(
            app.open_fictional_workspace_case(5),
            Err("fictional_workspace_case_filtered_out")
        );
    }

    #[test]
    fn fictional_workspace_close_escape_and_other_source_actions_clear_details() {
        let mut app = MedOriginNativePreview::default();
        app.enter_fictional_workspace();
        app.open_fictional_workspace_case(3).unwrap();
        assert_eq!(
            app.fictional_workspace_detail
                .as_ref()
                .unwrap()
                .relations
                .len(),
            3
        );
        app.clear_fictional_output(); // Escape path used by native eframe.
        assert!(app.fictional_workspace_detail.is_none());
        assert!(app.fictional_workspace_unlocked); // UI still requires explicit Close.
        app.open_fictional_workspace_case(4).unwrap();
        app.inspect_selected_core_receipt().unwrap();
        assert!(app.fictional_workspace_detail.is_none());
        assert!(app.core_report.is_some());
        app.open_fictional_workspace_case(2).unwrap();
        assert!(app.core_report.is_none());
        app.close_fictional_workspace();
        assert!(!app.fictional_workspace_unlocked);
        assert!(app.fictional_workspace_detail.is_none());
        assert!(app.fictional_workspace_selected.is_none());
        assert_eq!(
            app.fictional_workspace_filter,
            FictionalWorkspaceFilter::All
        );
        assert_eq!(
            app.open_fictional_workspace_case(0),
            Err("fictional_workspace_closed")
        );
    }

    #[test]
    fn fictional_workspace_unknown_case_indexes_never_reuse_previous_success() {
        let mut app = MedOriginNativePreview::default();
        app.enter_fictional_workspace();
        app.open_fictional_workspace_case(0).unwrap();
        for index in [6, 7, usize::MAX] {
            assert_eq!(
                app.open_fictional_workspace_case(index),
                Err("fictional_workspace_case_not_allowed")
            );
            assert!(app.fictional_workspace_detail.is_none());
            assert!(app.fictional_workspace_selected.is_none());
            assert!(app.fictional_workspace_notice.is_some());
        }
    }

    #[test]
    fn actual_native_core_provenance_view_model_inspects_two_source_pinned_receipts() {
        let mut app = MedOriginNativePreview::default();
        for index in 0..PINNED_CORE_CASE_LABELS.len() {
            app.core_report_selection = index;
            app.inspect_selected_core_receipt()
                .expect("real pinned synthetic Core data");
            let receipt = app
                .core_report
                .as_ref()
                .expect("Core report visible after admission");
            assert_eq!(receipt.status, "not_validated");
            assert!(receipt.disclosure.contains("Not for patient data"));
            assert_eq!(receipt.report_sha256.len(), 64);
            assert!(app.core_report_notice.is_none());
            assert!(app.preview.is_none());
            assert!(app.comparison.is_none());
            assert!(app.result.is_none());
        }
        // A new native fixture selection/hash action must not preserve
        // a previously rendered source-bound Core report.
        app.hash_selected().expect("fictional D0 fixture");
        assert!(app.core_report.is_none());
        assert!(app.core_report_notice.is_none());
        assert!(app.result.is_some());
    }

    #[test]
    fn invalid_core_selection_and_explicit_clear_fail_closed_without_stale_display() {
        let mut app = MedOriginNativePreview::default();
        app.inspect_selected_core_receipt()
            .expect("source-backed first QA receipt");
        assert!(app.core_report.is_some());
        app.core_report_selection = usize::MAX;
        assert_eq!(
            app.inspect_selected_core_receipt(),
            Err("core_report_inspection_refused")
        );
        assert!(app.core_report.is_none());
        assert!(app.core_report_notice.is_some());
        app.core_report_selection = 1;
        app.inspect_selected_core_receipt()
            .expect("source-backed negative QA receipt");
        assert!(app.core_report.is_some());
        assert!(app.core_report_notice.is_none());
        app.clear_fictional_output();
        assert!(app.core_report.is_none());
        assert!(app.core_report_notice.is_none());
        assert_eq!(app.core_report_selection, 1);
    }

    #[test]
    fn three_compiled_fictional_sources_yield_exact_reference_pointers_without_dates() {
        let cases = [
            (
                "observation-minimal",
                4usize,
                1usize,
                "/subject/reference",
                "Patient/synthetic",
            ),
            (
                "bundle-valid",
                6usize,
                3usize,
                "/entry/1/resource/subject/reference",
                "Patient/synthetic",
            ),
            (
                "bundle-linked",
                10usize,
                3usize,
                "/entry/1/resource/subject/reference",
                "urn:uuid:00000000-0000-4000-8000-000000000001",
            ),
        ];
        for (id, selected, expected_count, expected_pointer, expected_target) in cases {
            let mut app = MedOriginNativePreview {
                selected,
                ..Default::default()
            };
            assert_eq!(FIXTURES[selected].id, id);
            app.inspect_selected_relationships()
                .expect("three reviewed fictional graph inputs");
            let view = app
                .relationships
                .as_ref()
                .expect("verified source-bound graph");
            assert_eq!(view.source.id, id);
            assert_eq!(view.source.sha256, FIXTURES[selected].sha256);
            assert_eq!(view.edges.len(), expected_count);
            assert!(
                view.edges
                    .iter()
                    .any(|e| e.source_pointer == expected_pointer && e.target == expected_target)
            );
            assert!(app.relationship_notice.is_none());
            assert!(app.preview.is_none());
            assert!(app.comparison.is_none());
        }
    }

    #[test]
    fn malformed_fictional_edges_and_invented_dates_are_refused() {
        let observation = MedOriginNativePreview::verified_json_for(4).unwrap();
        let obs_changed = observation.replace("Patient/synthetic", "Patient/external");
        assert_eq!(
            project_pinned_fictional_relations("observation-minimal", &obs_changed),
            Err("fictional_relation_changed"),
        );
        let obs_dated = observation.replace(
            "\"status\":\"final\"",
            "\"status\":\"final\",\"effectiveDateTime\":\"2026-01-01\"",
        );
        assert_eq!(
            project_pinned_fictional_relations("observation-minimal", &obs_dated),
            Err("fictional_relation_unreviewed_date"),
        );
        for (name, index) in [("bundle-valid", 6usize), ("bundle-linked", 10usize)] {
            let source = MedOriginNativePreview::verified_json_for(index).unwrap();
            assert_eq!(
                project_pinned_fictional_relations(name, source)
                    .unwrap()
                    .len(),
                3
            );
            let bad_urn = source.replace(
                "00000000-0000-4000-8000-000000000002",
                "00000000-0000-4000-8000-000000000003",
            );
            assert_eq!(
                project_pinned_fictional_relations(name, &bad_urn),
                Err("fictional_relation_changed"),
            );
            let bad_entries = source.replace("\"entry\":[", "\"entry\":[]");
            assert!(project_pinned_fictional_relations(name, &bad_entries).is_err());
            let noncanonical_date = source.replace(
                "\"active\":true",
                "\"active\":true,\"birthDate\":\"1970-01-01\"",
            );
            assert_eq!(
                project_pinned_fictional_relations(name, &noncanonical_date),
                Err("fictional_relation_unreviewed_date"),
            );
        }
        assert_eq!(
            project_pinned_fictional_relations("patient-minimal", observation),
            Err("fictional_relation_fixture_not_approved"),
        );
        assert!(project_pinned_fictional_relations("bundle-valid", "not-json").is_err());
    }

    #[test]
    fn relationship_ui_state_clears_on_explicit_verify_reset_and_invalid_fixture() {
        let mut app = MedOriginNativePreview {
            selected: 4,
            ..Default::default()
        };
        app.inspect_selected_relationships().unwrap();
        assert!(app.relationships.is_some());
        app.hash_selected().unwrap();
        assert!(
            app.relationships.is_none(),
            "verification must clear prior graph"
        );
        assert!(app.relationship_notice.is_none());
        app.inspect_selected_relationships().unwrap();
        app.clear_fictional_output();
        assert!(app.relationships.is_none());
        assert!(app.relationship_notice.is_none());
        app.inspect_selected_relationships().unwrap();
        app.selected = 1; // intentionally invalid UTF-8 boundary vector
        assert_eq!(
            app.inspect_selected_relationships(),
            Err("fictional_relation_fixture_not_approved"),
        );
        assert!(app.relationships.is_none());
        assert!(app.relationship_notice.is_some());
        app.selected = usize::MAX;
        assert_eq!(
            app.inspect_selected_relationships(),
            Err("invalid_synthetic_selection"),
        );
        assert!(app.relationships.is_none());
    }

    #[test]
    fn clear_fictional_output_removes_all_rendered_state_without_mutating_choices() {
        let mut app = MedOriginNativePreview {
            selected: 0,
            compare_with: 4,
            ..Default::default()
        };
        assert!(app.compare_selected().is_ok());
        assert!(app.comparison.is_some());
        app.clear_fictional_output();
        assert_eq!((app.selected, app.compare_with), (0, 4));
        assert!(app.result.is_none());
        assert!(app.preview.is_none());
        assert!(app.preview_notice.is_none());
        assert!(app.comparison.is_none());

        assert!(app.preview_selected().is_ok());
        assert!(app.preview.is_some());
        app.clear_fictional_output();
        assert!(app.result.is_none());
        assert!(app.preview.is_none());
        assert!(app.preview_notice.is_none());
        assert!(app.comparison.is_none());

        app.selected = 1; // synthetic invalid UTF-8 boundary fixture
        assert_eq!(app.preview_selected(), Err("preview_unavailable"));
        assert!(app.preview_notice.is_some());
        app.clear_fictional_output();
        assert!(app.result.is_none());
        assert!(app.preview_notice.is_none());
        assert!(app.comparison.is_none());
    }

    #[test]
    fn directional_semantic_and_hex_details_are_cleared_before_recomparing() {
        let mut app = MedOriginNativePreview {
            selected: 0,
            compare_with: 4,
            ..Default::default()
        };
        app.compare_selected().expect("first fictional comparison");
        let first = app.comparison.as_ref().expect("first comparison state");
        assert_eq!(first.left.id, "patient-minimal");
        assert_eq!(first.right.id, "observation-minimal");
        assert!(
            first
                .json_path_diff
                .contains("Fictional JSON path difference: /")
        );
        assert!(
            first
                .byte_diff_summary
                .contains("Fictional byte difference:")
        );
        assert!(
            first
                .byte_context
                .contains("Fictional HEX context at zero-based byte")
        );
        let previous_pointer = first.json_path_diff.clone();
        let previous_bytes = first.byte_diff_summary.clone();
        let previous_hex = first.byte_context.clone();

        app.clear_fictional_output();
        assert_eq!((app.selected, app.compare_with), (0, 4));
        assert!(app.result.is_none());
        assert!(app.preview.is_none());
        assert!(app.preview_notice.is_none());
        assert!(app.comparison.is_none());

        // A changed selection must compute *new* directional evidence rather
        // than resurrecting the previous JSON Pointer or raw byte context.
        app.compare_with = 6;
        app.compare_selected().expect("second fictional comparison");
        let second = app.comparison.as_ref().expect("second comparison state");
        assert_eq!(second.left.id, "patient-minimal");
        assert_eq!(second.right.id, "bundle-valid");
        assert!(
            second
                .json_path_diff
                .contains("Fictional JSON path difference: /")
        );
        assert!(
            second
                .byte_diff_summary
                .contains("Fictional byte difference:")
        );
        assert!(
            second
                .byte_context
                .contains("Fictional HEX context at zero-based byte")
        );
        assert_ne!(
            second.json_path_diff, previous_pointer,
            "stale JSON Pointer"
        );
        assert_ne!(
            second.byte_diff_summary, previous_bytes,
            "stale byte comparison"
        );
        assert_ne!(second.byte_context, previous_hex, "stale HEX context");
    }

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
    fn fictional_preview_hash_checks_returned_bytes_not_only_provider_metadata() {
        let original =
            fictional_json_preview_v1("patient-minimal").expect("compiled fictional Patient");
        assert!(verified_fictional_preview_bytes(
            FIXTURES[0],
            original.raw_json
        ));

        // Same byte count and unchanged metadata, different actual source data.
        let modified = original.raw_json.replacen("synthetic", "synthetix", 1);
        assert_eq!(modified.len(), original.raw_json.len());
        assert!(!verified_fictional_preview_bytes(FIXTURES[0], &modified));

        // A forged metadata/catalog pairing cannot authorize a different hash.
        let wrong_digest = FixtureSpec {
            sha256: FIXTURES[4].sha256,
            ..FIXTURES[0]
        };
        assert!(!verified_fictional_preview_bytes(
            wrong_digest,
            original.raw_json
        ));

        // Even if a catalog entry advertises 2,049 bytes, no oversized raw
        // preview can pass the independent D2 display/compare boundary.
        let oversized = "a".repeat(2_049);
        let oversized_spec = FixtureSpec {
            bytes: oversized.len(),
            ..FIXTURES[0]
        };
        assert!(!verified_fictional_preview_bytes(
            oversized_spec,
            &oversized
        ));

        for fixture in FIXTURES {
            if let Ok(payload) = fictional_json_preview_v1(fixture.id) {
                assert!(
                    verified_fictional_preview_bytes(fixture, payload.raw_json),
                    "compiled fictional preview must match digest: {}",
                    fixture.id
                );
            }
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
        assert!(
            changed
                .contains(r#"/resourceType (value differs: left="Patient", right="Observation")"#)
        );
        let escaped = fictional_json_path_diff(r#"{"a/b~c":[1,2]}"#, r#"{"a/b~c":[1,3]}"#).unwrap();
        assert!(escaped.contains("/a~1b~0c/1 (value differs: left=2, right=3)"));
        let missing = fictional_json_path_diff(r#"{"a":1}"#, r#"{"a":1,"b":2}"#).unwrap();
        assert!(missing.contains("/b (field missing on left; right=2)"));
        let reverse_missing = fictional_json_path_diff(r#"{"a":1,"b":2}"#, r#"{"a":1}"#).unwrap();
        assert!(reverse_missing.contains("/b (field missing on right; left=2)"));
        let array = fictional_json_path_diff(r#"{"a":[1]}"#, r#"{"a":[1,2]}"#).unwrap();
        assert!(array.contains("/a/1 (array length differs: left=1, right=2)"));
        let reverse_array = fictional_json_path_diff(r#"{"a":[1,2]}"#, r#"{"a":[1]}"#).unwrap();
        assert!(reverse_array.contains("/a/1 (array length differs: left=2, right=1)"));
        let types = fictional_json_path_diff(r#"{"a":true}"#, r#"{"a":"true"}"#).unwrap();
        assert!(types.contains("/a (JSON type differs: left=boolean, right=string)"));
        let long = format!(r#"{{"a":"{}"}}"#, "x".repeat(300));
        let bounded = fictional_json_path_diff(&long, r#"{"a":"y"}"#).unwrap();
        assert!(bounded.len() < 400, "never emit an unbounded scalar hint");
        let root = fictional_json_path_diff("true", "false").unwrap();
        assert!(root.contains("(root) (value differs: left=true, right=false)"));
        assert_eq!(
            fictional_json_path_diff("not json", "{}"),
            Err("fictional_json_parse_refused")
        );
    }

    #[test]
    fn pinned_fictional_patient_observation_pointer_matches_windows_uia_contract() {
        let left =
            MedOriginNativePreview::verified_json_for(0).expect("pinned fictional Patient bytes");
        let right = MedOriginNativePreview::verified_json_for(4)
            .expect("pinned fictional Observation bytes");
        assert_eq!(
            fictional_json_path_diff(left, right).expect("synthetic JSON Pointer"),
            "Fictional JSON path difference: /id (value differs: left=\"synthetic\", right=\"synthetic-observation\"). Structural developer hint only; original source bytes unchanged."
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
