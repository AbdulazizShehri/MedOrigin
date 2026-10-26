# Security alert coverage — GitHub read-only visibility audit

Tracks [#621](https://github.com/AbdulazizShehri/MedOrigin/issues/621).
It is **not** a scan proving that dependencies are safe, does not resolve
vulnerabilities, and grants no release or model qualification.

Run from an authenticated workstation with the free GitHub CLI:

```bash
python scripts/check_medorigin_security_visibility.py \
  --repository AbdulazizShehri/MedOrigin
```

The tool attempts three **read-only** sources, using bounded full pagination:

1. Dependabot open alerts
2. Code scanning open alerts
3. Secret scanning open alerts

A successful, complete empty `200 []` response means only **zero currently
visible open alerts**. It does **not** establish that vulnerability scanning
covers all dependencies, that any individual dependency is safe, or that
there are no private/unreported vulnerabilities.

Any disabled, inaccessible, missing, truncated, malformed, or non-200 signal
is clearly reported as unavailable and **blocks visibility admission**.
Nonzero visible alerts likewise require a separate triage decision.
The command exits 2 for such blockers. It never calls the repository
settings API, requests higher privileges, pushes changes or uploads artifacts.
It also always reports `vulnerability_free=false` and
`publication_authorized=false`.

On October 26, 2026, the existing `Dependabot alerts` endpoint returned
`403: Dependabot alerts are disabled for this repository`. This is a
**missing observability signal**, not an assurance of zero vulnerabilities.
The existing vulnerability finding in optional pinned `pillow==12.3.0`
and `accelerate==1.14.0` is separately documented in
[#622](https://github.com/AbdulazizShehri/MedOrigin/issues/622).
It is not fixed by enabling alerts.

**Owner/admin action:** enable GitHub dependency graph and **free** Dependabot
vulnerability alerts if eligible, after verifying that enabling them does
not incur any paid billing. Do not change `pyproject.toml`, `uv.lock`,
the frozen scientific research assets, Dependabot update-PR limits, or
paid security options without a separately authorized governed decision.
Re-run the read-only audit and attach the exact response and SHA for #621
and the independent reviewer #603. A returned `200 []` is visibility
evidence, not a security signoff.

The synthetic CI job tests the classifier and failure cases using a
read-only GitHub token; it does **not** misrepresent mock API responses as
real security scanning or mutate repository settings.
