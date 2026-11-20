"""Owner Windows: exact Core979 reference guard and official R4 to native HMAC worklist.

Only two Core-generated invented Bundles may be imported. The independent
source-only preflight first proves that cross-person Observation/Encounter
references are rejected regardless of entry ordering. NOT production/clinical.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import launch_windows_real_core971_official_r4_fictional_batch as r4

CORE979_SHA = "440cee21494a62c458106631931f3610c05d1ea8"

# Offline, read-only, stdout/stderr-free check against the actual pinned
# Core979 interpreter/module paths. Deliberately contains only invented FHIR
# resources and no user-controlled file, patient or endpoint options.
_CROSS_PERSON_PROBE = """
import copy, sys
from pathlib import Path
source=Path(sys.argv[1])
sys.path[:0]=[str(source/'src'), str(source/'apps'/'workspace'/'src')]
from medscale.fhirkit.bundle import BundlePreflightError, inspect_synthetic_bundle
from medscale.fhirkit.workspace_demo import _fictional_bundle

valid=_fictional_bundle()
person=copy.deepcopy(valid['entry'][1])
person['fullUrl']='urn:uuid:00000000-0000-4000-8000-000000000004'
person['resource']['id']='fictional-patient-002'
person['resource']['name'][0]['text']='INVENTED_PRIVATE_NAME_NEVER_LOGGED'
visit=copy.deepcopy(valid['entry'][2])
visit['fullUrl']='urn:uuid:00000000-0000-4000-8000-000000000005'
visit['resource']['id']='fictional-encounter-002'
visit['resource']['subject']['reference']=person['fullUrl']
lab=copy.deepcopy(valid['entry'][0])
lab['fullUrl']='urn:uuid:00000000-0000-4000-8000-000000000006'
lab['resource']['id']='fictional-observation-002'
lab['resource']['subject']['reference']=person['fullUrl']
lab['resource']['encounter']['reference']=visit['fullUrl']
valid['entry'].extend([person,visit,lab])
for entries in (valid['entry'],list(reversed(valid['entry']))):
    good={**valid,'entry':copy.deepcopy(entries)}
    result=inspect_synthetic_bundle(good)
    if result['resource_count']!=6 or result['clinical_use_authorized'] is not False:
        raise SystemExit(19)
    bad=copy.deepcopy(good)
    for entry in bad['entry']:
        if entry['resource']['id']=='fictional-observation-002':
            entry['resource']['subject']['reference']=valid['entry'][1]['fullUrl']
    try:
        inspect_synthetic_bundle(bad)
    except BundlePreflightError as exc:
        if str(exc)!='observation_encounter_patient_mismatch':
            raise SystemExit(20)
    else:
        raise SystemExit(21)
"""


def _require_guarded_core(source: Path) -> Path:
    source = r4._attest_core(source, required_core_sha=CORE979_SHA)
    if not (source / "tests/test_workspace_guarded_sha256.py").is_file():
        raise ValueError("guarded_core979_sha_boundary_missing")
    try:
        result = subprocess.run(
            [sys.executable, "-B", "-c", _CROSS_PERSON_PROBE, str(source)],
            cwd=source,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            capture_output=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError("guarded_core979_cross_patient_probe_unavailable") from exc
    if result.returncode != 0 or result.stdout or result.stderr:
        # Never relay source paths, invented names or raw Python exceptions.
        raise ValueError("guarded_core979_cross_patient_preflight_refused")
    # Verify the source boundary again after the independent child probe.
    return r4._attest_core(source, required_core_sha=CORE979_SHA)


def launch(
    source: Path,
    exe: Path,
    sha: str,
    archive: Path,
    *,
    qa_auto_close: bool = False,
    qa_uia: bool = False,
) -> None:
    if sys.platform != "win32":
        raise ValueError("guarded_core979_windows_host_required")
    if qa_auto_close and qa_uia:
        raise ValueError("guarded_core979_qa_mode_conflict")
    # Confirm Core979 correctness BEFORE any encrypted import or GUI launch.
    source = _require_guarded_core(source)
    # Reuse the already-qualified exact legacy Core971/979 receipt parser,
    # official HL7 v4.0.1 source pin, per-launch HMAC and native GUI UIA.
    r4.launch(
        source,
        exe,
        sha,
        archive,
        qa_auto_close=qa_auto_close,
        qa_uia=qa_uia,
        required_core_sha=CORE979_SHA,
    )
    print("GUARDED_CORE979_CROSS_PATIENT_PROBE_AND_R4_HMAC_WORKLIST_PASS_NONCLINICAL")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-source", type=Path, required=True)
    parser.add_argument("--native-exe", type=Path, required=True)
    parser.add_argument("--native-sha256", type=str, required=True)
    parser.add_argument("--offline-r4-schema", type=Path, required=True)
    parser.add_argument("--qa-auto-close", action="store_true")
    parser.add_argument("--qa-uia", action="store_true")
    try:
        options = parser.parse_args()
        launch(
            options.core_source,
            options.native_exe,
            options.native_sha256,
            options.offline_r4_schema,
            qa_auto_close=options.qa_auto_close,
            qa_uia=options.qa_uia,
        )
    except (ValueError, OSError, ImportError) as exc:
        # A fixed denial code only. Do not print filenames/PHI or raw traceback.
        print(
            "GUARDED_CORE979_R4_HMAC_NATIVE_NO_GO:" + str(exc),
            file=sys.stderr,
        )
        raise SystemExit(2) from None
