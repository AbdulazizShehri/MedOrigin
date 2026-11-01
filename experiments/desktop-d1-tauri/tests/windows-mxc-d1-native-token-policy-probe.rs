// NONPUBLISHING SYNTHETIC-ONLY Windows primary-token gate differential.
// Link the exact D1 runtime helper, not a copy of the security logic.
// No GUI, network calls, PHI, signed application or packet-level claims.
#[path = "../windows-token-gate/src/lib.rs"]
mod token_gate;
fn main() {
    match token_gate::require_windows_appcontainer_primary_token() {
        Ok(()) => println!("D1_NATIVE_PRIMARY_TOKEN_GATE_ACCEPTED_NO_PACKET_PROOF"),
        Err(reason) => {
            eprintln!("D1_NATIVE_PRIMARY_TOKEN_GATE_REJECTED: {reason}");
            std::process::exit(76);
        }
    }
}
