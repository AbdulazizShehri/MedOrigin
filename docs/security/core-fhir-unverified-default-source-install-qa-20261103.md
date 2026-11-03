# MedOrigin Core — fail-closed local FHIR truthfulness (2026-11-03)

**Status: PRIVATE SOURCE-ONLY CANDIDATE, NO-GO FOR PUBLIC OR CLINICAL RELEASE.** Linked to confirmed correctness blocker [#877](https://github.com/AbdulazizShehri/MedOrigin/issues/877). This candidate branch is stacked on private Wheel/security PR #876 at immutable parent `146b59aa08a41eb8f12fcf4d2a4bd795f65f22c6`; source tests and installed distribution were executed without external services or patient data.

## Demonstrated bad previous contract

In an actual clean isolated Python 3.14.4 `uv` virtual environment containing only the offline-built `medscale==0.3.0` Wheel from Core source `764416f83003c8e6bdaf7a70702e159dcd9de18e`, `medscale fhir validate` returned **exit 0, status `valid`, no errors and no warnings** for both a simple fictional FHIR Bundle and a made-up `resourceType=UnknownFictionalResource`. The command created content-addressed reports in both cases. No actual schema/terminology/profile checking took place.

The source `src/medscale/fhirkit/validate.py::validate_fhir` previously calculated a deterministic content hash, then **unconditionally** returned `ValidationReport(status="valid", errors=(), warnings=())`. The CLI's optional external-validator command remains **unimplemented** and returned exit 2; the local always-success result was a misleading FHIR conformance signal. Historical M5 documentation intentionally calls this an optional-validator deterministic **boundary**, not a full validator. This is not evidence any PHI or EHR was processed.

## Bounded mitigation, explicit compatibility change

- `src/medscale/fhirkit/validate.py`: local boundary now returns `status="not_validated"`, `errors=()`, and a fixed warning stating that FHIR R4 schema, terminology and profile validation were **not performed** and only deterministic provenance was recorded. The input SHA-256/content-addressed storage contract remains; the old no-op self-comparison of `canonical_json` was removed. **No substitute inference or invented lightweight schema validator.**
- `src/medscale/cli/fhir.py`: label the existing default truthfully. Preserve `--summary-only` exit 0 for an explicit no-validation JSON display, preserve the existing `--with-validator` unsupported/exit-2 behavior, write deterministic local provenance reports, but return **exit 2** rather than 0 from `medscale fhir validate` when full validation has not run.
- Tests `tests/test_fhirkit.py` and `tests/test_fhir_cli.py` check that both a known fictional FHIR structure and an invented resource type remain `not_validated` with a warning, no claimed error-free FHIR conformance and actual stored report. The existing public CLI entrypoint and summary-only legacy compatibility remain.
- **Compatibility impact:** this intentionally changes the local report `status` from `valid` and CLI success return 0 to `not_validated` and exit 2. Consumers relying on the old result must be explicitly reconciled/retested before any protected integration. It does **not** rehash or overwrite historical reports, frozen research inputs, or evidence. The report format v1 schema is unchanged; status is a free string in existing `ValidationReport`.
- An actual validator integration, offline FHIR R4 conformance fixtures and independent trust qualification remain separate future work; neither an invented `resourceType` nor a valid-looking one is certified by this mitigation.

## Exact Windows source-backed test matrix

Final tested functional SHA `96f76adf0dfe618a3095001092f8e5b716dbc88a`, in a task-owned standalone full private Git clone. Local-validator source Git blob `ec96396f094dd0f32b42bca362a518749aa13695`; CLI source Git blob `745c48b1ee0a67a3fa89bed2b9f08a52b9256021`.

- Python **3.11.15**: `tests/test_fhirkit.py` + `tests/test_fhir_cli.py`, **26 passed / 2 deselected**, exit 0, 1.37 sec.
- Python **3.12.13**: **26 passed / 2 deselected**, exit 0, 1.82 sec.
- Python **3.14.7**: **26 passed / 2 deselected**, exit 0, 1.83 sec.
- Two existing network-sensitive/standalone packaging fixture tests requiring `uv` executable and `pip install` were **deliberately deselected** on Windows. The actual installed-Wheel journey below supplies separate offline installation evidence; do not claim 28/28.
- Ruff lint, Ruff format --check (all four changed Python files), and `git diff --check` against parent **PASS**.
- Python 3.11/3.12 pytest8.4.2 was borrowed temporarily from the existing Python3.14 pure-Python site-packages with plugin auto-load disabled; `--noconftest` excluded global research fixtures. These are focused source tests, **not** independent full CI or hermetic per-version venvs.

## Real installed-Wheel fail-closed CLI E2E (WSL ext4)

A fresh local `/tmp` ext4 Git clone of identical functional SHA `96f76adf0dfe618a3095001092f8e5b716dbc88a` staged source from exact committed Git with the frozen trust-root SHA checks, built Wheel+sdist via preinstalled `uv build --offline --no-create-gitignore`, then installed **only** the resulting Wheel into an isolated Python 3.14.4 `uv venv` with `uv pip install --offline --no-deps --link-mode=copy`. No package registry, optional external validator, model, paid inference or other dependencies.

- Wheel SHA256 `b0fda9434168b10c271973c449b93c2ef9bed70692dcc2c1e76c85194cc85fa1`. This one offline build's sdist SHA256 `fff72ece8770701d569f5ffe0ad8fcc35f8cc8baea7ceeed41147e9261ed08a3`; cross-build byte reproducibility of sdist **not established**.
- Source-bound Wheel verifier **EXIT 0**; source-bound sdist verifier **EXIT 0**; hardened base publisher gate **EXIT 2** correctly for unresolved optional extras/runtime dependency policy. `publication_authorized=false`.
- From the **installed CLI**, running `medscale fhir validate` on a fictional empty `Bundle(type=collection)` and on `{"resourceType":"UnknownFictionalResource","id":"synthetic-negative"}` separately produced **exit 2 in both**, stored one content-addressed report each, and both JSON outputs had `status="not_validated"`, one explicit warning, and empty `errors`. Their input hashes differed, confirming payload distinction. The synthetic files had no patient records/identifiers.
- `medscale fhir validate --summary-only <fictional-bundle>` retained exit 0 and returned normalized input JSON without pretending to validate.
- Final command EXIT **0** after asserting the two expected nonzero validation results, report status, report persistence and summary-only compatibility. Temporary `/tmp` source/build/venv/report files were cleaned by a task-owned shell trap.

## Remaining blockers

Actual FHIR R4 schema, terminology, profile validation integration and negative corpus are **not delivered**; #877 stays open for this scope and compatibility/security acceptance. Source candidate is not clinically qualified. Other release NO-GO: package/version and ADR-0045 owner governance #574, unsafe optional extras #622, independent #603 review, hosted exact-new-head full CI, and separate native desktop #662/#673/#676. No protected-main merge, tag, release, installer, TestPyPI/PyPI, real PHI/EHR or model-training work. This is a private Draft candidate only.
