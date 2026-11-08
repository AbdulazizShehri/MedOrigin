//! Experimental native GUI with synthetic bytes only. No EHR, PHI or networking.
pub mod app;
pub mod core_file_batch;
pub mod core_provenance;
pub mod encrypted_readback;
pub mod local_bundle_import;
pub mod protected_audit;
pub mod screens;
pub mod session;
pub mod support;
pub mod synthetic_bundle;
pub mod theme;
pub mod workspace_receipt;
pub use app::{FIXTURES, MedOriginNativePreview};
