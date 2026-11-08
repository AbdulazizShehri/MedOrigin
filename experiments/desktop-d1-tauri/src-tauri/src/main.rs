// No additional console window in an experimental Windows desktop build.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    medorigin_desktop_d1_preview_lib::run()
}
