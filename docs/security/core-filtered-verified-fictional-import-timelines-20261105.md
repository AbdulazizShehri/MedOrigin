# MedOrigin Core: source-verified filtered fictional Workspace chronology

Private Core engineering, 2026-11-05 (Asia/Riyadh). No real patient data,
production keys, clinical use, external FHIR R4 certification or publication.

## Actual user-visible functionality

Existing Core supports **two or more independently encrypted FHIR-shaped
fictional imports** with verified audit chain, original source hashes and
per-import dated Encounter/Observation events, but it could only return the
entire timeline. Users now need a way to search a chronological range or
specific event kind without dumping patient identities or conflating separate
imported Patient IDs. This source-only enhancement adds:

- `medscale.fhirkit.workspace_multi_timeline.list_filtered_verified_synthetic_import_timelines`
  with inclusive `from_day_utc` and `through_day_utc` and exact
  `resource_type=Encounter|Observation`; full import/audit/source AES-GCM
  verification is completed **before** event filtering, including imports
  for which the selected view has zero matching events.
- Original source event ordinals and original import/audit order remain
  unchanged, with visible/hidden counts reconciled to the full verified
  chronology. Identical local Patient IDs in different imports are never
  treated as evidence of one real person. There is no identity join.
- Undated events stay visible when filtering only by event type; applying
  a UTC calendar range excludes undated events rather than misclassifying
  them. No partial results are returned on corruption, missing keys or
  failed source or audit attestation.
- The additive public CLI
  `medscale fhir filtered-multi-timeline-demo --synthetic-only --ephemeral-demo
  --from-day 2026-11-04 --through-day 2026-11-04 --event-type Encounter`
  genuinely imports two fixed imaginary FHIR Bundles in AES-GCM SQLite,
  creates audit events, closes and independently reopens that store, then
  reads all source-verified events and returns a filtered, strictly bounded
  metadata-only JSON view. It refuses source files, patient references,
  arbitrary filter names, duplicate flags, malformed calendar dates and
  wrong order, without echoing input strings or creating a network service.
- The old `multi-timeline-demo` exact-flag CLI is unchanged.

The sample above independently qualifies **4 source events from 2 imports**,
shows **1 verified Encounter on November 4** and 3 hidden events, retaining
both import groups even if one has zero matches. This is not a cross-import
patient history or FHIR clinical result.

## Source-local verification and nonrelease boundaries

**Verified native Windows Python 3.14:** expanded actual Core/Workspace
import, encrypted readback, multi-import timeline, portable demo and batch
regression suites **112/112 PASS**; Ruff lint/format **PASS**, git diff
whitespace **PASS**. Actual local source-dispatch CLI command with the fixed
November 4 Encounter view returned exit0 and independent AES-GCM cold reopen,
2 imports, 4 source events, 1 visible + 3 hidden, no identity join and
clinical_use_authorized=false. CLI is exercised from current SOURCE through
`from medscale.cli import main`; this is not a generated Windows native
console shim. A hidden first import forced to fail source validation correctly
blocks the entire selected view even if the filter would exclude its events.
Source tests also cover forged dates, event types, actor/permissions, current
chained audit SHA, missing key, and rejected patient-like CLI arguments.
Independently installed Wheel/Workspace provenance and hosted
cross-platform CI must be checked separately; source execution is not
equivalent to an installed/signed launcher. No permanent local workspaces.

Do not merge protected `main`, tag, deploy, sign, publish, use PHI, import
real EHR data, or assert clinical approval. Main blockers remain full official
HL7 FHIR R4 schema, terminology, invariants and external clinical
conformance (#877); full Developer Beta gate (#882); native shim attestation
(#893); independent security/clinical reviews (#603), dependency warnings
(#622), production authentication and OS key custody, and founder release
authority (#574). The passing Core-only browser negative-truth contract in
draft #954 is technical QA, not an approved release.
