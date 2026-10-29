// Adapted from emilk/eframe_template under Apache-2.0, see UPSTREAM-NOTICE.md.
// Modified: no web target, persistence, telemetry, navigation or external data.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: eframe::egui::ViewportBuilder::default()
            .with_inner_size([920.0, 600.0])
            .with_min_inner_size([700.0, 480.0]),
        ..Default::default()
    };
    eframe::run_native(
        "MedOrigin Native Rust — Synthetic Experiment (NO RELEASE)",
        options,
        Box::new(|_cc| {
            Ok(Box::new(
                medorigin_desktop_d2_native_egui::MedOriginNativePreview::default(),
            ))
        }),
    )
}
