//! Closed-world timeline projection of THREE examples from FOUR compiled
//! FICTIONAL fixtures. Never a general patient timeline or clinical FHIR parser.
//! No file IO, network, PHI, system clock, timezone, or user-supplied document.

use super::{CommandError, FIXTURES, fixture_entry, sha256_hex, structural};
use serde::Serialize;
use serde_json::Value;

pub(super) const CONTRACT_TIMELINE: &str = "medorigin-three-fictional-timeline-entries-v1";
pub(super) const TIMELINE_SCOPE: &str = "FOUR_PINNED_SYNTHETIC_FIXTURES";
const PATIENT_ID: &str = "fixture-patient-alpha";

#[derive(Serialize, Debug)]
#[serde(deny_unknown_fields)]
pub(super) struct FictionalTimelineEvent {
    pub event_id: &'static str,
    pub event_kind: &'static str,
    pub source_fixture_id: &'static str,
    pub source_resource_type: &'static str,
    pub source_sha256_hex: String,
    pub source_byte_len: usize,
    pub date: Option<String>,
    pub date_json_pointer: Option<&'static str>,
    pub date_status: &'static str,
    pub label: &'static str,
}

#[derive(Serialize, Debug)]
#[serde(deny_unknown_fields)]
pub(super) struct FictionalPatientTimeline {
    pub contract: &'static str,
    pub patient_fixture_id: &'static str,
    pub scope: &'static str,
    pub order: &'static str,
    pub events: Vec<FictionalTimelineEvent>,
    pub synthetic_only: bool,
    pub fhir_semantics_validated: bool,
    pub release_authorized: bool,
}

fn invalid() -> CommandError {
    CommandError::new("fictional_timeline_rejected")
}

// Conservative calendar syntax guard, not FHIR date-profile validation.
fn valid_yyyy_mm_dd(text: &str) -> bool {
    let b = text.as_bytes();
    if b.len() != 10 || b[4] != b'-' || b[7] != b'-' {
        return false;
    }
    if ![0, 1, 2, 3, 5, 6, 8, 9]
        .into_iter()
        .all(|index| b[index].is_ascii_digit())
    {
        return false;
    }
    let parse = |range: std::ops::Range<usize>| -> Option<u32> {
        std::str::from_utf8(&b[range]).ok()?.parse::<u32>().ok()
    };
    let (year, month, day) = match (parse(0..4), parse(5..7), parse(8..10)) {
        (Some(y), Some(m), Some(d)) if (1..=9999).contains(&y) => (y, m, d),
        _ => return false,
    };
    let leap = year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
    let max_days = match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if leap => 29,
        2 => 28,
        _ => return false,
    };
    (1..=max_days).contains(&day)
}

fn read_pinned_date(
    document: &Value,
    pointer: &str,
    exact_expected: &str,
) -> Result<String, CommandError> {
    let date = document
        .pointer(pointer)
        .and_then(Value::as_str)
        .ok_or_else(invalid)?;
    // Changing a committed fixture's meaning must require explicit review;
    // do not silently create a new real-world chronology.
    if !valid_yyyy_mm_dd(date) || date != exact_expected {
        return Err(invalid());
    }
    Ok(date.to_owned())
}

fn document(id: &str) -> Result<(Value, &'static [u8]), CommandError> {
    let (_, _, bytes) = fixture_entry(id).ok_or_else(invalid)?;
    if bytes.len() > super::MAX_INPUT_BYTES {
        return Err(invalid());
    }
    let parsed = serde_json::from_slice::<Value>(bytes).map_err(|_| invalid())?;
    Ok((parsed, bytes))
}

fn dated_event(
    source: &'static str,
    kind: &'static str,
    event_id: &'static str,
    label: &'static str,
    date: String,
    pointer: &'static str,
) -> Result<FictionalTimelineEvent, CommandError> {
    let (_, bytes) = document(source)?;
    Ok(FictionalTimelineEvent {
        event_id,
        event_kind: kind,
        source_fixture_id: source,
        source_resource_type: structural_kind(source)?,
        source_sha256_hex: sha256_hex(bytes),
        source_byte_len: bytes.len(),
        date: Some(date),
        date_json_pointer: Some(pointer),
        date_status: "source_date_only",
        label,
    })
}

fn structural_kind(source: &'static str) -> Result<&'static str, CommandError> {
    match source {
        "fixture-patient-alpha" => Ok("Patient"),
        "fixture-allergy-beta" => Ok("AllergyIntolerance"),
        "fixture-observation-gamma" => Ok("Observation"),
        _ => Err(invalid()),
    }
}

/// The time axis uses only two true *documented source dates*. An Observation
/// without a date must stay in an undated section; never invent a timestamp.
pub(super) fn project_fictional_timeline(
    id: &'static str,
) -> Result<FictionalPatientTimeline, CommandError> {
    if id != PATIENT_ID {
        return Err(CommandError::new("unknown_patient_fixture"));
    }
    // The strict recursive JSON/known synthetic ID/relationship checks run
    // for every compiled source before any positive timeline is returned.
    for (fixture_id, _, bytes) in FIXTURES {
        structural::analyze_fixture(fixture_id, bytes)?;
    }
    let (patient, _) = document(PATIENT_ID)?;
    let (allergy, _) = document("fixture-allergy-beta")?;
    let (observation, observation_bytes) = document("fixture-observation-gamma")?;

    let dob = read_pinned_date(&patient, "/birthDate", "1970-01-01")?;
    let recorded = read_pinned_date(&allergy, "/recordedDate", "2026-01-01")?;
    // Explicitly reject newly added date fields until the closed-world
    // projection is reassessed; a missing date is not a dated event.
    if [
        "effectiveDateTime",
        "effectivePeriod",
        "issued",
        "date",
        "recordedDate",
    ]
    .into_iter()
    .any(|field| observation.get(field).is_some())
    {
        return Err(invalid());
    }
    let events = vec![
        dated_event(
            "fixture-allergy-beta",
            "fictional_recorded_date",
            "fictional-allergy-recorded",
            "Fictional allergy record date",
            recorded,
            "/recordedDate",
        )?,
        dated_event(
            PATIENT_ID,
            "fictional_demographic_date",
            "fictional-patient-dob",
            "Fictional example birth date",
            dob,
            "/birthDate",
        )?,
        FictionalTimelineEvent {
            event_id: "fictional-observation-undated",
            event_kind: "fictional_undated_observation",
            source_fixture_id: "fixture-observation-gamma",
            source_resource_type: "Observation",
            source_sha256_hex: sha256_hex(observation_bytes),
            source_byte_len: observation_bytes.len(),
            date: None,
            date_json_pointer: None,
            date_status: "not_present_in_source",
            label: "Fictional observation (no recorded event date)",
        },
    ];
    // Two documented dates in descending order, followed by an explicit
    // undated item. The ordering is source-derived, never clock-based.
    if events[0].date <= events[1].date {
        return Err(invalid());
    }
    Ok(FictionalPatientTimeline {
        contract: CONTRACT_TIMELINE,
        patient_fixture_id: PATIENT_ID,
        scope: TIMELINE_SCOPE,
        order: "dated_descending_then_undated",
        events,
        synthetic_only: true,
        fhir_semantics_validated: false,
        release_authorized: false,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_fictional_timeline_dates_and_hash_provenance() {
        let timeline = project_fictional_timeline(PATIENT_ID).unwrap();
        assert_eq!(timeline.contract, CONTRACT_TIMELINE);
        assert_eq!(timeline.patient_fixture_id, PATIENT_ID);
        assert_eq!(timeline.scope, TIMELINE_SCOPE);
        assert!(!timeline.fhir_semantics_validated);
        assert!(!timeline.release_authorized);
        assert!(timeline.synthetic_only);
        assert_eq!(timeline.events.len(), 3);
        assert_eq!(timeline.events[0].date.as_deref(), Some("2026-01-01"));
        assert_eq!(timeline.events[0].date_json_pointer, Some("/recordedDate"));
        assert_eq!(timeline.events[1].date.as_deref(), Some("1970-01-01"));
        assert_eq!(timeline.events[1].date_json_pointer, Some("/birthDate"));
        assert_eq!(timeline.events[2].date, None);
        assert_eq!(timeline.events[2].date_json_pointer, None);
        assert_eq!(timeline.events[2].date_status, "not_present_in_source");
        for event in &timeline.events {
            let (_, _, bytes) = fixture_entry(event.source_fixture_id).unwrap();
            assert_eq!(event.source_sha256_hex, sha256_hex(bytes));
            assert_eq!(event.source_byte_len, bytes.len());
        }
    }

    #[test]
    fn rejects_unknown_focus_instead_of_exposing_other_patient_data() {
        assert_eq!(
            project_fictional_timeline("fixture-allergy-beta")
                .unwrap_err()
                .code,
            "unknown_patient_fixture",
        );
    }

    #[test]
    fn calendar_parser_rejects_nonexistent_days_and_noncanonical_time() {
        for day in [
            "2025-02-29",
            "2026-13-01",
            "2026-00-01",
            "2026-04-31",
            "2026-01-00",
            "2026-01-32",
            "0000-01-01",
            "2026-1-01",
            "2026-01-01T12:00:00Z",
            "../2026-01-01",
            "",
        ] {
            assert!(!valid_yyyy_mm_dd(day), "unexpectedly allowed {day}");
        }
        for day in ["1970-01-01", "2024-02-29", "2000-02-29", "2026-01-01"] {
            assert!(valid_yyyy_mm_dd(day), "unexpectedly rejected {day}");
        }
    }

    #[test]
    fn rejects_replaced_or_invented_source_date() {
        let missing: Value = serde_json::json!({"resourceType":"Patient"});
        assert_eq!(
            read_pinned_date(&missing, "/birthDate", "1970-01-01")
                .unwrap_err()
                .code,
            "fictional_timeline_rejected"
        );
        let changed: Value = serde_json::json!({"birthDate":"1971-01-01"});
        assert_eq!(
            read_pinned_date(&changed, "/birthDate", "1970-01-01")
                .unwrap_err()
                .code,
            "fictional_timeline_rejected"
        );
        let impossible: Value = serde_json::json!({"birthDate":"2025-02-29"});
        assert!(read_pinned_date(&impossible, "/birthDate", "1970-01-01").is_err());
    }
}
