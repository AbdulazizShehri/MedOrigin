# MedOrigin v0.3.4 Release Notes — Desktop Completion & Product Reality Hardening

- **Release Date:** 2026-11-21
- **Tag:** `v0.3.4`
- **Target OS:** Windows x64 (Native PE), Cross-platform Linux/macOS source support
- **Track Classification:**
  - **Lane A (Developer Software Track):** QUALIFIED
  - **Lane B (Research & Benchmarks):** `SCIENTIFIC_NOT_QUALIFIED` (MRL-0809 / MRL-0899 preserved; root `pyproject.toml` and `uv.lock` byte-intact)
  - **Lane C (Clinical Operations):** `CLINICAL_NOT_AUTHORIZED` (CW-021 preserved; strictly synthetic fixtures, zero PHI, zero live EHR writes)

---

## Executive Summary

MedOrigin v0.3.4 addresses the product reality audit requirements by resolving all discrepancies between reported completion status and the actual implemented codebase:

1. **Resolution of 28-Screen Status Discrepancy:**
   - Previous builds had only 8 active routes, with 16 screens routed to a placeholder `NotConnected` status and 4 gated/deferred screens.
   - v0.3.4 completes implementation for all 16 previously unrouted screens in `experiments/desktop-d2-native-egui/src/screens_connected.rs`.
   - All 16 screens now feature full egui interactive UIs connected to synthetic-only Clinical Workspace and Research Core adapters.
   - Screen-by-screen audit and verification evidence is documented in `docs/execution/v0.3/MEDORIGIN_28_SCREEN_AUDIT_ACCEPTANCE_MATRIX.md`.

2. **Strict Boundary Preservation:**
   - The 4 gated or deferred screens remain strictly non-clinical and unavailable:
     - Screen 4: *Audio & transcript* (GATED: Audio capture not authorized; non-clinical research only)
     - Screen 6: *Orders & tasks* (GATED: Clinical orders not authorized; zero live EHR writes)
     - Screen 7: *Coding suggestions* (DEFERRED: Billing and coding suggestions require specialized validation)
     - Screen 21: *Model catalog & runtime* (GATED: Model execution gated; no models installed)

3. **Reconciliation of Desktop Product Architecture:**
   - Reconciled documentation across root `README.md`, `experiments/desktop-d2-native-egui/README.md`, and single-EXE setup guides.
   - Clarified that MedOrigin Desktop D2 is an official Lane A Developer Preview desktop application (browser-free, native Rust/egui, local-first, zero PHI).

4. **Automated Windows Lifecycle & Reality Testing:**
   - Standalone user setup executable (`MedOrigin-Synthetic-Private-Setup-windows-x86_64.exe`) and portable zip archive (`MedOrigin-Synthetic-D2-windows-x86_64-<hash>.zip`) fully qualified via `qualify_windows_private_user_setup.py`.
   - Verified clean installation, Start Menu shortcut creation, tampered binary detection, and clean uninstallation leaving zero orphan files.
   - Automated UIAutomation test suites (`windows-native-fhir-uia-qualification.ps1` and `windows-real-core963-file-batch-receipt-uia.ps1`) run and pass 100% green against the native Windows PE executable.

5. **CycloneDX 1.5 Software Bill of Materials (SBOM):**
   - Published unified CycloneDX 1.5 JSON SBOM at `docs/releases/sbom-v0.3.4.cdx.json` covering all 263 workspace components (Python packages from `uv.lock` and native Rust dependencies from `cargo-cyclonedx`).

---

## Artifact Inventory

| Asset Name | Type | Purpose |
|---|---|---|
| `medscale-0.3.4-py3-none-any.whl` | Wheel | Core Python package wheel (ADR-0045 Base Core projection) |
| `medscale-0.3.4.tar.gz` | Source Distribution | Source archive for reproducible building |
| `MedOrigin-Synthetic-Private-Setup-windows-x86_64.exe` | Windows Setup | Self-extracting single-EXE user installer for Windows x64 |
| `MedOrigin-Synthetic-D2-windows-x86_64-<hash>.zip` | Portable Archive | Zero-install standalone desktop application |
| `sbom-v0.3.4.cdx.json` | CycloneDX SBOM | Full component and license inventory (spec 1.5) |
| `SHA256SUMS.txt` | Cryptographic Hashes | Authenticated checksums for all release assets |
