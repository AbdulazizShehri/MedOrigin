# Third-party Source & Attribution Policy

MedOrigin is independently branded research software built with open-source components and interoperability standards. A claim of permission to copy or modify third-party code does not establish ownership of that code and does not waive required attribution.

## Current baseline

- Repository license: [Apache License 2.0](LICENSE).
- The source and tooling manifest in [pyproject.toml](pyproject.toml), `uv.lock`, and the Workspace package manifests lists concrete package dependencies. Each package has its own license and copyright holders.
- Model checkpoints, datasets, benchmarks, pretrained weights, and services have **separate rights**. No project-level Apache-2.0 label automatically extends to those artifacts.
- Reference analyses and design inspiration in `docs/architecture/`, `docs/strategy/`, and ADRs are not proof that the referenced projects' source code has been copied or incorporated.

## Mandatory record for each direct source reuse

Before introducing third-party source files or significant derived code, record:

| Field | Required evidence |
| --- | --- |
| Source | Upstream project, canonical repository URL and maintainer |
| Identity | Exact commit/release and file paths used |
| Rights | Applicable SPDX/license, notices, redistribution conditions and any separately documented permission |
| Transformation | What was reused, modified, or adapted locally |
| Distribution | Files carried into MedOrigin and required attribution locations |
| Verification | License review, security review, tests, and reproducibility limits |

Keep original copyright and attribution notices where required. If a supplier's license or permission is unclear, block direct reuse rather than silently treating it as an original MedOrigin implementation.

## Independent identity without provenance laundering

It is appropriate to design MedOrigin's own UX, architecture, names, schemas, documentation, and visual system. It is **not** appropriate to delete upstream notices, rewrite commit authorship, misattribute existing source, or claim an imported algorithm as an original invention.

The existing source history and research evidence stay preserved through the MedOrigin rebrand. A future donor-integration PR must include a concrete third-party inventory instead of an unverifiable blanket statement that every dependency or reference has been imported.

For security concerns, use [private vulnerability reporting](https://github.com/TheHalfMoon/MedOrigin/security/advisories/new).
