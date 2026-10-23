# MedOrigin — Identity and Compatibility Policy

**Status:** Current public identity and source-compatibility policy. No scientific protocol, frozen source, execution grant, or release authorization is amended by this document.

## Public identity

- Product and repository: **MedOrigin**
- Canonical GitHub home: https://github.com/AbdulazizShehri/MedOrigin
- Brand proposition: **Every medical AI output deserves an origin.**
- Focus: evidence-native research infrastructure + local-first Clinical Workspace
- Product posture: transparent research software, not a medical device or PHI-ready application

Use **MedOrigin** in new public-facing product documentation, repository metadata, presentations, onboarding, and general-purpose interface copy.

## Official visual identity

The founder-approved MedOrigin identity (Concept 01 / Overlap Forward) is published
in [assets/brand](../assets/brand/README.md). The canonical mark uses two equal charcoal diagonal strokes to the left of a
separate orange wedge and an orange circular field, with a transparent diagonal
gap between the wedge and the circular field, matching the approved reference.
Use orange `#FF6A00`, charcoal `#202020`, and warm paper `#FAF7F3`.
All MedOrigin wordmark files are self-contained outlined SVGs; no font file is
redistributed. The approved assets do not imply clinical validation or publication.

## What intentionally keeps its historical identity

- The Python distribution, import package, and command remain `medscale`.
- The scientific implementation namespace `medscale.mesc`, MRL/CW identifiers, FHIR contracts, and stored keys are **not** mass-renamed.
- `MESC` and `MedScale` remain intact when they identify a prior scientific decision, previous project identity, canonical path, pinned Git object, archival document, frozen dependency manifest, external API, or published release.
- Earlier GitHub issue/PR decisions, original failure records, data provenance, citation and licensing records, and signed/hashed research artifacts remain authentic records of their historical names.
- Do **not** rewrite vendor, contributor, model, or third-party authorship to make borrowed code look internally invented.

## Verified residual-name audit

The 2026-10-11 source audit found legacy names in 1,263 of 1,431 tracked files. Many occurrences are technical or frozen identities: `src/medscale`, executable tests, dependency lockfiles, `specs/`, research notebooks, provider and model receipts, and prior decisions. This is **not** a safe repository-wide string-replacement task. Historical GitHub URLs remain in original evidence; current installation, citation, and contribution instructions use `AbdulazizShehri/MedOrigin`.

The outstanding package/API migration needs compatibility shims, dependency/lockfile review, tests and independent authorization when scientific source-bound contracts would change. No old source authorship or historical identity may be erased merely for cosmetic branding.

## Separate engineering migration

Future changes to a Python distribution name, package imports, public API, lockfiles, or serialized schema require explicit compatibility design: migration map; aliases/deprecation policy; tests across installed versions; dependency, provenance and artifact identity review; independent review; exact-head CI; and a separate authorization if governed science bytes or credentials are affected.

A cosmetic replacement across `src/`, `specs/`, `notebooks/`, history, cryptographic custody, or model manifests is **not** approved.

## Design voice

MedOrigin is an independent implementation, not a skin over a competitor. Prefer plain claims, auditable architecture, humane interaction patterns, and designs grounded in our own schemas and workflows. No screenshots of imaginary UI or inflated badges claiming clinical readiness.

- **Voice:** precise, calm, evidence-led.
- **Navigation:** research, evidence, workspace, datasets, governance.
- **Presentation:** clear typographic hierarchy, generous spacing, restrained technical color, accessible contrast.
- **Design principle:** show the underlying source, provenance, uncertainty, and user-control state before decorative confidence.
- **Claims:** labels like **implemented**, **fixture-only**, **blocked**, **not authorized**, and **verified externally** are distinct.

## External work and source permissions

Review and integrate external software when its actual license, lineage, and technical fit are established; prefer a bounded adapter over unnecessary copying. Keep required SPDX, copyright, NOTICE, and license text unaltered. Record the exact upstream revision and local modifications in a dedicated inventory for any directly reused code. A brand change never erases provenance.

See [Third-party provenance](../THIRD_PARTY_NOTICES.md), [contributing](../CONTRIBUTING.md), and [the research roadmap](../ROADMAP.md).
