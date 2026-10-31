# Cross-job Core artifact SHA-256 identity — source-only qualification

**Date: 2026-10-31. Status: OPEN DRAFT / NO RELEASE / NO MERGE.** This supplements [Draft #778](https://github.com/AbdulazizShehri/MedOrigin/pull/778) and its existing private `qualified-dist` handoff. Immutable base SHA: `81bde5c35e7263a8a14787a074bcfe9a66dac103`. Canonical research `pyproject.toml`, `uv.lock`, MRL evidence, optional extras, version identity and all publication flags remain untouched.

## Scope and trust boundary

Before this change, the canonical protected-tag build validated the exact two Core archive bytes and staged them in `qualified-dist`, but the **downstream** `install-smoke`, conditional GitHub Release and conditional TestPyPI jobs only relied on an independently downloaded artifact, and TestPyPI only asserted one Wheel and one sdist. A pair could be different after transfer without being compared with an expected digest produced outside that downloaded payload. This is a **missing cross-job byte-identity assurance**, not proof that GitHub artifacts were actually attacked.

The build job now calculates SHA-256 for each of the two **private qualified archives** before `actions/upload-artifact`, with strict count (exactly two top-level entries), type, and lower-case 64-hex checks. It emits immutable-to-the-job `needs.build.outputs.wheel_sha256` and `needs.build.outputs.sdist_sha256` via `$GITHUB_OUTPUT`. Nothing is uploaded, published or released solely because these outputs exist.

The downloaded artifact in EACH downstream job is checked against **those independent build outputs** before it may be installed or released:
- `install-smoke` verifies the downloaded `dist` pair **before** `uv pip install` of the Wheel.
- `github-release` verifies the downloaded pair **before** its pre-existing hard optional-extras gate and separate private `qualified-dist` restaging, so the release action consumes requalified bytes.
- `testpypi-publish` explicitly adds `build` to its pre-existing `github-release` dependency (now `needs: [github-release, build]`) and verifies the downloaded pair before invoking its trusted publishing action. It does not check out repository code, gain extra token permissions, or acquire any publish capability unless both the original opt-in flag and GitHub Release prerequisite succeed.

Each verification uses fail-closed Bash and `sha256sum` on the tagged jobs' Ubuntu runners. It requires both outputs to be exactly 64 lower-case hex characters; exact two top-level entries with one regular non-symlink Wheel and one regular non-symlink sdist; exact hash matches for both. An extra file, symlink, missing archive, invalid expected digest or mutated bytes cause a non-zero exit. No self-authenticating manifest inside the downloaded payload is treated as the source of expected hashes.

## Actual automated evidence (nonpublishing)

- **Test-first expected RED:** [GitHub Actions #41220508368](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41220508368), all six source-only Windows/Ubuntu/macOS × Python3.11/3.12 jobs failed the new cross-job contract checks before implementation. These are *missing-contract* failures, not exploited package releases.
- New source-level checks assert build outputs are recorded after the private handoff and before uploading; install/Release/TestPyPI all verify against `needs.build.outputs` before their first install or publish operation; both original TestPyPI trusted publisher opt-in and its GitHub Release gating remain; no new checkout or token scope is added to TestPyPI.
- A real Linux test extracts the **actual tagged workflow Bash verification step**, rather than copying an independent implementation, and executes that step separately for all three consumers on synthetic bytes. It confirms clean success and rejection of Wheel tampering, sdist tampering, a rogue third file, missing archive, symlinked Wheel and incorrect expected SHA-256. This is tested without a tag or any publisher action.
- **Final exact-head qualification:** must be recorded in PR discussion after source-only CI completes at the final exact SHA, with Windows/Ubuntu/macOS × Python 3.11/3.12 and Ruff. The production tag path cannot be executed without publishing authority and remains unrun.

## Important limitations

GitHub Actions job outputs are a distinct value channel from the artifact ZIP, **not a cryptographic signature or external independent attestation**. This detects changed artifact payloads between trusted jobs; it does not prove adversarial mutation resistance within the **same** runner immediately after a last check, protect an already compromised GitHub runner or token, or certify exact Git-to-artifact provenance. Source-to-Git checks, immutable private handoff, external independent review and future publisher-time no-mutation requirements remain separate. `publication_authorized=false` and all opt-ins remain unchanged.

**NO-GO still applies:** #574 owner/version/ADR-0045 decision, #622 frozen optional research Pillow/Accelerate advisories, #603 independent security/author review, #662 Windows D1 WebView2 child TCP/UDP/DNS egress, #673 Linux maintenance and #676 macOS accessibility. No protected-main merge, tag, GitHub Release, TestPyPI/PyPI publication, clinical deployment, PHI, EHR writes or paid services.
