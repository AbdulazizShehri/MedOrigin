# MedOrigin Core — immutable FHIR report storage / traversal refusal QA

**Date:** 2026-11-04 Asia/Riyadh  
**Status:** PRIVATE DRAFT / local synthetic-only Core software security fix. **NOT a FHIR R4 validator, independent security approval, clinical-use authorization, merge or release GO.**

## Source identity and scope

Stacked on private Draft #901 exact base Git SHA `ad0c62b4366789f5c7e41fc601bb6d0f9d640873`. Private branch `security/medorigin-fhir-immutable-report-path-20261104`; **actually tested functional source SHA `f08021517974b1cebe6643c554f6bdaecb603a0c`**. Exactly three functional source-controlled files changed: `src/medscale/fhirkit/storage.py`, `src/medscale/cli/fhir.py`, new `tests/test_fhir_storage_file_integrity.py`, plus this evidence document. This is a **real non-UI packaged Core storage fix**; therefore previous Wheel binary digests, source qualification receipts and exact-head CI cannot be reused as release approval. No native desktop/UI, frozen root `pyproject.toml`/`uv.lock`, MRL research artifacts/receipts, publisher/release workflow, protected main or registry modified.

## Two real defects reproduced on original parent source — entirely fictional files

1. **Hard-link overwrite:** Existing `store_report()` used `Path.write_text()` unconditionally at `fhirkit/reports/<report-hash>/report.json`. In a task-owned local Windows temp directory, prepared a **hard link** from that intended report path to a second, separately named `fictional-victim.txt` containing an innocuous ASCII sentinel. When storing the synthetic report, the original implementation changed the separate file's contents. The two paths had link count=2; this is a demonstrable local filesystem overwrite flaw. It does not require PHI to reproduce and does not demonstrate exploiting other users' files without writable shared directory permissions.
2. **Report-hash path traversal:** Original `load_report(report_hash_value)` interpolated the caller-provided string directly into a filesystem path without validating it. In a task-only root with a file `unreviewed-file/report.json` outside `fhirkit/reports`, calling `load_report("../../unreviewed-file",root=...)` read the outside file on native Windows. All contents fictional. Initial attempted test used the wrong number of parent segments and was corrected before the confirmed reproduction.

The parent CLI also propagated storage exceptions through a Python traceback on refusal, potentially exposing filesystem paths. This patch redacts the CLI refusal to a fixed label and does not emit a positive report when storage is blocked.

## Surgical fix

`store_report()` is now **exclusive-create, never overwrite**: `os.open(... O_CREAT | O_EXCL | O_WRONLY, mode=0600)`, write/flush/fsync and close. Existing report path may only be returned if it is a regular **single-link** file with byte-for-byte identical canonical JSON; it is returned **without rewriting**. A missing, corrupt, changed, symlinked, hard-linked, nonregular or mismatching file refuses with `FhirStorageError`; it is **never silently repaired, replaced, truncated or deleted**. All report directories are pre/post-checked for symbolic links and Windows junctions. The `report_hash` must be canonical lower-case 64-hex SHA-256.

`load_report()` accepts **only** canonical lower-case 64-hex identifiers, refuses linked paths and nonregular/hard-linked target files, verifies canonical JSON contents round-trip and compares the reconstructed `report_hash()` with the directory ID. A well-formed but altered stored report is now rejected rather than returned. The CLI catches `FhirStorageError` from report storage, exits **2**, prints only `FHIR_REPORT_STORAGE_BLOCKED` to stderr and **no positive FHIR report** to stdout. No third-party libraries added.

**Important trust boundary:** this is fail-closed for normal local filesystem artifact safety on reviewed Windows/Linux hosts. `Path` component symlink checks are pre/post-flight; the code does **not** provide a directory-fd/handle-relative, race-free defence against a malicious concurrently writing process swapping intermediate directories (TOCTOU), nor does it establish OS ACL confinement or a genuine HL7 FHIR R4 schema/profile/terminology validator. If attacker-controlled shared write access to the output directory is in scope, #603 must require an OS-level confinement/handle-based design. Do not describe it as independently audited or clinically fit.

## Source-controlled tests and cross-platform proof

New adversarial tests cover: first create, byte-identical idempotent reuse without mtime update, corruption preservation, hard-link overwrite refusal preserving the other file, valid bytes with hard-link still rejected, 11 malicious/noncanonical identifiers including `..` and Windows backslash variants, real traversal read blocked, linked parent and linked final report, nonregular report path, malformed/missing report, modified canonical JSON mismatch, and CLI no stdout/traceback/absolute-path leakage on storage refusal.

Nine non-UI Core source test modules including new file plus `test_core_installed_python_interpreter.py`, `test_core_installed_console_launcher.py`, `test_core_source_bound_fhir_provenance.py`, `test_installed_core_fhir_provenance.py`, `test_fhirkit.py`, `test_fhir_cli.py`, `test_base_core_publication_scope.py`, `test_medorigin_prepublication_rehearsal.py` at functional SHA:

| Native Windows Python | PASS | SKIP | DESELECTED | Exit |
|---|---:|---:|---:|---:|
| 3.11.15 | **284** | 4 | 2 | 0 |
| 3.12.13 | **284** | 4 | 2 | 0 |
| 3.14.7 | **284** | 4 | 2 | 0 |

**852 passed total**, no failing cases, Ruff lint/format and Git diff--check PASS. Four skips per interpreter are Windows symlink privilege limitations; two old standalone Wheel fixture cases per interpreter intentionally deselected. Python3.11/3.12 reused preinstalled pure Python pytest via ephemeral `PYTHONPATH`, disabled plugin auto-loading and `--noconftest`: **not** a hermetic per-version install or hosted full CI.

The same fixed source was independently tested using **real Linux WSL/ext4** with Python3: genuine symlinked target store/load both refused, hard-link overwrite refused, symlinked parent directory refused with no outside directory mutation, and ordinary canonical store/load roundtrip passed. Task-only temporary Linux directory automatically cleaned.

## Actual Git-bound offline distribution and native Windows installed Wheel

Isolated WSL/ext4 Git clone of precise functional source SHA **`f08021517974b1cebe6643c554f6bdaecb603a0c`** staged approved read-only Core projection, built genuine `medscale==0.3.0` Wheel and sdist **offline**, independently matched both to this exact Git SHA (source identity exit0). Publisher's policy gate still **exit2/BLOCKED** because unsafe unqualified research optional extras remain in metadata. This source change modifies actual production Wheel bytes: do **not** reuse any earlier Wheel SHA or old CI receipt.
- Exact new source-bound Wheel SHA256 **`29bc1cf99a1b2ffbcdec13606cdf72159a50141ec71891cf4ed2c42d267f1187`**.
- Exact new source-bound one-build sdist SHA256 **`b6b4295d81ee28648b972b5647692bb2c78a1c657fe7926d1d393b558096cd95`**.

Installed this same Wheel without downloading dependencies into **two real isolated native Windows stdlib venvs**, Python3.11.15 and Python3.12.13, via existing Python3.14.7 pip26.2.1 using `--python`, `--no-index --no-deps --no-compile`. Each installed Wheel, invoked via its installed interpreter `-I -B`, **actually refused hard-link overwrite, rejected report-ID traversal and tampered canonical JSON, preserved identical-existing reports**, and invoking its real `Scripts/medscale.exe` against an intentionally corrupt synthetic report path returned CLI exit2 with only fixed redacted error and no positive stdout. No PHI, network, external model or clinical validation.

**Honest diagnostic correction:** the first attempt to run the strict source-to-installed qualifier on the *same* venvs **failed EXIT2** for `unqualified installed Core package directory`: the manual installed console CLI smoke had already created `__pycache__` under the package, which the existing strict provenance verifier correctly treats as unqualified. This is **test-environment contamination**, not success or a source-runtime regression. Recreated **two separate fresh task-only venvs with `pip --no-compile`**, verified zero caches **before** any manual CLI smoke, and on these fresh Windows3.11/3.12 installations the complete exact-Git→Wheel/sdist→2 pinned Python executables+4 base runtime DLLs each→startup-hook checks→250 complete installed Core files/249 Python source files per runtime→both pip26.2.1 RECORD-bound installed console PE templates→FHIR `not_validated` provenance gate returned **exit0 TWICE**, with zero new package bytecode caches after either run. All vendor source signature, independent audit, actual FHIR conformance, clinical use, merge/tag and publication authority booleans explicitly remain false.

## NO-GO / still incomplete

- This work is a new source change with **no latest-HEAD hosted 20-job CI/CodeQL**; old-green hosted CI cannot qualify it. All work is private Draft only.
- Independent security review/OS filesystem concurrency ACL/DLL and signer checks #603 and #893 remain OPEN.
- Base publisher still deliberately BLOCKED by #622 optional dependency advisories and owner ADR/version/release authority #574. Doc-only Draft #903 is a **proposed, not accepted** metadata-isolation ADR; do not bypass source identity.
- Actual FHIR R4 schema/profile/terminology validation #877 still unavailable. This local CLI reports `not_validated` and exits2, not clinical or schema conformance.
- Existing Developer Beta/static preview incompatible old `valid` receipt #882 and native desktop #662/#673/#676 belong to separate UI agent and are independent gates.

**No protected main merge, release/tag/signing/installer/PyPI/TestPyPI publication, live EHR/PHI, clinical claims, frozen research/lock changes or other-agent UI/native desktop modifications.** The software release is still NO-GO.
