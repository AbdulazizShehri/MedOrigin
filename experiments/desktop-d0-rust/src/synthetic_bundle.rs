//! Offline fictional Bundle graph checks on fixed compiled fixtures only.
//! This is NOT full FHIR conformance, terminology or clinical validation.
use std::collections::HashSet;
use std::fmt;

use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};

use serde_json::Value;

// serde_json::Value intentionally keeps the last occurrence of an object key.
// Check every nested object before using Value for security-relevant graph
// decisions; escaped JSON key names are decoded before duplicate comparison.
struct UniqueKeys;

impl<'de> DeserializeSeed<'de> for UniqueKeys {
    type Value = ();

    fn deserialize<D: de::Deserializer<'de>>(self, deserializer: D) -> Result<(), D::Error> {
        deserializer.deserialize_any(UniqueKeys)
    }
}

impl<'de> Visitor<'de> for UniqueKeys {
    type Value = ();

    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("JSON with no duplicate object keys")
    }

    fn visit_map<M: MapAccess<'de>>(self, mut map: M) -> Result<(), M::Error> {
        let mut keys = HashSet::new();
        while let Some(key) = map.next_key::<String>()? {
            if !keys.insert(key) {
                return Err(de::Error::custom("duplicate JSON object key"));
            }
            map.next_value_seed(UniqueKeys)?;
        }
        Ok(())
    }

    fn visit_seq<S: SeqAccess<'de>>(self, mut seq: S) -> Result<(), S::Error> {
        while seq.next_element_seed(UniqueKeys)?.is_some() {}
        Ok(())
    }

    fn visit_bool<E: de::Error>(self, _: bool) -> Result<(), E> {
        Ok(())
    }
    fn visit_i64<E: de::Error>(self, _: i64) -> Result<(), E> {
        Ok(())
    }
    fn visit_u64<E: de::Error>(self, _: u64) -> Result<(), E> {
        Ok(())
    }
    fn visit_f64<E: de::Error>(self, _: f64) -> Result<(), E> {
        Ok(())
    }
    fn visit_str<E: de::Error>(self, _: &str) -> Result<(), E> {
        Ok(())
    }
    fn visit_string<E: de::Error>(self, _: String) -> Result<(), E> {
        Ok(())
    }
    fn visit_unit<E: de::Error>(self) -> Result<(), E> {
        Ok(())
    }
}

pub(crate) fn reject_duplicate_object_keys(raw: &[u8]) -> Result<(), serde_json::Error> {
    let mut parser = serde_json::Deserializer::from_slice(raw);
    UniqueKeys.deserialize(&mut parser)?;
    parser.end()
}

pub(crate) fn inspect_fictional_bundle(raw: &[u8]) -> &'static str {
    if reject_duplicate_object_keys(raw).is_err() {
        return "INVALID_JSON";
    }
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
    let mut patient_full_url: Option<&str> = None;
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
                patient_full_url = Some(url);
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
    // Permit an exact synthetic relative reference OR a Bundle-local fullUrl
    // belonging to the patient entry. Never dereference URLs or resolve remotely.
    if reference != Some("Patient/synthetic") && reference != patient_full_url {
        return "INVALID_REFERENCE";
    }
    "BUNDLE_GRAPH_OK"
}

#[cfg(test)]
mod tests {
    use super::inspect_fictional_bundle;
    use serde_json::{Value, json};

    #[test]
    fn rejects_duplicate_json_keys_in_d2_copied_bundle_parser() {
        let raw = std::str::from_utf8(include_bytes!("../fixtures/bundle-valid.json")).unwrap();
        assert_eq!(inspect_fictional_bundle(raw.as_bytes()), "BUNDLE_GRAPH_OK");
        for (needle, replacement) in [
            (
                "\"resourceType\":\"Bundle\"",
                "\"resourceType\":\"Patient\",\"resourceType\":\"Bundle\"",
            ),
            (
                "\"resourceType\":\"Patient\"",
                "\"resourceType\":\"Observation\",\"resourceType\":\"Patient\"",
            ),
            (
                "\"resourceType\":\"Bundle\"",
                "\"\\u0072esourceType\":\"Patient\",\"resourceType\":\"Bundle\"",
            ),
        ] {
            let forged = raw.replacen(needle, replacement, 1);
            assert_ne!(forged, raw, "test fixture must contain target");
            assert_eq!(inspect_fictional_bundle(forged.as_bytes()), "INVALID_JSON");
        }
    }

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
