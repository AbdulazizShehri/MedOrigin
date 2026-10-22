# Contributing to MedOrigin

Thank you for your interest. MedOrigin is an open research platform for **verifiable
clinical AI**. Its value comes from discipline, not volume — so contributions are held
to explicit scientific and engineering standards.

Please read this document, the [Code of Conduct](CODE_OF_CONDUCT.md), and the
[program rules R1–R7](docs/governance/rules.md) before opening a pull request.

## Ground rules (non-negotiable)

MedOrigin preserves these invariants at all times:

- **FHIR-native, validator-first, grammar-constrained, deterministic.**
- **Synthetic-only, PHI-free.** No real patient data enters training, evaluation, or
  benchmarks — ever (Rule R2).
- **No LLM-as-judge in any primary metric** (Rule R5). Headline metrics are executable.
- **One-way dependency.** Clinical Workspace information must not flow back into the research/training system; external project dependencies must remain explicit, licensed, and reviewed.
- **Permissive licensing.** Anything shipped must permit derivative models and
  commercial use (Rule R3).
- **Reproducibility.** No result without a script and a committed artifact (Rule R7).

A change that violates any invariant will not be merged, regardless of quality.

## How to participate

Start with a [discussion](https://github.com/AbdulazizShehri/MedOrigin/discussions) for larger ideas or an [issue](https://github.com/AbdulazizShehri/MedOrigin/issues/new/choose) for a focused change. Contributors can help with setup instructions, API documentation, reproducible tests, FHIR fixtures, accessibility, translations, and scientific tooling. Do not submit real patient data or unlicensed code. See [governance](GOVERNANCE.md), [support](SUPPORT.md), and [the Code of Conduct](CODE_OF_CONDUCT.md).

Small documentation-only contributions are welcome; report the checks you actually ran, and mark unavailable checks explicitly rather than inventing results. Maintainers decide merge readiness according to the protected branch and scientific safety rules.

## Development setup

MedOrigin uses [uv](https://docs.astral.sh/uv/) and Python 3.11.

```bash
git clone https://github.com/AbdulazizShehri/MedOrigin.git
cd MedOrigin
uv sync
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

The Python package and CLI remain named `medscale` for backwards compatibility; see the [brand transition policy](docs/BRAND_TRANSITION.md).

## The quality gate

Every change must pass, locally and in CI, before merge:

```bash
uv run ruff check .          # lint
uv run ruff format --check . # formatting
uv run mypy                  # strict typing
uv run pytest                # tests
```

The pre-commit hooks run the same checks. Do not bypass them.

## Workflow

1. **Trace your work.** Every change maps to an issue. Research changes also require a
   research question (RQ1–RQ7), horizon, and accepted scope in the
   [Research Vision](docs/vision/MEDSCALE_RESEARCH_VISION.md). Documentation, accessibility,
   tests, and onboarding improvements need a clear issue and acceptance criteria, not
   an invented research claim.
2. **One ticket at a time** (Rule R4). Finish, verify, commit — do not open the next.
3. **Branch** from `main`; keep the change small and focused.
4. **Test deterministically.** New behavior needs a deterministic test with a fixed seed.
5. **Commit** using [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat:`, `fix:`, `docs:`, `build:`, `ci:`, `refactor:`, `test:`, `chore:`).
6. **Open a PR** using the template. Fill the checklist honestly.

## Decisions and ADRs

Any decision that would cost more than a day to reverse requires an
[ADR](docs/adr/) (Rule R6): propose, wait for approval, then implement. Use
[`docs/adr/0000-template.md`](docs/adr/0000-template.md).

## Third-party code and design integrity

Use external sources only with validated rights, provenance and necessary notices. Branding must not obscure copyright or claim external code as original; see [Third-party notices](THIRD_PARTY_NOTICES.md). Source licenses, model licenses, and dataset rights are separate.

## Citations

No citation is written from memory (Rule R1). Every reference resolves to a live API
response with an identifier, `verified_at`, and `source_api`. See the
[reproducibility policy](docs/research/reproducibility_policy.md).

## Reporting issues

Use the issue templates. For security or PHI concerns, follow [SECURITY](SECURITY.md).
## Private planning and agent settings

Do not add unpublished founder strategy, internal roadmaps, supplier research,
budgets, private decisions, or agent-specific instructions to this public
repository. Keep those items in access-controlled internal workspaces. Local
editor and agent files are intentionally ignored by Git. This restriction does
not permit deleting original research provenance, required third-party
attribution, or versioned scientific protocols already needed for verification.

Public issues and pull requests should contain only actionable, non-sensitive
technical details and measured evidence. Do not post credentials, patient data,
or private plans in issues or CI logs.
