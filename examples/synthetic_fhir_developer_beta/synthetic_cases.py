"""Pinned non-PHI synthetic Workspace demonstration for the local desktop UI.

Reads only the audited, deterministic Workspace fixture using an *installed*
medscale-workspace 0.1.0.dev1 interpreter. Rejects any payload drift, including
unknown fields, rather than allowing arbitrary patient records into the UI.
"""

from __future__ import annotations

import json
from pathlib import Path

from reproduce import call, verify_workspace_shell

EXPECTED_SNAPSHOT = {
    "workspace_id": "6cd9e9f4-1c3b-40b4-b10f-5b16db71a9fe",
    "data_class": "SYNTHETIC",
    "patient": {
        "object_id": "9dd789b2-f8c3-52e3-9834-ae86951cb3e5",
        "object_type": "Patient",
        "display_name": "Synthetic Patient Alpha",
    },
    "encounter": {
        "object_id": "7a2e996d-05a4-53cc-9d8e-cabc5bb429b3",
        "object_type": "Encounter",
        "patient_id": "9dd789b2-f8c3-52e3-9834-ae86951cb3e5",
        "label": "Synthetic Encounter 001",
    },
    "capabilities": {
        "network": False,
        "microphone": False,
        "ehr": False,
        "external_model": False,
        "persistent_write": True,
    },
    "storage": {
        "engine": "sqlite3",
        "payload_encryption": "AES-256-GCM",
        "key_derivation": "HKDF-SHA-256",
        "plaintext_fallback": False,
        "platform_key_provider": "unavailable-fail-closed",
    },
}

_SNAPSHOT_COMMAND = (
    "from medscale_workspace.app import workspace_snapshot; "
    "import json; print(json.dumps(workspace_snapshot(), sort_keys=True))"
)


def admit_snapshot(data: object) -> dict[str, str]:
    """Admit exactly the known synthetic fixture, never free-form object data."""
    if not isinstance(data, dict) or data != EXPECTED_SNAPSHOT:
        raise ValueError("Installed Workspace fixture differs from pinned synthetic-only contract")
    return {
        "workspace": "Synthetic workspace",
        "patient": "Synthetic Patient Alpha",
        "encounter": "Synthetic Encounter 001",
        "data_class": "SYNTHETIC",
        "origin": "Installed Workspace 0.1.0.dev1",
    }


def load_synthetic_case(interpreter: Path, workdir: Path) -> dict[str, str]:
    """Load the *fixed* fixture using an installed interpreter without file I/O."""
    verify_workspace_shell(interpreter, workdir)
    proc = call(interpreter, ["-I", "-c", _SNAPSHOT_COMMAND], workdir)
    if proc.returncode != 0 or len(proc.stdout) > 4096:
        raise ValueError("Synthetic Workspace fixture could not be loaded")
    try:
        return admit_snapshot(json.loads(proc.stdout))
    except (ValueError, TypeError) as exc:
        # Do not echo stderr, original data, or potentially sensitive fields.
        raise ValueError("Synthetic Workspace fixture was not admitted") from exc
