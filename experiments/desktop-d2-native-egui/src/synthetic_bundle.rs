//! Bounded, read-only structural FHIR Bundle browser for NONCLINICAL dummy IDs.
//! Arbitrary PHI and patient fields are NOT admissible. This is not FHIR R4
//! validation, a production IPC trust root, a medical record store, or a
//! substitute for the existing SHA-pinned AES-GCM Core readback transport.
use std::collections::{HashMap, HashSet};

use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

use crate::encrypted_readback::{FictionalReadbackLink, FictionalReadbackResource};

pub const MAX_SYNTHETIC_BUNDLE_BYTES: usize = 32_768;
pub const MAX_SYNTHETIC_BUNDLE_RESOURCES: usize = 48;

#[derive(Clone, Debug)]
pub struct SyntheticBundlePreview {
    pub resources: Vec<FictionalReadbackResource>,
    pub sha256: String,
    pub patient_count: usize,
}

fn object_with_exact_fields<'a>(
    value: &'a Value,
    allowed: &[&str],
) -> Result<&'a Map<String, Value>, &'static str> {
    let object = value.as_object().ok_or("synthetic_bundle_not_an_object")?;
    if object.len() != allowed.len() || !allowed.iter().all(|key| object.contains_key(*key)) {
        return Err("synthetic_bundle_unreviewed_fields");
    }
    Ok(object)
}

fn required_string<'a>(value: &'a Map<String, Value>, key: &str) -> Result<&'a str, &'static str> {
    value
        .get(key)
        .and_then(Value::as_str)
        .ok_or("synthetic_bundle_required_string_missing")
}

fn fake_uuid(value: &str) -> bool {
    value.len() == 45
        && value.starts_with("urn:uuid:00000000-0000-4000-8000-")
        && value.as_bytes()[33..].iter().all(u8::is_ascii_digit)
}

fn fake_id(value: &str, kind: &str) -> bool {
    let prefix = match kind {
        "Patient" => "fictional-patient-",
        "Encounter" => "fictional-encounter-",
        "Observation" => "fictional-observation-",
        _ => return false,
    };
    value.strip_prefix(prefix).is_some_and(|suffix| {
        suffix.len() == 3 && suffix.bytes().all(|c| c.is_ascii_digit()) && suffix != "000"
    })
}

fn reference(
    object: &Map<String, Value>,
    name: &str,
) -> Result<FictionalReadbackLink, &'static str> {
    let details = object_with_exact_fields(
        object
            .get(name)
            .ok_or("synthetic_bundle_reference_missing")?,
        &["reference"],
    )?;
    let target = required_string(details, "reference")?;
    if !fake_uuid(target) {
        return Err("synthetic_bundle_external_reference_refused");
    }
    Ok(FictionalReadbackLink {
        field: name.to_owned(),
        target: target.to_owned(),
    })
}

pub fn admit_bounded_synthetic_fhir_bundle(
    raw: &[u8],
) -> Result<SyntheticBundlePreview, &'static str> {
    if raw.is_empty() || raw.len() > MAX_SYNTHETIC_BUNDLE_BYTES {
        return Err("synthetic_bundle_bytes_out_of_bounds");
    }
    let value: Value = serde_json::from_slice(raw).map_err(|_| "synthetic_bundle_invalid_json")?;
    // Reject duplicate keys, extraneous whitespace, ambiguous encodings and
    // reordering instead of silently discarding potentially unsafe raw data.
    if serde_json::to_vec(&value).ok().as_deref() != Some(raw) {
        return Err("synthetic_bundle_noncanonical_or_duplicate_keys");
    }
    let root = object_with_exact_fields(&value, &["resourceType", "type", "meta", "entry"])?;
    if required_string(root, "resourceType")? != "Bundle"
        || required_string(root, "type")? != "collection"
    {
        return Err("synthetic_bundle_not_a_collection");
    }
    let meta = object_with_exact_fields(&root["meta"], &["tag"])?;
    let tags = meta["tag"]
        .as_array()
        .ok_or("synthetic_bundle_tag_missing")?;
    if tags.len() != 1 {
        return Err("synthetic_bundle_tag_count_refused");
    }
    let tag = object_with_exact_fields(&tags[0], &["code", "system"])?;
    if required_string(tag, "system")? != "https://medorigin.si/synthetic-only"
        || required_string(tag, "code")? != "fictional-structural-demo-no-phi"
    {
        return Err("synthetic_bundle_wrong_demo_tag");
    }

    let entries = root["entry"]
        .as_array()
        .ok_or("synthetic_bundle_entries_missing")?;
    if !(3..=MAX_SYNTHETIC_BUNDLE_RESOURCES).contains(&entries.len()) {
        return Err("synthetic_bundle_entry_count_refused");
    }
    let mut resources = Vec::with_capacity(entries.len());
    let mut urls = HashSet::with_capacity(entries.len());
    let mut ids = HashSet::with_capacity(entries.len());
    for entry in entries {
        let item = object_with_exact_fields(entry, &["fullUrl", "resource"])?;
        let full_url = required_string(item, "fullUrl")?;
        if !fake_uuid(full_url) || !urls.insert(full_url.to_owned()) {
            return Err("synthetic_bundle_invalid_or_duplicate_urn");
        }
        let data = item["resource"]
            .as_object()
            .ok_or("synthetic_bundle_resource_not_object")?;
        let kind = required_string(data, "resourceType")?;
        let id = required_string(data, "id")?;
        if !fake_id(id, kind) || !ids.insert((kind.to_owned(), id.to_owned())) {
            return Err("synthetic_bundle_invalid_or_duplicate_fake_id");
        }
        let fields: &[&str] = match kind {
            "Patient" => &["resourceType", "id"],
            "Encounter" => &["resourceType", "id", "subject"],
            "Observation" => &["resourceType", "id", "subject", "encounter"],
            _ => return Err("synthetic_bundle_unreviewed_resource_type"),
        };
        object_with_exact_fields(&item["resource"], fields)?;
        let mut links = Vec::new();
        if kind != "Patient" {
            links.push(reference(data, "subject")?);
        }
        if kind == "Observation" {
            links.push(reference(data, "encounter")?);
        }
        resources.push(FictionalReadbackResource {
            resource_type: kind.to_owned(),
            resource_id: id.to_owned(),
            full_url: full_url.to_owned(),
            links,
        });
    }

    let index_by_url: HashMap<&str, usize> = resources
        .iter()
        .enumerate()
        .map(|(idx, record)| (record.full_url.as_str(), idx))
        .collect();
    let mut patients = 0_usize;
    let mut encounters = 0_usize;
    let mut observations = 0_usize;
    for record in &resources {
        match record.resource_type.as_str() {
            "Patient" => patients += 1,
            "Encounter" => {
                encounters += 1;
                let patient = index_by_url
                    .get(record.links[0].target.as_str())
                    .and_then(|i| resources.get(*i))
                    .ok_or("synthetic_bundle_dangling_patient_reference")?;
                if patient.resource_type != "Patient" {
                    return Err("synthetic_bundle_subject_not_patient");
                }
            }
            "Observation" => {
                observations += 1;
                let patient = index_by_url
                    .get(record.links[0].target.as_str())
                    .and_then(|i| resources.get(*i))
                    .ok_or("synthetic_bundle_dangling_patient_reference")?;
                let encounter = index_by_url
                    .get(record.links[1].target.as_str())
                    .and_then(|i| resources.get(*i))
                    .ok_or("synthetic_bundle_dangling_encounter_reference")?;
                if patient.resource_type != "Patient"
                    || encounter.resource_type != "Encounter"
                    || encounter.links[0].target != patient.full_url
                {
                    return Err("synthetic_bundle_cross_patient_reference_refused");
                }
            }
            _ => return Err("synthetic_bundle_unreviewed_resource_type"),
        }
    }
    if patients == 0 || patients > 16 || encounters == 0 || observations == 0 {
        return Err("synthetic_bundle_patient_graph_counts_refused");
    }
    let digest = Sha256::digest(raw)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect::<String>();
    Ok(SyntheticBundlePreview {
        resources,
        sha256: digest,
        patient_count: patients,
    })
}

impl SyntheticBundlePreview {
    pub fn index_for(&self, urn: &str) -> Option<usize> {
        self.resources
            .iter()
            .position(|record| record.full_url == urn)
    }

    pub fn owner_patient(&self, index: usize) -> Option<usize> {
        let record = self.resources.get(index)?;
        if record.resource_type == "Patient" {
            return Some(index);
        }
        self.index_for(&record.links.first()?.target)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const DEMO: &[u8] = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");

    fn changed(mut update: impl FnMut(&mut Value)) -> Vec<u8> {
        let mut source: Value = serde_json::from_slice(DEMO).unwrap();
        update(&mut source);
        serde_json::to_vec(&source).unwrap()
    }

    #[test]
    fn forty_eight_records_and_sixteen_patients_are_bounded_not_three_fixture_ids() {
        let mut entries = Vec::new();
        let uuid = |number: usize| format!("urn:uuid:00000000-0000-4000-8000-{number:012}");
        for patient in 1..=16 {
            let patient_url = uuid(patient);
            let encounter_url = uuid(patient + 16);
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
                "fullUrl": uuid(patient + 32),
                "resource":{"id":format!("fictional-observation-{patient:03}"),"resourceType":"Observation",
                    "subject":{"reference":patient_url},"encounter":{"reference":encounter_url}}
            }));
        }
        let mut document = serde_json::json!({
            "entry": entries,
            "meta":{"tag":[{"code":"fictional-structural-demo-no-phi",
                "system":"https://medorigin.si/synthetic-only"}]},
            "resourceType":"Bundle",
            "type":"collection"
        });
        let bytes = serde_json::to_vec(&document).unwrap();
        let valid = admit_bounded_synthetic_fhir_bundle(&bytes).unwrap();
        assert_eq!(valid.resources.len(), MAX_SYNTHETIC_BUNDLE_RESOURCES);
        assert_eq!(valid.patient_count, 16);
        assert_eq!(valid.owner_patient(47), Some(45));
        document["entry"]
            .as_array_mut()
            .unwrap()
            .push(serde_json::json!({
                "fullUrl": uuid(49),
                "resource":{"id":"fictional-observation-017","resourceType":"Observation",
                    "subject":{"reference":uuid(1)},"encounter":{"reference":uuid(17)}}
            }));
        assert!(
            admit_bounded_synthetic_fhir_bundle(&serde_json::to_vec(&document).unwrap()).is_err()
        );
    }

    #[test]
    fn eight_fictional_records_span_two_isolated_patient_graphs() {
        let preview = admit_bounded_synthetic_fhir_bundle(DEMO).unwrap();
        assert_eq!(preview.resources.len(), 8);
        assert_eq!(preview.patient_count, 2);
        assert_eq!(preview.sha256.len(), 64);
        assert_eq!(preview.owner_patient(0), Some(0));
        assert_eq!(preview.owner_patient(1), Some(0));
        assert_eq!(preview.owner_patient(2), Some(0));
        assert_eq!(preview.owner_patient(4), Some(4));
        assert_eq!(preview.owner_patient(5), Some(4));
        assert_eq!(preview.owner_patient(7), Some(4));
        assert_eq!(preview.owner_patient(usize::MAX), None);
        assert_eq!(preview.index_for(&preview.resources[7].full_url), Some(7));
        assert_eq!(preview.index_for("urn:uuid:absent"), None);
    }

    #[test]
    fn rejects_noncanonical_duplicate_or_untrusted_metadata() {
        assert!(admit_bounded_synthetic_fhir_bundle(b"").is_err());
        assert!(
            admit_bounded_synthetic_fhir_bundle(&vec![b'x'; MAX_SYNTHETIC_BUNDLE_BYTES + 1])
                .is_err()
        );
        assert!(admit_bounded_synthetic_fhir_bundle(&[DEMO, b" "].concat()).is_err());
        assert!(admit_bounded_synthetic_fhir_bundle(&[b"\n", DEMO].concat()).is_err());
        let duplicate = String::from_utf8_lossy(DEMO)
            .replacen("{\"entry\"", "{\"type\":\"collection\",\"entry\"", 1)
            .into_bytes();
        assert!(admit_bounded_synthetic_fhir_bundle(&duplicate).is_err());
        for modified in [
            changed(|v| v["meta"]["tag"][0]["code"] = "real-patient".into()),
            changed(|v| v["type"] = "transaction".into()),
            changed(|v| v["resourceType"] = "Patient".into()),
            changed(|v| v["release_authorized"] = true.into()),
            changed(|v| v["entry"][0]["resource"]["name"] = "PHI".into()),
            changed(|v| v["entry"][0]["resource"]["birthDate"] = "1990-01-01".into()),
            changed(|v| v["entry"][0]["resource"]["telecom"] = "unsafe".into()),
            changed(|v| v["entry"][0]["resource"]["text"] = "notes".into()),
            changed(|v| v["entry"][0]["resource"]["id"] = "patient-real-001".into()),
            changed(|v| v["entry"][0]["resource"]["id"] = "fictional-patient-000".into()),
        ] {
            assert!(admit_bounded_synthetic_fhir_bundle(&modified).is_err());
        }
    }

    #[test]
    fn rejects_duplicate_keys_and_external_or_mismatched_graph_edges() {
        for modified in [
            changed(|v| {
                let x = v["entry"][0]["fullUrl"].clone();
                v["entry"][1]["fullUrl"] = x;
            }),
            changed(|v| {
                let x = v["entry"][5]["resource"]["id"].clone();
                v["entry"][1]["resource"]["id"] = x;
            }),
            changed(|v| {
                v["entry"][1]["resource"]["subject"]["reference"] =
                    "https://example.com/Patient/1".into()
            }),
            changed(|v| {
                v["entry"][1]["resource"]["subject"]["reference"] =
                    "urn:uuid:00000000-0000-4000-8000-000000000099".into()
            }),
            changed(|v| {
                let x = v["entry"][5]["fullUrl"].clone();
                v["entry"][2]["resource"]["encounter"]["reference"] = x;
            }),
            changed(|v| {
                let x = v["entry"][4]["fullUrl"].clone();
                v["entry"][2]["resource"]["subject"]["reference"] = x;
            }),
            changed(|v| v["entry"][2]["resource"]["code"] = "clinical".into()),
            changed(|v| v["entry"][2]["resource"]["resourceType"] = "MedicationRequest".into()),
        ] {
            assert!(admit_bounded_synthetic_fhir_bundle(&modified).is_err());
        }
    }
}
