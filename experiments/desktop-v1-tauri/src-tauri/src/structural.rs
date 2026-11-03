//! Strict bounded JSON *subset* inspection for compile-time fictional fixtures.
//! Never a FHIR R4 validator, real data reader, or clinical semantic gate.
//! Duplicate keys at *any* nesting depth are refused before inspecting shape.

use serde::de::{self, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Deserializer, Serialize};
use serde_json::Value;
use std::collections::HashSet;
use std::fmt;

use super::{CommandError, MAX_INPUT_BYTES, fixture_entry, sha256_hex};

pub(super) const CONTRACT_STRUCTURE: &str = "medorigin-fictional-structure-subset-v1";
const MAX_REFERENCES: usize = 64;
const MAX_BUNDLE_ENTRIES: usize = 16;
const BUNDLE_URN_PREFIX: &str = "urn:example:invalid:medorigin:";

/// The evidence is explicitly an intentionally narrow, fictional-only subset.
#[derive(Serialize, Debug)]
#[serde(deny_unknown_fields)]
pub(super) struct FixtureStructuralEvidence {
    pub contract: &'static str,
    pub fixture_id: &'static str,
    pub resource_type: &'static str,
    pub resource_id: &'static str,
    pub byte_len: usize,
    pub sha256_hex: String,
    pub reference_count: usize,
    pub bundle_entry_count: usize,
    pub duplicate_keys_rejected: bool,
    pub structural_subset_checked: bool,
    pub fhir_semantics_validated: bool,
    pub synthetic_only: bool,
    pub release_authorized: bool,
}

struct UniqueJson(Value);

struct UniqueJsonVisitor;

impl<'de> Deserialize<'de> for UniqueJson {
    fn deserialize<D: Deserializer<'de>>(deserializer: D) -> Result<Self, D::Error> {
        deserializer.deserialize_any(UniqueJsonVisitor)
    }
}

impl<'de> Visitor<'de> for UniqueJsonVisitor {
    type Value = UniqueJson;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("JSON with unique keys at every object depth")
    }

    fn visit_bool<E: de::Error>(self, value: bool) -> Result<Self::Value, E> {
        Ok(UniqueJson(Value::Bool(value)))
    }

    fn visit_i64<E: de::Error>(self, value: i64) -> Result<Self::Value, E> {
        Ok(UniqueJson(Value::Number(value.into())))
    }

    fn visit_u64<E: de::Error>(self, value: u64) -> Result<Self::Value, E> {
        Ok(UniqueJson(Value::Number(value.into())))
    }

    fn visit_f64<E: de::Error>(self, value: f64) -> Result<Self::Value, E> {
        serde_json::Number::from_f64(value)
            .map(|number| UniqueJson(Value::Number(number)))
            .ok_or_else(|| E::custom("non-finite number"))
    }

    fn visit_str<E: de::Error>(self, value: &str) -> Result<Self::Value, E> {
        Ok(UniqueJson(Value::String(value.to_owned())))
    }

    fn visit_string<E: de::Error>(self, value: String) -> Result<Self::Value, E> {
        Ok(UniqueJson(Value::String(value)))
    }

    fn visit_unit<E: de::Error>(self) -> Result<Self::Value, E> {
        Ok(UniqueJson(Value::Null))
    }

    fn visit_none<E: de::Error>(self) -> Result<Self::Value, E> {
        Ok(UniqueJson(Value::Null))
    }

    fn visit_seq<A: SeqAccess<'de>>(self, mut sequence: A) -> Result<Self::Value, A::Error> {
        let mut values = Vec::new();
        while let Some(value) = sequence.next_element::<UniqueJson>()? {
            values.push(value.0);
        }
        Ok(UniqueJson(Value::Array(values)))
    }

    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Self::Value, A::Error> {
        let mut values = serde_json::Map::new();
        while let Some((key, value)) = map.next_entry::<String, UniqueJson>()? {
            if values.contains_key(&key) {
                return Err(de::Error::custom("duplicate JSON member"));
            }
            values.insert(key, value.0);
        }
        Ok(UniqueJson(Value::Object(values)))
    }
}

fn invalid() -> CommandError {
    CommandError::new("structural_subset_rejected")
}

fn known_kind(id: &str) -> Option<&'static str> {
    match id {
        "fixture-patient-alpha" => Some("Patient"),
        "fixture-allergy-beta" => Some("AllergyIntolerance"),
        "fixture-observation-gamma" => Some("Observation"),
        "fixture-bundle-delta" => Some("Bundle"),
        _ => None,
    }
}

fn string_field<'a>(value: &'a Value, key: &str) -> Result<&'a str, CommandError> {
    value.get(key).and_then(Value::as_str).ok_or_else(invalid)
}

fn collect_references(value: &Value, refs: &mut Vec<String>) -> Result<(), CommandError> {
    match value {
        Value::Object(object) => {
            for (key, item) in object {
                if key == "reference" {
                    let text = item.as_str().ok_or_else(invalid)?;
                    if refs.len() >= MAX_REFERENCES || text.len() > 128 {
                        return Err(invalid());
                    }
                    refs.push(text.to_owned());
                } else {
                    collect_references(item, refs)?;
                }
            }
        }
        Value::Array(array) => {
            for item in array {
                collect_references(item, refs)?;
            }
        }
        _ => {}
    }
    Ok(())
}

fn check_reference(reference: &str) -> Result<(), CommandError> {
    let (kind, id) = reference.split_once('/').ok_or_else(invalid)?;
    if id.contains('/') || known_kind(id) != Some(kind) || fixture_entry(id).is_none() {
        return Err(invalid());
    }
    Ok(())
}

fn check_bundle_entries(value: &Value) -> Result<usize, CommandError> {
    let entries = value
        .get("entry")
        .and_then(Value::as_array)
        .ok_or_else(invalid)?;
    if entries.is_empty() || entries.len() > MAX_BUNDLE_ENTRIES {
        return Err(invalid());
    }
    let mut seen_urns = HashSet::new();
    let mut seen_ids = HashSet::new();
    for entry in entries {
        let resource = entry.get("resource").ok_or_else(invalid)?;
        let id = string_field(resource, "id")?;
        let kind = string_field(resource, "resourceType")?;
        let urn = string_field(entry, "fullUrl")?;
        if known_kind(id) != Some(kind)
            || fixture_entry(id).is_none()
            || id == "fixture-bundle-delta"
            || urn != format!("{BUNDLE_URN_PREFIX}{id}")
            || !seen_urns.insert(urn)
            || !seen_ids.insert(id)
        {
            return Err(invalid());
        }
    }
    Ok(entries.len())
}

/// Checked only against the four immutable, fictional fixture identities.
/// This does not validate the FHIR profile, value sets, codes or clinical meaning.
pub(super) fn analyze_fixture(
    fixture_id: &'static str,
    bytes: &[u8],
) -> Result<FixtureStructuralEvidence, CommandError> {
    if bytes.len() > MAX_INPUT_BYTES {
        return Err(CommandError::new("input_limit_exceeded"));
    }
    let document = serde_json::from_slice::<UniqueJson>(bytes)
        .map_err(|_| invalid())?
        .0;
    let expected = known_kind(fixture_id).ok_or_else(invalid)?;
    let resource_type = string_field(&document, "resourceType")?;
    let resource_id = string_field(&document, "id")?;
    let note = string_field(&document, "note")?;
    if resource_type != expected || resource_id != fixture_id || !note.contains("FICTIONAL") {
        return Err(invalid());
    }

    let mut references = Vec::new();
    collect_references(&document, &mut references)?;
    for reference in &references {
        check_reference(reference)?;
    }
    let bundle_entry_count = if resource_type == "Bundle" {
        if string_field(&document, "type")? != "collection" {
            return Err(invalid());
        }
        check_bundle_entries(&document)?
    } else {
        if document.get("entry").is_some() {
            return Err(invalid());
        }
        0
    };
    // This check ensures the expected synthetic cross-resource relationships.
    if resource_type == "AllergyIntolerance"
        && string_field(document.get("patient").ok_or_else(invalid)?, "reference")?
            != "Patient/fixture-patient-alpha"
    {
        return Err(invalid());
    }
    if resource_type == "Observation"
        && string_field(document.get("subject").ok_or_else(invalid)?, "reference")?
            != "Patient/fixture-patient-alpha"
    {
        return Err(invalid());
    }

    Ok(FixtureStructuralEvidence {
        contract: CONTRACT_STRUCTURE,
        fixture_id,
        resource_type: expected,
        resource_id: fixture_id,
        byte_len: bytes.len(),
        sha256_hex: sha256_hex(bytes),
        reference_count: references.len(),
        bundle_entry_count,
        duplicate_keys_rejected: true,
        structural_subset_checked: true,
        fhir_semantics_validated: false,
        synthetic_only: true,
        release_authorized: false,
    })
}

#[cfg(test)]
mod tests {
    use super::super::FIXTURES;
    use super::*;

    #[test]
    fn four_pinned_fictional_fixtures_pass_subset_not_fhir_validation() {
        for (id, _, bytes) in FIXTURES {
            let proof = analyze_fixture(id, bytes).unwrap();
            assert_eq!(proof.fixture_id, *id);
            assert_eq!(proof.resource_type, known_kind(id).unwrap());
            assert_eq!(proof.sha256_hex, sha256_hex(bytes));
            assert_eq!(proof.byte_len, bytes.len());
            assert!(proof.duplicate_keys_rejected);
            assert!(proof.structural_subset_checked);
            assert!(!proof.fhir_semantics_validated);
            assert!(proof.synthetic_only);
            assert!(!proof.release_authorized);
        }
    }

    #[test]
    fn rejects_nested_duplicate_keys_before_structural_check() {
        let cases = [
            r#"{"resourceType":"Patient","id":"fixture-patient-alpha","note":"FICTIONAL","name":[{"family":"A","family":"B"}]}"#,
            r#"{"resourceType":"Patient","resourceType":"Patient","id":"fixture-patient-alpha","note":"FICTIONAL"}"#,
            r#"{"resourceType":"Patient","id":"fixture-patient-alpha","note":"FICTIONAL","name":[{"family":"A","nested":{"x":1,"x":2}}]}"#,
        ];
        for candidate in cases {
            let err = analyze_fixture("fixture-patient-alpha", candidate.as_bytes()).unwrap_err();
            assert_eq!(err.code, "structural_subset_rejected");
        }
    }

    #[test]
    fn rejects_incorrect_identity_and_broken_cross_resource_reference() {
        for candidate in [
            r#"{"resourceType":"Observation","id":"wrong-id","note":"FICTIONAL","subject":{"reference":"Patient/fixture-patient-alpha"}}"#,
            r#"{"resourceType":"Observation","id":"fixture-observation-gamma","note":"FICTIONAL","subject":{"reference":"Patient/private-patient"}}"#,
            r#"{"resourceType":"Observation","id":"fixture-observation-gamma","note":"FICTIONAL","subject":{"reference":"https://example.invalid/PHI"}}"#,
        ] {
            let err =
                analyze_fixture("fixture-observation-gamma", candidate.as_bytes()).unwrap_err();
            assert_eq!(err.code, "structural_subset_rejected");
            assert!(
                !serde_json::to_string(&err)
                    .unwrap()
                    .contains("private-patient")
            );
        }
    }

    #[test]
    fn rejects_duplicate_bundle_entries_and_forged_full_url() {
        for candidate in [
            r#"{"resourceType":"Bundle","id":"fixture-bundle-delta","note":"FICTIONAL","type":"collection","entry":[{"fullUrl":"urn:example:invalid:medorigin:fixture-patient-alpha","resource":{"resourceType":"Patient","id":"fixture-patient-alpha"}},{"fullUrl":"urn:example:invalid:medorigin:fixture-patient-alpha","resource":{"resourceType":"Patient","id":"fixture-patient-alpha"}}]}"#,
            r#"{"resourceType":"Bundle","id":"fixture-bundle-delta","note":"FICTIONAL","type":"collection","entry":[{"fullUrl":"https://attacker.test","resource":{"resourceType":"Patient","id":"fixture-patient-alpha"}}]}"#,
        ] {
            assert_eq!(
                analyze_fixture("fixture-bundle-delta", candidate.as_bytes())
                    .unwrap_err()
                    .code,
                "structural_subset_rejected"
            );
        }
    }

    #[test]
    fn rejects_oversize_bytes_and_non_json() {
        assert_eq!(
            analyze_fixture("fixture-patient-alpha", &vec![b'0'; MAX_INPUT_BYTES + 1])
                .unwrap_err()
                .code,
            "input_limit_exceeded"
        );
        assert_eq!(
            analyze_fixture("fixture-patient-alpha", b"not a json document")
                .unwrap_err()
                .code,
            "structural_subset_rejected"
        );
    }
}
