// TEST-ONLY, NONPUBLISHING. Reuses real D2 GUI; no networking in src/.
// Single synthetic TCP connect to localhost, never DNS or Internet.
use eframe::egui;
use medorigin_desktop_d2_native_egui::MedOriginNativePreview;
use std::net::{Ipv4Addr, SocketAddr, SocketAddrV4, TcpStream};
use std::time::Duration;

fn prove_localhost_denial() -> &'static str {
    let Ok(raw) = std::env::var("MEDORIGIN_D2_SYNTHETIC_LOOPBACK_PORT") else {
        return "D2_SELF_SANDBOX_PROBE_NOT_CONFIGURED";
    };
    let Ok(port) = raw.parse::<u16>() else {
        return "D2_SELF_SANDBOX_PROBE_INVALID_PORT";
    };
    if port == 0 {
        return "D2_SELF_SANDBOX_PROBE_INVALID_PORT";
    }
    let address = SocketAddr::V4(SocketAddrV4::new(Ipv4Addr::LOCALHOST, port));
    match TcpStream::connect_timeout(&address, Duration::from_secs(2)) {
        Err(error) if matches!(error.raw_os_error(), Some(1 | 13)) => {
            "D2_SELF_PROCESS_APP_SANDBOX_LOOPBACK_DENIED_EPERM"
        }
        #[cfg(target_os = "linux")]
        Err(error) if matches!(error.raw_os_error(), Some(101 | 113)) => {
            "D2_LINUX_ROOTLESS_NETNS_LOOPBACK_UNREACHABLE"
        }
        Err(_) => "D2_SELF_SANDBOX_PROBE_INCONCLUSIVE_SOCKET_ERROR",
        Ok(_) => "D2_SELF_SANDBOX_PROBE_UNEXPECTED_NETWORK_ALLOWED_NO_GO",
    }
}

#[derive(Default)]
struct NetworkTestWrapper {
    app: MedOriginNativePreview,
    probe_result: Option<&'static str>,
    #[cfg(target_os = "linux")]
    linux_logged: bool,
}

impl eframe::App for NetworkTestWrapper {
    fn ui(&mut self, ui: &mut egui::Ui, frame: &mut eframe::Frame) {
        let result = self.probe_result.get_or_insert_with(prove_localhost_denial);
        #[cfg(target_os = "linux")]
        if !self.linux_logged {
            // Test-only process evidence. The actual D2 product has no network APIs.
            eprintln!("MEDORIGIN_D2_LINUX_NETWORK_PROBE_RESULT={result}");
            self.linux_logged = true;
        }
        ui.monospace(*result);
        <MedOriginNativePreview as eframe::App>::ui(&mut self.app, ui, frame);
    }
}

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([920.0, 600.0])
            .with_min_inner_size([700.0, 480.0]),
        ..Default::default()
    };
    eframe::run_native(
        "MedOrigin D2 Synthetic Network Test (NOT PRODUCT)",
        options,
        Box::new(|_cc| Ok(Box::<NetworkTestWrapper>::default())),
    )
}
