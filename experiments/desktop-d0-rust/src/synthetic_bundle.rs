//! Offline fictional Bundle graph checks on fixed compiled fixtures only.
//! This is NOT full FHIR conformance, terminology or clinical validation.
use std::collections::HashSet;

use serde_json::Value;

pub(crate) fn inspect_fictional_bundle(raw: &[u8]) -> &'static str {
    let Ok(value) = serde_json::from_slice::<Value>(raw) else {
        return "INVALID_JSON";
    };
    if value.get("resourceType").and_then(Value::as_str) != Some("Bundle")
        || value.get("id").and_then(Value::as_str) != Some("synthetic-bundle")
    {
        return "INVALID_BUNDLE_ENVELOPE";
    }
    if value.get("type").and_then(Value::as_str) != Some("collection") {
        return "INVALID_BUNDLE_TYPE";
    }
    let Some(entries) = value.get("entry").and_then(Value::as_array) else {
        return "INVALID_BUNDLE_ENVELOPE";
    };
    // Deliberately require exactly one fictional Patient and one Observation.
    if entries.len() != 2 {
        return "INVALID_BUNDLE_ENVELOPE";
    }

    let mut urls = HashSet::new();
    let mut patient_seen = false;
    let mut observation_seen = false;
    let mut reference: Option<&str> = None;
    for entry in entries {
        let Some(url) = entry.get("fullUrl").and_then(Value::as_str) else {
            return "INVALID_BUNDLE_ENVELOPE";
        };
        // Only local synthetic URN names, never a dereferenceable URL.
        if !matches!(
            url,
            "urn:uuid:00000000-0000-4000-8000-000000000001"
                | "urn:uuid:00000000-0000-4000-8000-000000000002"
        ) {
            return "INVALID_BUNDLE_ENVELOPE";
        }
        if !urls.insert(url) {
            return "DUPLICATE_ENTRY";
        }
        let Some(resource) = entry.get("resource") else {
            return "INVALID_BUNDLE_ENVELOPE";
        };
        match resource.get("resourceType").and_then(Value::as_str) {
            Some("Patient") => {
                if patient_seen
                    || url != "urn:uuid:00000000-0000-4000-8000-000000000001"
                    || resource.get("id").and_then(Value::as_str) != Some("synthetic")
                    || resource.get("active").and_then(Value::as_bool) != Some(true)
                {
                    return "INVALID_BUNDLE_ENVELOPE";
                }
                patient_seen = true;
            }
            Some("Observation") => {
                if observation_seen
                    || url != "urn:uuid:00000000-0000-4000-8000-000000000002"
                    || resource.get("id").and_then(Value::as_str) != Some("synthetic-observation")
                    || resource.get("status").and_then(Value::as_str) != Some("final")
                    || resource
                        .pointer("/code/coding/0/system")
                        .and_then(Value::as_str)
                        != Some("urn:synthetic:code")
                    || resource
                        .pointer("/code/coding/0/code")
                        .and_then(Value::as_str)
                        != Some("fictional-measurement")
                    || resource
                        .pointer("/valueQuantity/value")
                        .and_then(Value::as_i64)
                        != Some(37)
                    || resource
                        .pointer("/valueQuantity/unit")
                        .and_then(Value::as_str)
                        != Some("fictional")
                {
                    return "INVALID_BUNDLE_ENVELOPE";
                }
                observation_seen = true;
                reference = resource
                    .pointer("/subject/reference")
                    .and_then(Value::as_str);
            }
            _ => return "INVALID_BUNDLE_ENVELOPE",
        }
    }
    if !patient_seen || !observation_seen {
        return "INVALID_BUNDLE_ENVELOPE";
    }
    if reference != Some("Patient/synthetic") {
        return "INVALID_REFERENCE";
    }
    "BUNDLE_GRAPH_OK"
}

#[cfg(test)]
mod tests {
    use super::inspect_fictional_bundle;
    use serde_json::{Value, json};

    #[test]
    fn rejects_manipulated_local_graph_instead_of_dereferencing() {
        let raw = include_bytes!("../fixtures/bundle-valid.json");
        let mut parsed: Value = serde_json::from_slice(raw).unwrap();
        assert_eq!(inspect_fictional_bundle(raw), "BUNDLE_GRAPH_OK");
        parsed["entry"][1]["resource"]["subject"]["reference"] =
            json!("https://example.org/Patient/real");
        assert_eq!(
            inspect_fictional_bundle(&serde_json::to_vec(&parsed).unwrap()),
            "INVALID_REFERENCE"
        );
        parsed["entry"][1]["resource"]["subject"]["reference"] = json!("Patient/synthetic");
        parsed["entry"][1]["fullUrl"] = json!("https://example.org/Observation/real");
        assert_eq!(
            inspect_fictional_bundle(&serde_json::to_vec(&parsed).unwrap()),
            "INVALID_BUNDLE_ENVELOPE"
        );
        parsed["entry"][1]["fullUrl"] = parsed["entry"][0]["fullUrl"].clone();
        assert_eq!(
            inspect_fictional_bundle(&serde_json::to_vec(&parsed).unwrap()),
            "DUPLICATE_ENTRY"
        );
    }
}
