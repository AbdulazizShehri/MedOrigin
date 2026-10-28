"""Exercise the real installed Core CLI through the native Windows synthetic desktop.

Nonpublishing CI smoke test. Only bundled fictional FHIR fixtures are used.
Requires Windows, Tcl/Tk and a previously built, isolated Core wheel install.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "synthetic_fhir_developer_beta"
sys.path.insert(0, str(EXAMPLE))
import desktop  # type: ignore[import-not-found]  # noqa: E402


def run_smoke(cli: Path, *, timeout_seconds: float = 40.0) -> None:
    # Dynamic OS check keeps this CLI lintable from Linux CI while refusing
    # any non-Windows GUI run at runtime.
    if platform.system() != "Windows":
        raise RuntimeError("native desktop smoke test requires a Windows GUI runner")
    if not cli.is_file():
        raise ValueError("installed Core CLI executable is missing")
    if timeout_seconds <= 0:
        raise ValueError("timeout must be positive")

    root = desktop.tk.Tk()
    try:
        app = desktop.Desktop(root, cli)
        # Constructor sets its own default geometry: resize only AFTER setup.
        # Keep the test window off-screen while exercising real Tk events.
        root.geometry("850x610-2000-2000")
        root.update()
        for name in ("Overview", "Synthetic cases", "Synthetic validation", "Safety & scope"):
            app._switch(name)
            root.update()
            canvas = app.canvas
            if canvas.winfo_height() <= 0:
                raise AssertionError("desktop Canvas was not laid out")
            if name == "Safety & scope" and (
                app.pages[name].winfo_reqheight() <= canvas.winfo_height()
            ):
                raise AssertionError("safety page no longer exercises vertical overflow")
            canvas.yview_moveto(1)
            root.update()
            if abs(canvas.yview()[1] - 1.0) > 1e-7:
                raise AssertionError("cannot reach page bottom: " + name)

        app._switch("Synthetic validation")
        root.update()
        if app.canvas.yview()[0] != 0:
            raise AssertionError("navigation did not reset to page top")
        app.run_button.invoke()

        deadline = time.monotonic() + timeout_seconds
        while app.working and time.monotonic() < deadline:
            root.update()
            time.sleep(0.05)
        root.update()
        if app.working:
            raise TimeoutError("installed synthetic FHIR validation timed out")
        if app.status.get() != "PASSED - SYNTHETIC":
            raise AssertionError("installed synthetic Core CLI did not validate")
        if app.last_result is None or app.last_result["workspace"] is not None:
            raise AssertionError("unexpected result or Workspace payload")
        for digest in (app.report_hash.get(), app.fixture_hash.get()):
            if not desktop.HEX256.fullmatch(digest):
                raise AssertionError("invalid synthetic result digest")
        if str(app.copy_button.cget("state")) != "normal":
            raise AssertionError("copy action did not become available")

        with tempfile.TemporaryDirectory(prefix="medorigin-native-ui-ci-") as directory:
            receipt = Path(directory) / "synthetic-evidence.json"
            with patch.object(desktop.filedialog, "asksaveasfilename", return_value=str(receipt)):
                app.export_button.invoke()
                if app.status.get() != "SYNTHETIC EVIDENCE SAVED":
                    raise AssertionError("explicit local synthetic export failed")
                saved = receipt.read_bytes()
                payload = json.loads(saved.decode("utf-8"))
                if payload.get("publication_authorized") is not False:
                    raise AssertionError("export must preserve publication hold")
                if payload.get("clinical_use_authorized") is not False:
                    raise AssertionError("export must preserve clinical hold")
                if payload["fhir"]["report_sha256"] != app.report_hash.get():
                    raise AssertionError("export did not match displayed digest")
                app.export_button.invoke()
                if app.status.get() != "EXPORT NOT SAVED - EXISTING FILE PRESERVED":
                    raise AssertionError("existing evidence must not be overwritten")
                if receipt.read_bytes() != saved:
                    raise AssertionError("existing receipt bytes changed")
    finally:
        root.destroy()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, required=True, help="Installed Core console executable")
    parser.add_argument("--timeout-seconds", type=float, default=40.0)
    args = parser.parse_args(argv)
    run_smoke(args.cli, timeout_seconds=args.timeout_seconds)
    print("MEDORIGIN_WINDOWS_DESKTOP_E2E_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
