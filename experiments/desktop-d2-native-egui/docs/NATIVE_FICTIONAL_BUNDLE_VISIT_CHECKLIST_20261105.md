# D2 native fictional multi-patient session visit checklist

**Owner-private developer experiment. Synthetic/structural Bundle ONLY. Not a clinician workflow, PHI import, review approval, clinical record, or release candidate.**

## Product behavior

The existing native Rust/egui fictional Bundle browser (3–48 source-admitted Patient/Encounter/Observation resources, up to 16 pretend patient groups) now supports an in-memory, bounded visit checklist:

- Mark current seen (demo only): records a boolean for only the currently source-admitted, currently visible fictional resource. Merely opening or following a link does not mark a record, and there is no clinical status.
- Next unseen visible record: advances within the currently active patient group and resource-type filter, skips already marked records, and wraps only among those currently visible. It clears navigation history as a direct worklist selection, never manufacturing a relationship edge. If all visible records were seen, it reports this locally without changing the selection.
- Reset seen (session only): clears all per-session marks, including other fictional patient groups. Patient/type switches preserve the overall session marks but clear stale selected records and relationship history. Clear/Escape, replacing the fictional source or relaunching resets the marks.
- Progress status: visible-seen/visible-total counts plus an explicit selected-record status, with no dates, names, clinical data, priority, inferred timeline, filesystem writes, Core modifications or network transmission.

The checklist is sized to the exact admitted Bundle resource count, never above 48. A forged length, hidden/stale selection, invalid graph destination or corrupted source state fails closed by clearing the source and checklist. It is intentionally not a reviewer signoff, FHIR validation, identity/RBAC mechanism, consent ledger, data-quality score or persistence feature.

## Compatibility boundaries

Default home stays source-free until clicking the existing built-in two-patient fictional demo. The explicit synthetic-multipatient-bundle-stdin flag still uses the original 32 KiB cap and five-second deadline; the encrypted Core session modes retain their 2 KiB cap and provenance/HMAC rules. No crates, network/file APIs, subprocesses, storage, clinical payload fields or permissions are introduced.

## Validation evidence

**Verified on the physical owner Windows 11 workstation against this source branch:**

- Offline locked Cargo all-target tests: **79 native Rust library + 14 native CLI + 7 source-only browser/network boundary = 100/100 PASS**, including 3 new visit-state tests. No tests skipped in these three suites.
- Offline locked all-target Clippy with -D warnings **PASS**, Cargo fmt --check **PASS**, native GUI build **PASS**. No new Cargo dependency or network permission.
- Exact compiled test GUI executable SHA-256: **d08c69fb8b2ffc601a9d9e46885d82da5774e5f6d7851989d384053fe358d4f2**. Exact eight-resource fictional source fixture SHA-256: **92004ddb54302dd70c899dc5ace1a88147e36d81d101f67616b9ee031365cd10**.
- Two independent **real Windows UIAutomation** runs against the exact same compiled GUI: explicit 32KiB-bounded synthetic stdin and no-argument home opt-in. Both clicked the new Mark seen / Next unseen / Reset controls, verified the session-visible progress text, exercised previous/next, patient groups, relationship Back and Clear, and ended **EXIT 0**. Existing exact markers: WINDOWS_NATIVE_EIGHT_RECORD_TWO_PATIENT_STRUCTURAL_FHIR_BUNDLE_GROUP_GRAPH_UIA_PASS_NONCLINICAL and WINDOWS_NOARG_ONE_CLICK_EMBEDDED_MULTIPATIENT_UIA_PASS_NONCLINICAL. Joint gate: MEDORIGIN_W88_REAL_WINDOWS_NATIVE_VISIT_ACTIONS_BOTH_STARTUP_MODES_PASS.

**Not yet verified for this new exact branch:** hosted Windows/Ubuntu PR CI, macOS new-code Apple AX, an installed binary or a professional accessibility/security/medical review. Base PR #962 CI passed before this change. No production-release qualification is inferred.

Private stacked Draft only. Unmerged, unpublished. Full production blockers remain: true clinical FHIR R4/profile validation, authenticated Core/workspace transport, patient identity and consent, secure key custody and encrypted clinical storage, network isolation, independent accessibility/security/clinical review, dependency remediation and signed installer.