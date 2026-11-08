"""Build deterministic in-repo FICTIONAL Bundle fixtures only; no external input."""

import hashlib
import json
import sys
from copy import deepcopy
from pathlib import Path

folder = Path(__file__).resolve().parents[1] / "fixtures"
if sys.argv[1:] not in ([], ["--check"]):
    raise SystemExit("usage: generate_fictional_bundles.py [--check]")
check_only = sys.argv[1:] == ["--check"]
patient = {"resourceType": "Patient", "id": "synthetic", "active": True}
observation = {
    "resourceType": "Observation",
    "id": "synthetic-observation",
    "status": "final",
    "code": {"coding": [{"system": "urn:synthetic:code", "code": "fictional-measurement"}]},
    "subject": {"reference": "Patient/synthetic"},
    "valueQuantity": {"value": 37, "unit": "fictional"},
}
entries = [
    {"fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000001", "resource": patient},
    {"fullUrl": "urn:uuid:00000000-0000-4000-8000-000000000002", "resource": observation},
]


def bundle(e, kind="collection"):
    return {"resourceType": "Bundle", "id": "synthetic-bundle", "type": kind, "entry": e}


valid = bundle(deepcopy(entries))
bad = deepcopy(valid)
bad["entry"][1]["resource"]["subject"]["reference"] = "Patient/absent"
linked = deepcopy(valid)
linked["entry"][1]["resource"]["subject"]["reference"] = (
    "urn:uuid:00000000-0000-4000-8000-000000000001"
)
dangling = deepcopy(linked)
dangling["entry"][1]["resource"]["subject"]["reference"] = (
    "urn:uuid:00000000-0000-4000-8000-000000000099"
)
dupe = deepcopy(valid)
dupe["entry"][1]["fullUrl"] = "urn:uuid:00000000-0000-4000-8000-000000000001"
for name, data in [
    ("bundle-valid", valid),
    ("bundle-bad-reference", bad),
    ("bundle-duplicate", dupe),
    ("bundle-wrong-type", bundle(deepcopy(entries), "transaction")),
    ("bundle-linked", linked),
    ("bundle-dangling", dangling),
]:
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    target = folder / (name + ".json")
    if check_only:
        if not target.is_file() or target.read_bytes() != raw:
            raise SystemExit(f"FICTIONAL_FIXTURE_DRIFT: {name}")
    else:
        target.write_bytes(raw)
    print(name, len(raw), hashlib.sha256(raw).hexdigest())
