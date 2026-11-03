# Core Wheel member CRC and Windows-name integrity — 2026-11-03

**Private nonpublishing MedOrigin Developer Beta Core evidence.** This branch stacks on #875 head `5627d2afeaa6fa55dfce2d5879013eaa3dcdc419`, and includes the earlier #874/#873 security work without editing protected `main`, UI, desktop or frozen research/lock/manifest files. No public tag, installer, registry upload, clinical use or release authorization was granted.

## Confirmed original false admissions

On Windows 11, the original immutable #875 base-scope guard returned `BASE_CORE_PUBLICATION_SCOPE_CLEAN` despite a syntactically readable Wheel containing:
- Files named `CON.txt`, `PRN`, `NUL.json`, `COM1.dll`, `LPT9.py`, `CONIN$.log`, `CONOUT$.log`, `AUX` or reserved name `AUX.txt` at root, and filenames with tab, newline or DEL control characters. These names are unsafe/colliding in relevant Windows filesystem semantics.
- An **unmodified and readable** `medscale-0.3.0.dist-info/METADATA` with a separate ZIP_STORED or ZIP_DEFLATED non-metadata member whose stored compressed bytes are corrupted, breaking the member's actual CRC/decompression. Local and central ZIP headers still agreed, so #869 header-binding could not alone detect payload corruption.

The second case was reproduced with a synthetic ZIP_STORED file. `zipfile.ZipFile.read("medscale/fictional.txt")` raised `BadZipFile: Bad CRC-32`, yet the original scope gate reported CLEAN. In an independent paired original-vs-new `git show` comparison at the same synthetic input: safe control CLEAN→CLEAN; reserved filename CLEAN→BLOCKED; control-character filename CLEAN→BLOCKED; corrupt non-metadata payload CLEAN→BLOCKED. In every case `publication_authorized=false`; this is a bug in *scope admission*, not evidence of a published affected artifact.

## Source changes

- `scripts/check_base_core_publication_scope.py` reuses the existing case-insensitive Windows reserved-device pattern from sdist in the Wheel member inventory. Wheel now rejects control characters (U+0000–U+001F and U+007F), reserved device basename components and previously blocked unsafe path forms. This keeps rules consistent across Wheel and TAR formats.
- After checking ZIP budgets, special members and physical local/central header consistency, it streams **every regular Wheel file** in fixed 64-KiB chunks and exercises actual decompression and CRC verification, rather than trusting CRC declarations or reading only METADATA. Declared per-member, total inflation and compressed/archive size limits are retained; a malformed member fails closed. Directory payload declarations are checked. No new dependency and no archive file is extracted or executed.
- `tests/test_base_core_publication_scope.py` adds 12 Windows-name/control-character cases, two CRC/corruption regressions (ZIP_STORED and ZIP_DEFLATED) and one clean compressed non-metadata positive case. Existing previous 70 scope tests remain.

## Actual Windows exact-source matrix

Final functional source HEAD `764416f83003c8e6bdaf7a70702e159dcd9de18e`, verified Git blobs production `75f2889d552da84e35de309c88201233ae22785d`, tests `9dc164191bd21efe99cf61a05eac816342ac0211`, from a separate owned Windows Git clone.

- **Python 3.11.15:** complete scope test module **85/85 PASS**, 7.06 sec, exit 0.
- **Python 3.12.13:** complete scope test module **85/85 PASS**, 8.72 sec, exit 0.
- **Python 3.14.7:** complete scope test module **85/85 PASS**, 7.73 sec, exit 0.
- Ruff check and format --check PASS on both changed Python files; `git diff --check` against base #875 PASS.
- All tests used actual interpreters; Python 3.11 and 3.12 reused existing pure-Python pytest 8.4.2 via temporary process-local Python 3.14 site-packages `PYTHONPATH`, disabled plugin auto-load, `--noconftest`. This is **not** independently installed per-version pytest or full repository hosted CI.

An intermediate functional SHA `2fbca84c9dae74b917cbc69d107269e5bae0b7a9` passed 85/85 on Python 3.14 but failed Ruff solely on two long exception tuples. These were formatting-only edits, followed by exact-head full 85/85 Python 3.11, 3.12, 3.14 and Ruff green at `764416f`.

## Actual built and clean-installed artifact qualification (free WSL/Linux ext4)

With preinstalled WSL Python 3.14.4, Git, `uv 0.12.21` and **no network builds/downloads**, used a local isolated ext4 Git clone of the exact functional SHA `764416f`, verified immutable research-root hashes, staged 254 source files from that Git commit, and built a real Wheel+sdist with `uv build --offline --no-create-gitignore`.

- Actual Wheel `medscale-0.3.0-py3-none-any.whl`, SHA256 `db3aa492df0d9cfcff0a8f06f5f1e49560eb16b26416256fd1ee055907a1def5`.
- One exact-build sdist `medscale-0.3.0.tar.gz`, SHA256 `041dd30167b2d0bd8757f33112794f098e7970728927bb68c8bd9ab1bd3844f4`. Other local builds of the same source yielded **different sdist hashes**, so byte-for-byte sdist reproducibility is **not** established; do not reuse this digest as an immutable release receipt without investigation.
- Source-bound Wheel checker EXIT 0 / `SOURCE_BOUND_WHEEL_QUALIFIED_ONLY`. Source-bound sdist checker EXIT 0 / `SDIST_SCOPE_QUALIFIED_ONLY`. Hardened base publisher gate EXIT 2 / `BLOCKED` due unqualified optional extras and runtime dependencies, `publication_authorized=false`. There was no false ZIP CRC/member rejection on the genuine built Wheel.
- In a task-owned isolated Python 3.14.4 virtual environment, `uv pip install --offline --no-deps --link-mode=copy` installed **exactly one package**, `medscale==0.3.0` (260 distribution files). `medscale --help` and `medscale fhir --help` both exited successfully. No optional inference/research dependencies, external validator or service was installed.
- A follow-up installed CLI smoke with a synthetic FHIR `Bundle` (`type: collection`, no patient records) wrote a content-addressed report `status=valid`, exit 0. **Important limitation discovered:** a made-up `resourceType=UnknownFictionalResource` also returned `status=valid` and exit 0. Source `src/medscale/fhirkit/validate.py::validate_fhir` sets `status="valid"` unconditionally and does not perform FHIR R4 schema, terminology or profile validation. Treat local FHIR reports as deterministic boundary/provenance outputs, **not as proof of FHIR conformance**. A separate contract correction/security disposition is required before claiming real validation or clinical suitability.

Each Linux run's source/artifacts/venv were held only under a distinct temporary `/tmp` path with verified automatic cleanup. No external dataset, PHI/EHR, paid compute, model training, cloud instrumentation, signing or publishing was used.

## Release disposition

**NO-GO.** Exact-new-HEAD hosted 20-job CI, independently attributable source/artifact security review #603, unapproved optional extras/advisories #622, ADR-0045 version/source policy and owner release authority #574, the FHIR local boundary truthfulness noted above, and desktop OS safety gates #662/#673/#676 all remain. Preserve source identity and known historical research bytes. No main merge, tag, release, TestPyPI/PyPI, clinical assertions or public distribution. `publication_authorized=false`.
