# MedOrigin Core: source-bound truthful browser QA (private, nonrelease)

2026-11-05, Asia/Riyadh. Follow-up to private draft Core PR #952.

## Product issue and implementation

The historical automated browser/Sentry workflow exercised the old
`examples/synthetic_fhir_developer_beta/reproduce.py` path. That legacy path
required `fhir validate` to say `valid`/exit 0, although the actual Core
correctly reports `not_validated`/exit 2 without a complete official
HL7 FHIR R4 validator. The browser workflow therefore failed before Edge
could load an HTML page. Never turn this into a synthetic fake-green report.

The private Core-only browser QA now uses the already-implemented truthful
`core_truth_preview.py` renderer with the existing source-qualified
`qualify_medorigin_developer_beta.py --core-negative-truth-preview` gate.
The hosted Windows job builds both Wheel and sdist from the exact source
projection, offline-installs the same Core Wheel separately in Python 3.11
and 3.12, and refuses the QA unless all of the following are true:

- Git source is clean and matches full Core Wheel source identity, sdist
  distribution scope and pinned Wheel metadata.
- Every installed Core Python source member matches the Wheel on BOTH
  independent Python interpreters.
- The existing provenance checker actually executes the two installed
  Python **modules**, not an unattested generated `medscale.exe` launcher.
- Both known and unknown fictional reports have stable, different SHA-256
  digests, both remain **NOT VALIDATED**, and receipt/HTML SHA digests from
  a second independent execution exactly match the qualified values.
- All clinical, full FHIR, publication, native-launcher and merge/release
  authorization fields are literally false.

Edge/Playwright now verifies two displayed **NOT VALIDATED** cases,
exact source-bound digests, a visible NOT AUTHORIZED footer, no horizontal
scroll at three device widths, no active script/iframe/image/form/link, and
zero external requests/errors. The legacy renderer's long hostile label/XSS
regression remains under test; offline Sentry additionally rejects a
synthetic patient-name field from the *new* Core proof without emitting the
input into its captured memory-only envelope. No network telemetry.

## Verification boundaries

Hosted Windows attempt on first functional head `349273b5` rebuilt exact
Core Wheel+sdist, independently qualified package source and interpreter
execution, then reached real Playwright Edge and correctly caught **phone-width
horizontal overflow** of the long SHA-256 report digest. This was a genuine UI
bug, not a package provenance or clinical-status failure. A second exact
hosted attempt on `9142cc60` also failed overflow, proving the CSS-only
change was insufficient. The root cause was an **unterminated `content` quote
on the CSP meta tag**. Edge parsed `<title>`, `<style>` and much of the page
as CSP directive text; no CSS stylesheet was actually applied. We now close
the attribute correctly, keep the SHA-wrapping defensive CSS, and require a
parsed stylesheet, CSP tag, and zero body margin in real Edge QA.

Independent **actual owner Windows Edge/Playwright** rendered the corrected
immutable fictional preview at 375×667, 850×610 and 1440×900. Exact
`documentElement.scrollWidth == innerWidth` at all three, body margin 0,
`document.styleSheets.length == 1`, SHA codes display as wrapping blocks,
no overflowing elements and no CSP parsing console errors. This is a
renderer/viewport proof with fictional fixed digests, NOT the separate
installed artifact/source-qualified hosted proof. A subsequent exact-head
hosted CI result still must be inspected. Without the quote fix, the new
HTML-parser regression fails, even if a future CSS rule looks valid.

At author-source level, Windows Python 3.14 Ruff and formatting checks
passed. The existing negative-truth/full-gate regression plus additional
new source-bound handoff adversarial tests: **47 PASS**. The first pytest
attempt had unrelated Windows default-temp-folder ACL errors; rerunning
with a new private `--basetemp` produced 47/47 pass. This is not a claim
that the source-independent hosted real Edge/installed-Wheel job passed;
its exact commit run must be inspected before recording such evidence.

The **separate full Developer Beta release/rehearsal workflow remains
strictly blocked** by legacy full-FHIR/clinical requirements and is not
skipped, softened, marked continue-on-error or falsely reported green.
This change cannot qualify FHIR conformance, a production clinical
Workspace, real patient data, PHI, authenticated RBAC, native executable
identity, OS egress confinement, external safety review or release.

Keep this stacked PR **PRIVATE DRAFT**. Do not merge protected main,
publish, sign a release, transfer patient records or modify frozen
research assets. #882/#877/#893/#603/#622/#574 and production security
remain independently unresolved.
