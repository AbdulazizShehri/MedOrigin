# MedOrigin D2 — exact-blob Python regression execution (2026-11-03)

**Result: 17/17 PASS, process exit 0, two independent invocations on Python 3.13.5. This qualifies the source-only Python regression suite, NOT the native D2 build, OS egress, clinical use or release.**

## GitHub provenance

At the moment of test input capture and after both executions, private Draft PR [#865](https://github.com/AbdulazizShehri/MedOrigin/pull/865) was open, unmerged, and had exact HEAD `55e955838c7d2c25d4f8ce44c031bba098b42d66`.

Files were retrieved **individually through the connected private GitHub account**, reproduced byte-for-byte in a clean isolated local working directory, and validated using Git's exact blob hash algorithm **before executing any tests**. The local `git hash-object` results matched GitHub's independently returned content SHA:

| Source-controlled relative test file | Exact verified Git blob SHA |
| --- | --- |
| `tests/verify_d2_fixture_catalog.py` | `ffe9429f5b5977066e5cdd07c4fc04bcb107487f` |
| `tests/test_verify_d2_fixture_catalog.py` | `9691a7f3f0b46d88fa4a68fc63628efda6fdc877` |
| `tests/test_verify_d2_fixture_catalog_tree.py` | `fec742aefa4278d51ed56b787e85bd97b0e416a0` |

No changes or mock alterations were introduced into these three files for the test run. The local environment had **Python 3.13.5**, but no `cargo` or `rustc` and no access to the private full Git checkout over the network. No Windows Desktop Commander calls were attempted; prior device monthly quota remains a separate blocker.

## Reproducible command and actual observed result

Executed in a directory containing exactly the three SHA-verified test files:

```bash
python -m unittest discover -s . -p 'test_verify_d2_fixture_catalog*.py' -v
```

First run: **17/17 tests PASS**, exit 0, in approximately 0.017 seconds. Repeated independently with stdout/stderr captured: **17/17 PASS**, exit 0, in approximately 0.013 seconds. Summary printed by the actual Python `unittest` runner:

```text
----------------------------------------------------------------------
Ran 17 tests in 0.013s

OK
EXIT_CODE=0
```

All eight source-helper negative tests passed: clean fixed Patient, same-length modified raw bytes, wrong raw length, forged SHA-256, forged synthetic envelope status, bogus non-JSON preview, duplicate D0 literal, and incomplete D2 fixture list. All nine temporary synthetic D0/D2 tree tests passed, covering: unmodified 12-fixture tree, corrupted Bundle fixture bytes, substituted Observation byte-dispatch, altered resource limit, changed resource-size dispatch, modified invalid UTF-8 byte, changed oversize filler, changed exact-limit padding, and reorder of two otherwise SHA-correct catalog entries. Temporary test trees were created and deleted by Python `TemporaryDirectory` cleanup.

## Explicit boundaries

These tests exercise the **actual exact GitHub-source Python code** on synthetic local trees. They do **not** execute the `verify_d2_fixture_catalog.py` full-repository command over all original D0 Rust literals, six real Bundle JSON files and actual D2 app source in one complete local checkout. The prior independent 12/12 SHA audit read those genuine source files through GitHub, but that is a *different* measurement. No `cargo test`, `cargo fmt`, `cargo clippy`, Windows UIAutomation, Linux AT-SPI, macOS VoiceOver, WebView2 WFP/DNS/TCP/UDP denial, hosted exact-HEAD CI, independent security sign-off, PHI workflows, clinical FHIR validation, signing, protected-main merge, installer, binary publishing or release occurred.

**Release status remains NO-GO** pending #662 (Windows D1 egress), #673 (Linux AccessKit/zbus), #676 (spoken VoiceOver), #622 (optional research dependencies), #603 (independent review), and #574 (owner release authorization). This evidence is for engineering continuity only.
