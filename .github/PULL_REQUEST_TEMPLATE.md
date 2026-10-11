<!-- Thank you for contributing to MedOrigin. Keep PRs small and focused (one ticket). -->

## Summary

<!-- What does this change do, and why? -->

## Related

<!-- Link the issue / research question (RQ) / ADR this traces to. Work that maps to no
     research question or horizon is out of scope until the vision is amended. -->

- Traces to:

## Checklist

- [ ] Any reused third-party source includes required upstream copyright, license and notice evidence (see `THIRD_PARTY_NOTICES.md`)
- [ ] No source-bound historical identity, scientific receipt or frozen contract was rewritten for branding
- [ ] Actual independent review/tool coverage and limitations are reported honestly

- [ ] `uv run ruff check .` passes
- [ ] `uv run ruff format --check .` passes
- [ ] `uv run mypy` passes (strict)
- [ ] `uv run pytest` passes
- [ ] New/changed behavior is covered by a deterministic test
- [ ] Docs updated (including any referenced-but-new documents)
- [ ] No dependency on Afia introduced (MedOrigin never depends on Afia)
- [ ] No PHI / no real patient data introduced (synthetic-only)
- [ ] If this is a decision costing >1 day to reverse, an ADR is included
