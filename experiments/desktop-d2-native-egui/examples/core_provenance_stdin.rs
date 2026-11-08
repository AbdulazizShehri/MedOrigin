//! Standalone TEST-ONLY read-only Core → D2 fixture bridge via bounded stdin.
//! Not invoked by the D2 GUI; no patient files, Core launches or networking.
use medorigin_desktop_d2_native_egui::core_provenance::{
    FictionalCoreInput, admit_fixed_fictional_core_report,
};
use std::io::{self, Read};

const MAX_CORE_REPORT_BYTES: u64 = 2048;

fn main() -> Result<(), &'static str> {
    if std::env::args_os().len() != 1 {
        return Err("D2_CORE_QA_REFUSED_UNEXPECTED_ARGUMENTS");
    }
    let mut raw = Vec::new();
    let total = io::stdin()
        .lock()
        .take(MAX_CORE_REPORT_BYTES + 1)
        .read_to_end(&mut raw)
        .map_err(|_| "D2_CORE_QA_REFUSED_STDIN_IO")?;
    if total == 0 || total > MAX_CORE_REPORT_BYTES as usize {
        return Err("D2_CORE_QA_REFUSED_OVERSIZED_OR_EMPTY_REPORT");
    }
    let result = admit_fixed_fictional_core_report(&raw)
        .map_err(|_| "D2_CORE_QA_REFUSED_UNTRUSTED_REPORT")?;
    let case = match result.case {
        FictionalCoreInput::KnownStructureDefinition => "known-structure-definition",
        FictionalCoreInput::UnknownResourceNegativeControl => "unknown-fictional-negative",
    };
    println!(
        "D2_CORE_SYNTHETIC_ONLY case={} status={} report_sha256={} FHIR_R4_NOT_VALIDATED",
        case, result.status, result.report_sha256
    );
    Ok(())
}
