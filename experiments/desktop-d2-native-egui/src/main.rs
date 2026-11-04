// Adapted from emilk/eframe_template under Apache-2.0, see UPSTREAM-NOTICE.md.
// Native, offline-only developer preview. No network/process spawn/EHR/PHI.
// Optional one-shot synthetic stdin is a tight, untrusted source-hash admission.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::ffi::OsString;
use std::io::{self, Read};
use std::sync::mpsc::{self, RecvTimeoutError};
use std::time::Duration;

use medorigin_desktop_d2_native_egui::MedOriginNativePreview;

const MAX_FICTIONAL_CORE_STDIN: usize = 2048;
const EXPLICIT_SYNTHETIC_CORE_FLAG: &str = "--synthetic-core-stdin";
const EXPLICIT_SYNTHETIC_WORKSPACE_FLAG: &str = "--synthetic-workspace-receipt-stdin";
const EXPLICIT_SYNTHETIC_READBACK_FLAG: &str = "--synthetic-encrypted-readback-stdin";
const SYNTHETIC_CORE_STDIN_DEADLINE: Duration = Duration::from_secs(5);

/// Only this opt-in command-line switch permits reading a finite stdin
/// synthetic Core report. Default desktop launch does not read stdin at all.
/// No file path, subprocess, socket, HTTP, arbitrary FHIR input or model call.
fn make_app<R: Read + Send + 'static>(
    args: &[OsString],
    reader: R,
) -> Result<MedOriginNativePreview, io::Error> {
    make_app_with_deadline(args, reader, SYNTHETIC_CORE_STDIN_DEADLINE)
}

/// A malicious/abandoned pipe must not block native startup indefinitely.
/// The worker thread only reads the already-open stdin stream. It never
/// spawns processes or touches the filesystem or network. On timeout, the
/// GUI process exits before creating a window; the blocked reader is ended
/// with process termination (no background service persists).
fn make_app_with_deadline<R: Read + Send + 'static>(
    args: &[OsString],
    reader: R,
    deadline: Duration,
) -> Result<MedOriginNativePreview, io::Error> {
    if args.is_empty() {
        return Ok(MedOriginNativePreview::default());
    }
    if args.len() != 1
        || (args[0] != EXPLICIT_SYNTHETIC_CORE_FLAG
            && args[0] != EXPLICIT_SYNTHETIC_WORKSPACE_FLAG
            && args[0] != EXPLICIT_SYNTHETIC_READBACK_FLAG)
    {
        return Err(io::Error::new(
            io::ErrorKind::InvalidInput,
            "unapproved_d2_native_startup_argument",
        ));
    }
    // 2049 bytes are sufficient to detect oversized source data, without
    // reading an unbounded incoming payload or buffering clinical documents.
    let (sender, receiver) = mpsc::sync_channel(1);
    std::thread::Builder::new()
        .name("synthetic-core-stdin-once".to_owned())
        .spawn(move || {
            let mut bytes = Vec::with_capacity(512);
            let outcome = reader
                .take(MAX_FICTIONAL_CORE_STDIN as u64 + 1)
                .read_to_end(&mut bytes)
                .map(|_| bytes);
            let _ = sender.send(outcome);
        })?;
    let bytes = match receiver.recv_timeout(deadline) {
        Ok(result) => result?,
        Err(RecvTimeoutError::Timeout) => {
            return Err(io::Error::new(
                io::ErrorKind::TimedOut,
                "synthetic_core_stdin_deadline_refused",
            ));
        }
        Err(RecvTimeoutError::Disconnected) => {
            return Err(io::Error::new(
                io::ErrorKind::BrokenPipe,
                "synthetic_core_stdin_worker_disconnected",
            ));
        }
    };
    if bytes.is_empty() || bytes.len() > MAX_FICTIONAL_CORE_STDIN {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            "unapproved_d2_synthetic_core_stdin_size",
        ));
    }
    if args[0] == EXPLICIT_SYNTHETIC_READBACK_FLAG {
        MedOriginNativePreview::from_one_time_synthetic_encrypted_readback_stdin(&bytes).map_err(
            |_| {
                io::Error::new(
                    io::ErrorKind::InvalidData,
                    "unapproved_synthetic_encrypted_readback_projection",
                )
            },
        )
    } else if args[0] == EXPLICIT_SYNTHETIC_WORKSPACE_FLAG {
        MedOriginNativePreview::from_one_time_synthetic_workspace_stdin(&bytes).map_err(|_| {
            io::Error::new(
                io::ErrorKind::InvalidData,
                "unapproved_d2_synthetic_workspace_stdin_receipt",
            )
        })
    } else {
        MedOriginNativePreview::from_one_time_fictional_core_stdin(&bytes).map_err(|_| {
            io::Error::new(
                io::ErrorKind::InvalidData,
                "unapproved_d2_synthetic_core_stdin_report",
            )
        })
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<OsString> = std::env::args_os().skip(1).collect();
    let app = make_app(&args, io::stdin())?;
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
    const WORKSPACE_DEMO: &[u8] = include_bytes!("../fixtures/core/workspace-ephemeral-demo.json");
    const ENCRYPTED_READBACK: &[u8] =
        include_bytes!("../fixtures/core/encrypted-readback-projection.json");
    const CORE_NEGATIVE: &[u8] = include_bytes!("../fixtures/core/unknown-fictional-negative.json");

    #[test]
    fn real_core_decrypted_three_record_projection_starts_only_explicit_native_mode() {
        let app = make_app(
            &[OsString::from(EXPLICIT_SYNTHETIC_READBACK_FLAG)],
            Cursor::new(ENCRYPTED_READBACK),
        )
        .expect("exact fictional Core encrypted readback source projection");
        assert!(app.has_external_synthetic_encrypted_readback());
        assert!(!app.has_external_fictional_core_stdin());
        assert!(!app.has_external_fictional_workspace_stdin());
    }

    #[test]
    fn encrypted_readback_wrong_switch_and_forgery_never_create_native_gui() {
        for flag in [
            EXPLICIT_SYNTHETIC_CORE_FLAG,
            EXPLICIT_SYNTHETIC_WORKSPACE_FLAG,
        ] {
            assert!(make_app(&[OsString::from(flag)], Cursor::new(ENCRYPTED_READBACK)).is_err());
        }
        for raw in [
            b"{}".to_vec(),
            [ENCRYPTED_READBACK, b"\n"].concat(),
            [ENCRYPTED_READBACK, b" "].concat(),
            vec![b'x'; MAX_FICTIONAL_CORE_STDIN + 1],
        ] {
            assert!(
                make_app(
                    &[OsString::from(EXPLICIT_SYNTHETIC_READBACK_FLAG)],
                    Cursor::new(raw)
                )
                .is_err()
            );
        }
    }

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
    fn stalled_one_shot_stdin_refuses_on_deadline_without_starting_gui() {
        struct StalledReader(std::sync::mpsc::Receiver<()>);
        impl Read for StalledReader {
            fn read(&mut self, _buf: &mut [u8]) -> io::Result<usize> {
                let _ = self.0.recv();
                Ok(0)
            }
        }
        let (release, wait) = std::sync::mpsc::channel::<()>();
        let error = make_app_with_deadline(
            &[OsString::from(EXPLICIT_SYNTHETIC_CORE_FLAG)],
            StalledReader(wait),
            Duration::from_millis(35),
        )
        .err()
        .expect("abandoned stdin must fail closed");
        drop(release);
        assert_eq!(error.kind(), io::ErrorKind::TimedOut);
        assert_eq!(error.to_string(), "synthetic_core_stdin_deadline_refused");
    }

    #[test]
    fn complete_report_without_eof_is_not_accepted() {
        struct FullBytesWithoutEof {
            sent: bool,
            release: std::sync::mpsc::Receiver<()>,
        }
        impl Read for FullBytesWithoutEof {
            fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
                if !self.sent {
                    assert!(buf.len() >= CORE_KNOWN.len());
                    buf[..CORE_KNOWN.len()].copy_from_slice(CORE_KNOWN);
                    self.sent = true;
                    Ok(CORE_KNOWN.len())
                } else {
                    let _ = self.release.recv();
                    Ok(0)
                }
            }
        }
        let (release, wait) = std::sync::mpsc::channel::<()>();
        let result = make_app_with_deadline(
            &[OsString::from(EXPLICIT_SYNTHETIC_CORE_FLAG)],
            FullBytesWithoutEof {
                sent: false,
                release: wait,
            },
            Duration::from_millis(35),
        );
        drop(release);
        assert_eq!(
            result
                .err()
                .expect("report without EOF should be refused")
                .kind(),
            io::ErrorKind::TimedOut
        );
    }

    #[test]
    fn permission_denied_stdin_read_is_not_silently_coerced_to_empty() {
        struct DeniedReader;
        impl Read for DeniedReader {
            fn read(&mut self, _buf: &mut [u8]) -> io::Result<usize> {
                Err(io::Error::new(
                    io::ErrorKind::PermissionDenied,
                    "synthetic denied",
                ))
            }
        }
        let error = make_app(
            &[OsString::from(EXPLICIT_SYNTHETIC_CORE_FLAG)],
            DeniedReader,
        )
        .err()
        .expect("read error must not launch GUI");
        assert_eq!(error.kind(), io::ErrorKind::PermissionDenied);
    }

    #[test]
    fn exact_source_synthetic_encrypted_workspace_summary_opens_read_only_gui() {
        let app = make_app(
            &[OsString::from(EXPLICIT_SYNTHETIC_WORKSPACE_FLAG)],
            Cursor::new(WORKSPACE_DEMO),
        )
        .expect("one exact ephemeral synthetic-only workspace receipt");
        assert!(app.has_external_fictional_workspace_stdin());
        assert!(!app.has_external_fictional_core_stdin());
    }

    #[test]
    fn forged_workspace_production_flags_or_extra_records_refused_before_gui() {
        for data in [
            b"{}".to_vec(),
            [WORKSPACE_DEMO, b" "].concat(),
            [WORKSPACE_DEMO, b"\n"].concat(),
            vec![b'X'; MAX_FICTIONAL_CORE_STDIN + 1],
            WORKSPACE_DEMO
                .windows(5)
                .position(|w| w == b"false")
                .map(|idx| {
                    let mut bytes = WORKSPACE_DEMO.to_vec();
                    bytes[idx] = b't';
                    bytes
                })
                .expect("canonical fictional false safety marker"),
        ] {
            assert!(
                make_app(
                    &[OsString::from(EXPLICIT_SYNTHETIC_WORKSPACE_FLAG)],
                    Cursor::new(data)
                )
                .is_err(),
                "unapproved workspace receipt must fail before GUI"
            );
        }
        assert!(
            make_app(
                &[OsString::from(EXPLICIT_SYNTHETIC_CORE_FLAG)],
                Cursor::new(WORKSPACE_DEMO)
            )
            .is_err(),
            "workspace report cannot masquerade as Core validation"
        );
        assert!(
            make_app(
                &[OsString::from(EXPLICIT_SYNTHETIC_WORKSPACE_FLAG)],
                Cursor::new(CORE_KNOWN)
            )
            .is_err(),
            "Core validation receipt cannot masquerade as encrypted workspace"
        );
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
