# Python dependency advisory floor remediation — private Draft, 2026-11-05

## Scope

The GitHub Dependabot API reported **66 open default-branch uv.lock alerts**, grouped as Pillow 41, filelock 9, aiohttp 8, urllib3 3, and one each in certifi, setuptools, multidict, accelerate and diskcache. The retrieved advisories identified fixed releases for **seven packages representing 64 of 66 alerts**. No patched release was available in the retrieved metadata for accelerate or diskcache. These were alerts on the default branch, and are **NOT closed** by an unmerged private PR.

Pinned Pillow in optional rq1-runtime-feasibility is changed from 12.3.0 to **13.0.0**. The UV resolver updated other transitive dependencies: filelock 3.29.7 to **4.2.9** (patch floor 4.2.1), aiohttp 3.14.3 to **3.14.5** (floor 3.14.4), multidict 6.7.1 to **7.2.1** (floor 6.9.1), urllib3 2.7.0 to **2.8.0** (floor 2.8.0), certifi 2026.6.17 to **2026.10.23** (floor 2026.10.18), setuptools 84.0.0 to **84.2.1** (floor 84.1.0), and compatibility dependency yarl 1.24.5 to **1.25.1**.

## Qualification and limits

- uv lock --upgrade-package resolved **103 packages**, and uv lock --check **PASS** for the Python 3.11–3.14 multiplatform lock.
- Offline stdlib scripts/verify_python_lock_security_floor.py checks the patch floor on **every locked package record**, rejects stale variant entries and an old Pillow project constraint. Local regression tests: **16 PASS**. Ruff check and format of new source/tests: **PASS**.
- Actual installed **Windows CPython 3.14.7** binary wheels for all eight updated packages were isolated under a task-only directory and tested **PASS**: in-memory synthetic Pillow PNG roundtrip, aiohttp ClientSession create/close without requests, filelock temporary lock, multidict header, yarl local URL parsing, certifi bundle path, urllib3 PoolManager construction without requests, setuptools import. All eight runtime versions matched the new lock. The same eight patched packages were also installed in a disposable WSL/Linux CPython 3.11 virtual environment; source-linked version checks, in-memory synthetic Pillow PNG roundtrip, local aiohttp session, URL/header parsing and imports **PASS** with marker MEDORIGIN_LINUX_PY311_PATCHED_LOCK_EIGHT_PACKAGES_SMOKE_PASS. Lock SHA256 at this check: 59e2f783befeca4b6e3586ddfc62dab3f04594d607bcc5348fcd23388c4349c1.
- A lightweight event-triggered GitHub workflow checks the lock floors with Python stdlib only, no package installation or external API call. Its hosted results are separate from local test claims.

**Unqualified:** model-heavy optional Torch/Transformers training extras, entire clinical Core, macOS/Windows 3.11 and other wheel targets unless independently tested, an exhaustive CVE scan, third-party licenses or production risk acceptance. Pin updates may have behavior changes requiring deep model/clinical integration tests. An unresolved advisory must not be dismissed to get a green dashboard.

**NO-GO:** Owner-private Draft; no deploy, paid service, public package, main merge, clinical source, protected patient data or release authority. Accelerate and diskcache advisories remain visible until a vendor fix or independently approved removal/isolation strategy. Only future default-branch scanner re-evaluation can prove alert closure.