//! Experimental native GUI with synthetic bytes only. No EHR, PHI or networking.
pub mod app;
pub mod core_provenance;
pub mod workspace_receipt;
pub use app::{FIXTURES, MedOriginNativePreview};
