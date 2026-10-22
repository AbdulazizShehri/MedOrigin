# MedOrigin Documentation

MedOrigin is an open-source, evidence-grounded medical AI research platform with
a local-first **synthetic-only** clinical workspace foundation. Start with the
current architecture and development guides below.

> **Research software only.** Not a medical device; no clinical decision-making,
> PHI ingestion, real-patient evaluation, autonomous diagnosis, or external EHR
> write access is authorized.

## Start here

| Guide | Purpose |
| --- | --- |
| [Project overview](vision/MEDORIGIN_OVERVIEW.md) | Product intent, implemented foundations, and current limitations |
| [MedOrigin architecture](architecture/medorigin_architecture.md) | System boundaries, data flow, and package layout |
| [Quick start](guides/research_quickstart.md) | Reproduce supported local research workflows |
| [Developer guide](guides/developer_guide.md) | Install, test, and contribute to the project |
| [Project roadmap](../ROADMAP.md) | Current roadmap with scientific and release gates |
| [Research questions](research/research_questions.md) | Scientific questions and the evidence needed to answer them |

## Community

MedOrigin is developed in public. Contributions to documentation, accessibility,
FHIR contracts, reproducible tests, developer experience, and research tooling
are welcome.

- [Contributing](../CONTRIBUTING.md) — safe development workflow and review
- [Community governance](../GOVERNANCE.md) — proposal and maintainer decisions
- [Support and questions](../SUPPORT.md) — where to ask for help
- [Discussions](https://github.com/AbdulazizShehri/MedOrigin/discussions) — ideas and feedback
- [Code of Conduct](../CODE_OF_CONDUCT.md) and [Security](../SECURITY.md)

## Engineering reference

- [Interoperability](architecture/interoperability_strategy.md) — FHIR boundary
- [Model-independent platform design](architecture/model_agnostic_platform.md) — components and interfaces
- [Reproducibility policy](research/reproducibility_policy.md) — provenance and verification
- [Research program](research/README.md) — scientific method and experiments
- [Clinical Workspace specification](../specs/medscale-clinical-workspace-v1/README.md) — current bounded implementation
- [Software release track](releases/software_release_track.md) — independent synthetic-only developer-package gates
- [Program rules](governance/rules.md) and [research scope](vision/MEDSCALE_RESEARCH_VISION.md)

## Canonical sources & precedence

Repository documentation describes what exists, not what is scientifically or
clinically approved. For conflicts in scope or interpretation:

1. The [research scope](vision/MEDSCALE_RESEARCH_VISION.md) governs permitted work.
2. Accepted [architecture decisions](adr/) govern their recorded decisions.
3. The [program rules](governance/rules.md), specifications, and exact test/evidence
   records govern verified status and acceptance.
4. The [roadmap](../ROADMAP.md) describes direction; it does not supersede
   executable checks or scientific evidence.

Original research records retain their own citation history and identifiers.

## Record integrity and compatibility

This page highlights the **current MedOrigin project**, rather than treating
earlier comparative studies or rejected proposals as current product features.
Original decisions, experiment receipts, filenames, citations, and technical
compatibility interfaces remain available for verification. Public-facing
documentation is not authority to rewrite historical evidence.

- [Compatibility and project identity](BRAND_TRANSITION.md)
- [Architecture decisions](adr/) and [research records](research/)
- [Third-party rights and notices](../THIRD_PARTY_NOTICES.md)
- [GitHub repository](https://github.com/AbdulazizShehri/MedOrigin)

## Documentation checks

The documentation link checker validates local Markdown targets and anchors in
the supported root and `docs/` tree without network access:

```bash
uv run python scripts/check_docs_links.py
```

Docs in this repository are sources, not a hosted website or an approved
release. Scientific, clinical, and publication readiness remain separately
controlled by the governing research and release evidence.
