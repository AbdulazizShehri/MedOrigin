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

### Exact-HEAD v0.3.0 QA ZIP (single-source handoff)

The earlier, preserved two-source QA ZIP uses Core #598 plus separate
#617 example source and intentionally remains verifiable by the original
`verify_medorigin_qa_handoff.py` and `assemble_medorigin_unpublished_qa.py`.
**Do not re-label or silently rewrite that historical bundle.**

For the **exact, already qualified Developer Beta source** at
`62870f7f55848d289f78941b862092b9a0f366a0` (Draft #617), use the
new `scripts/assemble_medorigin_exact_head_qa.py` instead. It
requires the pre-built, separately source-qualified Wheel, sdist, and
source-provenance receipt from *that same* Git commit, checks their
literal known SHA-256 digests, includes only eight synthetic FHIR
examples and legal notices from the pinned Git tree, and independently
pins **all 15 source, executable-example, provenance and artifact SHA-256
values** in the verifier rather than trusting the ZIP's mutable checksum
list. It then produces an
unpublished, deterministically ordered 16-member ZIP. It refuses
unexpected members, falsified review/publication flags, duplicate or
symlink archive entries, mutated artifact/provenance hashes, and
accidental overwrites. The standalone verification action does not
extract or execute the ZIP and can compare it to a trusted external
ZIP SHA-256. The QA assembly tool may reside on a **later tooling-only
commit**; its product source identity remains the earlier, explicitly
pinned #617 SHA rather than pretending the new tooling was included
in the Core Wheel.

```powershell
python scripts/assemble_medorigin_exact_head_qa.py build C:/path/to/empty-output/MedOrigin-v0.3.0-62870f7f-Developer-Beta-UNPUBLISHED.zip --artifacts C:/path/to/exact-head-dist --provenance C:/path/to/exact-head-projection/MEDORIGIN_SOURCE_PROVENANCE.json
python scripts/assemble_medorigin_exact_head_qa.py verify C:/path/to/empty-output/MedOrigin-v0.3.0-62870f7f-Developer-Beta-UNPUBLISHED.zip --expected-sha256 bb82d997d80dc8d037b2a83ad652db5c4837dd7a7a824bb7ec978781c2ad2503
```

The SHA example above refers to the original Windows exact-HEAD QA ZIP
already reproduced and verified at this exact Git source. A future
candidate revision needs **new** exact source, artifact hashes,
independent review and a new assembler contract: do not reuse this
pinned script for changed software sources. It does **not** create a
standalone signed desktop installer or authorize publishing.

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

## Security boundary for optional inference/training extras — 2026-10-25

**The qualified v0.3.0 Developer Beta is the base, synthetic-only Core
installation.** Optional inference/training extras are **NOT SECURITY-QUALIFIED**
and are NOT authorized as part of this beta handoff.

The exact, source-bound Wheel `medscale-0.3.0-py3-none-any.whl`
(SHA-256 `a718b77794c817dfcf6a711cd97324b3626e4d65382ba39c670a7c303fae07e7`)
has **no unconditional `Requires-Dist`**. Its optional research and training
metadata nevertheless advertises `pillow==12.3.0` and
`accelerate==1.14.0` when selected extras are installed. Neither library
was installed in the clean, offline, base Core Python 3.11/3.12 rehearsals.

Free `pip-audit==2.10.0` queries on the 11 direct, exact-pinned optional
dependencies returned advisories in **two** packages:

- **Pillow 12.3.0**: multiple confirmed upstream security fixes, including
  critical/high image-decoder problems, are shipped in **Pillow 13.0.0**
  (2026-10-16). See the
  [upstream security release notes](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html).
- **Accelerate 1.14.0**: the
  [PYSEC-2026-3804 advisory](https://osv.dev/vulnerability/PYSEC-2026-3804)
  documents checkpoint `weight_map` path traversal/file-read and DoS
  behavior. A safe replacement version is **not yet qualified** in MedOrigin.

The free PyPI advisory service returned 38 vulnerability **records** and OSV
returned 43 across the same two packages, **not necessarily that many distinct
or applicable CVEs** (some records/aliases overlap). The scan intentionally
did **not** resolve optional transitive dependencies, two range-only extras,
their platform wheels, licenses or execution paths. See
[security follow-up #622](https://github.com/AbdulazizShehri/MedOrigin/issues/622)
and [disabled Dependabot alerts #621](https://github.com/AbdulazizShehri/MedOrigin/issues/621).

**Policy:** Do not install or advertise these extras as safe/qualified for
the Developer Beta. Do not change the frozen `pyproject.toml`, `uv.lock`,
canonical MRL manifests, historical `v0.2.0` receipts, or published project
metadata to remove alerts. Any amended isolated packaging projection that
removes or updates dependency metadata exceeds the currently accepted
ADR-0044 four-URL transformation, and needs a **separate, explicit governance
decision and exact-source package requalification**. Independent security
review #603 remains outstanding. Base Core technical PASS is not a claim of
overall release authorization or of optional-extras security.

## Outstanding preparation — distinct from the later publish button

1. **Independent release-boundary review #603**: review exact candidate
   source-to-wheel/sdist/provenance, hostile archives, release workflow trust,
   redistribution, and persisted-format decisions. Author-run testing and
   CodeQL do not count as the external/independent reviewer receipt.
2. **Owner decision #574 / ADR-0044 (completed 2026-10-25)**: route B,
   the isolated, read-only Core projection, is **Accepted**; retain unchanged
   frozen research root/lock/MRL bytes. The package/version/branding and
   optional-extras security limitations above remain explicit. Any new
   dependency-metadata transformation requires a separate approved change;
   do not revive the successor-root mutation without reconciliation.
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
