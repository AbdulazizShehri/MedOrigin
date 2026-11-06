//! A user-initiated local drag-and-drop file admission boundary for
//! strictly fictional, read-only FHIR-shaped Bundles. Never accepts PHI.
use std::fs::{self, File};
use std::io::Read;
use std::path::{Component, Path};

use crate::synthetic_bundle::{
    MAX_SYNTHETIC_BUNDLE_BYTES, SyntheticBundlePreview, admit_bounded_synthetic_fhir_bundle,
};

#[cfg(windows)]
const REPARSE_POINT: u32 = 0x400;

/// Read only a single explicitly dropped local file, limit it before allocation,
/// and admit only the exact synthetic-only FHIR Bundle schema. No filenames,
/// paths, record values, or rejected file bytes ever appear in error messages.
pub fn read_dropped_fictional_bundle(path: &Path) -> Result<SyntheticBundlePreview, &'static str> {
    if path.extension().and_then(|ext| ext.to_str()) != Some("json") {
        return Err("local_fictional_bundle_json_extension_required");
    }
    if !path.is_absolute() {
        return Err("local_fictional_bundle_absolute_path_required");
    }
    #[cfg(windows)]
    if !matches!(
        path.components().next(),
        Some(Component::Prefix(prefix)) if matches!(prefix.kind(), std::path::Prefix::Disk(_))
    ) {
        return Err("local_fictional_bundle_non_drive_path_refused");
    }
    #[cfg(not(windows))]
    if path
        .components()
        .any(|part| matches!(part, Component::Prefix(_)))
    {
        return Err("local_fictional_bundle_invalid_path_prefix");
    }

    // Refuse symlinked/junction/reparse ancestors, including on Windows 3.11
    // hosts that do not have Python's Path.is_junction method.
    for ancestor in path.ancestors() {
        let meta = fs::symlink_metadata(ancestor)
            .map_err(|_| "local_fictional_bundle_path_unavailable")?;
        if meta.file_type().is_symlink() {
            return Err("local_fictional_bundle_symlink_refused");
        }
        #[cfg(windows)]
        {
            use std::os::windows::fs::MetadataExt;
            if meta.file_attributes() & REPARSE_POINT != 0 {
                return Err("local_fictional_bundle_reparse_refused");
            }
        }
    }
    let meta = fs::symlink_metadata(path).map_err(|_| "local_fictional_bundle_missing")?;
    if !meta.is_file() || meta.len() == 0 || meta.len() > MAX_SYNTHETIC_BUNDLE_BYTES as u64 {
        return Err("local_fictional_bundle_size_or_filetype_refused");
    }
    let mut reader = File::open(path).map_err(|_| "local_fictional_bundle_open_refused")?;
    let mut data = Vec::with_capacity(meta.len() as usize);
    reader
        .by_ref()
        .take(MAX_SYNTHETIC_BUNDLE_BYTES as u64 + 1)
        .read_to_end(&mut data)
        .map_err(|_| "local_fictional_bundle_read_refused")?;
    if data.len() != meta.len() as usize {
        return Err("local_fictional_bundle_changed_during_read");
    }
    // This existing parser enforces canonical JSON bytes, exact synthetic tag,
    // fake Patient/Encounter/Observation IDs, no names/ages/values, bounded
    // resource count, and valid within-patient references.
    admit_bounded_synthetic_fhir_bundle(&data)
        .map_err(|_| "local_fictional_bundle_not_canonical_synthetic_no_phi")
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicU64, Ordering};

    static NEXT_TEST: AtomicU64 = AtomicU64::new(0);

    fn temp_json(data: &[u8]) -> std::path::PathBuf {
        let id = NEXT_TEST.fetch_add(1, Ordering::Relaxed);
        let file = std::env::temp_dir().join(format!(
            "medorigin-d2-local-bundle-test-{:?}-{id}.json",
            std::thread::current().id()
        ));
        fs::write(&file, data).expect("write isolated synthetic test");
        file
    }

    #[test]
    fn canonical_fake_bundle_is_admitted_read_only() {
        let raw = include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json");
        let path = temp_json(raw);
        let result = read_dropped_fictional_bundle(&path);
        fs::remove_file(path).unwrap();
        let parsed = result.expect("source-approved fake bundle");
        assert!(parsed.patient_count >= 1);
        assert!(parsed.resources.len() >= 3);
    }

    #[test]
    fn rejects_personal_patient_content() {
        let raw = br#"{"resourceType":"Patient","id":"person-001","name":[{"family":"Real"}]}"#;
        let path = temp_json(raw);
        assert!(matches!(
            read_dropped_fictional_bundle(&path),
            Err("local_fictional_bundle_not_canonical_synthetic_no_phi")
        ));
        fs::remove_file(path).unwrap();
    }

    #[test]
    fn rejects_empty_and_oversized_files_without_accepting_data() {
        for bytes in [Vec::new(), vec![b'x'; MAX_SYNTHETIC_BUNDLE_BYTES + 1]] {
            let path = temp_json(&bytes);
            assert!(matches!(
                read_dropped_fictional_bundle(&path),
                Err("local_fictional_bundle_size_or_filetype_refused")
            ));
            fs::remove_file(path).unwrap();
        }
    }

    #[test]
    fn rejects_non_json_extension_and_relative_paths() {
        assert!(matches!(
            read_dropped_fictional_bundle(Path::new("relative.json")),
            Err("local_fictional_bundle_absolute_path_required")
        ));
        let path = std::env::temp_dir().join(format!(
            "medorigin-d2-non-json-file-{:?}.txt",
            std::thread::current().id()
        ));
        fs::write(&path, b"not a JSON file").unwrap();
        assert!(matches!(
            read_dropped_fictional_bundle(&path),
            Err("local_fictional_bundle_json_extension_required")
        ));
        fs::remove_file(path).unwrap();
    }

    #[test]
    fn rejects_almost_canonical_bundle_with_extra_newline() {
        let mut raw =
            include_bytes!("../fixtures/core/synthetic-multipatient-fhir-bundle.json").to_vec();
        raw.push(b'\n');
        let path = temp_json(&raw);
        assert!(matches!(
            read_dropped_fictional_bundle(&path),
            Err("local_fictional_bundle_not_canonical_synthetic_no_phi")
        ));
        fs::remove_file(path).unwrap();
    }

    #[cfg(unix)]
    #[test]
    fn rejects_symlinked_file_without_following_it() {
        use std::os::unix::fs::symlink;
        let path = temp_json(b"{}");
        let link = path.with_extension("link.json");
        symlink(&path, &link).unwrap();
        assert!(matches!(
            read_dropped_fictional_bundle(&link),
            Err("local_fictional_bundle_symlink_refused")
        ));
        fs::remove_file(link).unwrap();
        fs::remove_file(path).unwrap();
    }
}
