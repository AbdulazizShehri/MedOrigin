// Adapted from emilk/eframe_template under Apache-2.0, see UPSTREAM-NOTICE.md.
// Synthetic-only, in-process native Rust eframe + D0; no browser, EHR, PHI or network.
use crate::core_provenance::{
    CoreProvenanceReceipt, FictionalCoreInput, PINNED_CORE_CASE_LABELS,
    admit_exact_source_reviewed_external_core_report, inspect_pinned_core_report,
};
use crate::encrypted_readback::{
    FictionalEncryptedReadback, admit_exact_encrypted_readback_projection,
};
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
    core_report_notice: Option<&'static str>,
    external_core_source_visible: bool,
    encrypted_workspace_receipt: Option<FictionalEncryptedWorkspaceReceipt>,
    encrypted_readback: Option<FictionalEncryptedReadback>,
    encrypted_readback_source_external: bool,
    encrypted_readback_selected: Option<usize>,
    encrypted_readback_history: Vec<usize>,
    encrypted_readback_filter: RecoveredResourceTypeFilter,
    encrypted_readback_query: String,
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
        self.core_report_notice = None;
        self.external_core_source_visible = false;
        self.encrypted_workspace_receipt = None;
        self.encrypted_readback = None;
        self.encrypted_readback_source_external = false;
        self.encrypted_readback_selected = None;
        self.encrypted_readback_history.clear();
        self.encrypted_readback_filter = RecoveredResourceTypeFilter::All;
        self.encrypted_readback_query.clear();
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
        self.core_report_notice = None;
        self.external_core_source_visible = false;
        self.encrypted_workspace_receipt = None;
        self.encrypted_readback = None;
        self.encrypted_readback_source_external = false;
        self.encrypted_readback_selected = None;
        self.encrypted_readback_history.clear();
        self.encrypted_readback_filter = RecoveredResourceTypeFilter::All;
        self.encrypted_readback_query.clear();
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

impl eframe::App for MedOriginNativePreview {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        if ui.input(|input| input.key_pressed(egui::Key::Escape)) {
            self.clear_fictional_output();
        }
        egui::CentralPanel::default().show(ui, |ui| {
            ui.heading("MedOrigin — Native Rust Experiment");
            ui.strong("Synthetic developer preview only · No EHR · No clinical use");
            ui.label("No browser engine, IPC server, Python worker, filesystem input or model is used in this proof of concept.");
            // This top-level native home is directly usable without scrolling
            // through historical developer fixtures. It exposes no PHI and
            // cannot create a patient, write to SQLite, or launch Core.
            let mut open_home_chart = false;
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
                } else {
                    ui.label("No verified encrypted Core Workspace is attached to this GUI session.");
                    ui.label("Launch the separate fictional-only portable Core demo to display verified identities.");
                }
            });
            if open_home_chart {
                let _ = self.open_recovered_fictional_patient_chart();
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
