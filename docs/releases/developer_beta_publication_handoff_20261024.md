# MedOrigin — Developer Beta publication handoff (PREPARED, NOT PUBLISHED)

**2026-10-24.** This file records a *local technical rehearsal* for the bounded
synthetic-only developer package. It is **not a release, release authorization,
independent security signoff, or a claim of clinician readiness**.

## Delivery identity and intended first package

- Product/repository: **MedOrigin** at `AbdulazizShehri/MedOrigin`.
- First Core distribution: **`medscale 0.3.0`**; import and CLI remain
  `medscale` for disclosed compatibility. There is no hidden rename.
- Separate Workspace: `medscale-workspace 0.1.0.dev1` (not bundled in Core,
  not approved as a PHI-bearing service or first-release dependency).
- The optional Tkinter example, fictional case explorer and local HTML viewer
  live in this source repository; **they are not in the Core wheel**. No
  standalone signed Windows/macOS installer exists yet. Do not market the Core
  wheel as a finished desktop patient app or a full FHIR conformance validator.
- Data: fictional fixtures only. No patient files, clinical claims, external
  EHR writes, model inference, or historical dataset migration.

## Exact positive technical rehearsal

The **pre-existing, unpublished** package artifacts bound to Draft PR #598's
`1cb9ccfeada45b6fa6514c404355f5901c2433f9` were checked on Windows:

| Artifact/step | Result |
| --- | --- |
| Core wheel `medscale-0.3.0-py3-none-any.whl` | SHA-256 `a718b77794c817dfcf6a711cd97324b3626e4d65382ba39c670a7c303fae07e7` |
| Wheel-to-committed-source verifier | PASS, 250 source files and 255 wheel members, no issues |
| Sdist scope/source verifier | PASS, 258 members, no issues |
| Installed metadata/projection URLs | PASS, `medscale 0.3.0`, no issues |
| Clean offline Python 3.11.15 installation | PASS |
| Clean offline Python 3.12.13 installation | PASS |
| Full installed Python source-byte comparison | PASS, **249 Python modules per runtime** matching wheel bytes |
| Cross-runtime actual synthetic FHIR run | PASS; `991d319d9c567db3a71985661a12abb67c8432ff43b439c08759f8ee1d52fbd9` |
| Native Tkinter GUI installed-Core E2E (Windows, both versions) | PASS, synthetic validation, copy, exclusive JSON export, no overwrite |

The reproducible **nonpublishing GitHub Actions rehearsal** is defined in
`.github/workflows/medorigin-developer-beta-rehearsal.yml`. On a PR or a
manual dispatch it stages the current committed source, builds the candidate
artifacts outside the checkout, clean-installs the exact wheel into Python
3.11 and 3.12 environments on Linux and Windows, checks the installed source
bytes, and runs the real synthetic FHIR example. A passing job is a technical
readiness receipt only; there is no upload, tag, publisher activation or
artifact distribution step.

The two local Windows installs used for the earlier evidence were created from
the **same** exact local wheel, without remote package installation or model download. The local E2E did not qualify
the optional independently packaged Workspace; it was Core-only.

The machine-readable automated source-to-installed-wheel rehearsal is in
`scripts/qualify_medorigin_developer_beta.py`. Given two *already installed*
venvs, a clean detached checkout of the candidate's exact Git SHA, and the
candidate wheel/sdist, run from this repository:

```bash
python scripts/qualify_medorigin_developer_beta.py \
  --checkout /path/to/clean-detached-Core-source \
  --wheel /path/to/medscale-0.3.0-py3-none-any.whl \
  --sdist /path/to/medscale-0.3.0.tar.gz \
  --python311 /path/to/python3.11-venv/bin/python \
  --python312 /path/to/python3.12-venv/bin/python
```

On Windows, point `--python311` and `--python312` to each venv's
`Scripts/python.exe`. All package checks use the exact source checkout.
The script runs only local verifier commands and a temporary synthetic E2E
reproduction, compares installed Python file bytes to the wheel, and returns
`TECHNICAL_PREPUBLICATION_REHEARSAL_PASS` with all authorization flags false.
It does not create a tag, upload an artifact, build from a mutable worktree,
touch historical receipts, invoke a package index or use network APIs.

## Local QA handoff integrity check (no installation or publication)

The unpublished Windows handoff prepared on 2026-10-24 is stored at
`C:/Users/Shehr/Desktop/MedOrigin-v0.3.0-Developer-Beta-UNPUBLISHED`
and the sibling `.zip`. Its ZIP SHA-256 is
`001034f6c9807159c005b28b3e0c00f4af2e7c709897b95ece02b2361a108555`.

Before installing anything from this *particular* QA handoff, run the
standard-library-only source checker:

```powershell
python scripts/verify_medorigin_qa_handoff.py "C:/Users/Shehr/Desktop/MedOrigin-v0.3.0-Developer-Beta-UNPUBLISHED.zip" --expected-zip-sha256 001034f6c9807159c005b28b3e0c00f4af2e7c709897b95ece02b2361a108555
python scripts/verify_medorigin_qa_handoff.py "C:/Users/Shehr/Desktop/MedOrigin-v0.3.0-Developer-Beta-UNPUBLISHED"
```

For a **repeatable, new** QA ZIP, there is also a standard-library-only,
read-only-source builder. It accepts only the pinned Core Wheel, sdist,
provenance and the previously committed synthetic examples, and creates a
**new, unpublished ZIP**, never overwriting the original:

```powershell
python scripts/assemble_medorigin_unpublished_qa.py `
  --repository . `
  --wheel C:/path/to/verified/medscale-0.3.0-py3-none-any.whl `
  --sdist C:/path/to/verified/medscale-0.3.0.tar.gz `
  --provenance C:/path/to/MEDORIGIN_SOURCE_PROVENANCE.json `
  --output C:/path/to/new-empty-folder/MedOrigin-v0.3.0-Developer-Beta-UNPUBLISHED.zip
```

This script reads the eight fixed examples and legal notices with
`git show` at pinned exact SHA `852ca86a`; it reads none of the mutable
checkout example files. It requires a clean Git worktree, checks the source
receipt and both exact known Core SHA-256 values, reuses the handoff verifier
on the assembled members and resulting ZIP, then exclusively creates the
output. ZIP entry order, timestamps and compression mode are fixed for
deterministic cross-machine assembly. It does **not** build, sign or publish
Core, install dependencies, contact GitHub or use patient data. Every
newly produced ZIP needs its **own** SHA-256 readback; the checksum above is
only for the earlier manually staged ZIP. Do not confuse a reproducible
test handoff with a final authorized release artifact.

The checker rejects missing/extra members, duplicate or unsafe ZIP paths,
symlinks, bad byte digests, ambiguous JSON, type-substituted authorization
flags and an unexpected Core/source identity; it performs **no extraction,
execution or network operation**. Both real local copies passed with
`MEDORIGIN_UNPUBLISHED_QA_INTEGRITY_PASS` and exactly 16 checked files.
Adversarial verification has separate focused tests.

This confirms internal consistency and matches the *previously trusted*
Core hashes; without an independently trusted external ZIP digest or a
publisher signature, it does **not authenticate an arbitrary downloaded
bundle**. The unsigned bundle consists of Core #598 artifacts plus separate
source examples from #617. It is a QA handoff, **not** a signed consumer
installer, an approved integrated source release, or proof of independent
security approval.

## Outstanding preparation — distinct from the later publish button

1. **Independent release-boundary review #603**: review exact candidate
   source-to-wheel/sdist/provenance, hostile archives, release workflow trust,
   redistribution, and persisted-format decisions. Author-run testing and
   CodeQL do not count as the external/independent reviewer receipt.
2. **Decision #574 / ADR-0044**: approve or reject the isolated Core projection,
   make the package/version/branding choice explicit, and preserve frozen
   research root/lock/MRL bytes. Do not combine a source-projection route
   with the older successor-root recommendation without reconciling policy.
3. **Integrated exact-head CI and packaging**: the original Core #598 has
   successful hosted checks. This source example stack (#612–#616 and later)
   has not been merged. Once a final release-source tree is selected,
   rebuild its own exact-commit wheel/sdist, rerun all required CI, CodeQL,
   clean-install checks, security review and license/attribution checks.
   Do not re-label #598's artifact as the output of a later head.
4. **Release packaging UX decision**: before calling this a downloadable
   *desktop app*, create/test signed or at least clearly unsigned platform
   installers and first-run UX, separately. A Python developer wheel can be
   distribution-ready without this claim.
5. **Deferred separate publication authorization**: only after preparation
   is accepted can the owner intentionally approve a tag, GitHub Release,
   PyPI/TestPyPI or HF operation. They are **not approved here**.

**Current truthful status:** `TECHNICAL_PREPUBLICATION_REHEARSAL_PASS` for
the bounded exact-SHA Core artifact; `INDEPENDENT_RELEASE_APPROVAL_PENDING`
for the overall package/release. **UNPUBLISHED**. No PHI or clinical use.
