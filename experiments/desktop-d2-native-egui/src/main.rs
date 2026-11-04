// Adapted from emilk/eframe_template under Apache-2.0, see UPSTREAM-NOTICE.md.
// Native, offline-only developer preview. No network/process spawn/EHR/PHI.
// Optional one-shot synthetic stdin is a tight, untrusted source-hash admission.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::ffi::OsString;
use std::io::{self, Read};

use medorigin_desktop_d2_native_egui::MedOriginNativePreview;

const MAX_FICTIONAL_CORE_STDIN: usize = 2048;
const EXPLICIT_SYNTHETIC_CORE_FLAG: &str = "--synthetic-core-stdin";

/// Only this opt-in command-line switch permits reading a finite stdin
/// synthetic Core report. Default desktop launch does not read stdin at all.
/// No file path, subprocess, socket, HTTP, arbitrary FHIR input or model call.
fn make_app<R: Read>(args: &[OsString], reader: R) -> Result<MedOriginNativePreview, io::Error> {
    if args.is_empty() {
        return Ok(MedOriginNativePreview::default());
    }
    if args.len() != 1 || args[0] != EXPLICIT_SYNTHETIC_CORE_FLAG {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "unapproved_d2_native_startup_argument",
        ));
    }
    // 2049 bytes are sufficient to detect oversized source data, without
    // reading an unbounded incoming payload or buffering clinical documents.
    let mut bytes = Vec::with_capacity(512);
    reader
        .take(MAX_FICTIONAL_CORE_STDIN as u64 + 1)
        .read_to_end(&mut bytes)?;
    if bytes.is_empty() || bytes.len() > MAX_FICTIONAL_CORE_STDIN {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "unapproved_d2_synthetic_core_stdin_size",
        ));
    }
    MedOriginNativePreview::from_one_time_fictional_core_stdin(&bytes).map_err(|_| {
        io::Error::new(
            io::ErrorKind::InvalidData,
            "unapproved_d2_synthetic_core_stdin_report",
        )
    })
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<OsString> = std::env::args_os().skip(1).collect();
    let app = make_app(&args, io::stdin().lock())?;
    let options = eframe::NativeOptions {
        viewport: eframe::egui::ViewportBuilder::default()
            .with_inner_size([920.0, 600.0])
            .with_min_inner_size([700.0, 480.0]),
        ..Default::default()
    };
    eframe::run_native(
        "MedOrigin Native Rust — Synthetic Experiment (NO RELEASE)",
        options,
        Box::new(move |_cc| Ok(Box::new(app))),
    )?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    const CORE_KNOWN: &[u8] = include_bytes!("../fixtures/core/known-structure-definition.json");
    const CORE_NEGATIVE: &[u8] = include_bytes!("../fixtures/core/unknown-fictional-negative.json");

    #[test]
    fn no_switch_never_reads_stdin_and_starts_without_external_core_claim() {
        struct RefuseRead;
        impl Read for RefuseRead {
            fn read(&mut self, _buf: &mut [u8]) -> io::Result<usize> {
                panic!("ordinary GUI launch must not read external stdin")
            }
        }
        let app = make_app(&[], RefuseRead).expect("default source-only GUI");
        assert!(!app.has_external_fictional_core_stdin());
    }

    #[test]
    fn source_compiled_synthetic_core_reports_are_only_two_startup_inputs() {
        for raw in [CORE_KNOWN, CORE_NEGATIVE] {
            let app = make_app(
                &[OsString::from(EXPLICIT_SYNTHETIC_CORE_FLAG)],
                Cursor::new(raw),
            )
            .expect("exact one-time fictional Core report");
            assert!(app.has_external_fictional_core_stdin());
        }
    }

    #[test]
    fn malformed_oversized_and_spoofed_valid_stdin_fail_before_gui() {
        let mut spoofed = CORE_KNOWN.to_vec();
        let position = spoofed
            .windows("not_validated".len())
            .position(|w| w == b"not_validated")
            .unwrap();
        spoofed[position] = b'x';
        for candidate in [
            Vec::new(),
            b"{}".to_vec(),
            spoofed,
            vec![b'X'; MAX_FICTIONAL_CORE_STDIN + 1],
            [CORE_KNOWN, b" "].concat(),
        ] {
            assert!(
                make_app(
                    &[OsString::from(EXPLICIT_SYNTHETIC_CORE_FLAG)],
                    Cursor::new(candidate),
                )
                .is_err(),
                "invalid stdin must fail closed"
            );
        }
    }

    #[test]
    fn unknown_startup_switches_are_refused_without_reading_stdin() {
        for args in [
            vec![OsString::from("--clinical-import")],
            vec![
                OsString::from(EXPLICIT_SYNTHETIC_CORE_FLAG),
                OsString::from("/tmp/patient"),
            ],
            vec![OsString::from("--file"), OsString::from("/tmp/patient")],
        ] {
            assert!(make_app(&args, io::empty()).is_err());
        }
    }
}
