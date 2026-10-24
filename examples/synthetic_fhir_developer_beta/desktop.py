"""MedOrigin: a native, offline SYNTHETIC-ONLY developer desktop preview.

Uses an already-installed medscale Core CLI. No user file imports, PHI,
network, microphone, clinical actions, or permanent validation data storage.
"""

from __future__ import annotations

import argparse
import queue
import re
import tempfile
import threading
import tkinter as tk
from functools import partial
from pathlib import Path
from tkinter import filedialog
from typing import Any

from evidence_export import save_receipt_new
from reproduce import run_one, verify_workspace_shell
from synthetic_cases import load_synthetic_case

BACKGROUND = "#0d1118"
SURFACE = "#171e29"
SURFACE_LIGHT = "#202936"
BORDER = "#303b4d"
PRIMARY = "#f18c57"
FOREGROUND = "#f6f7fb"
MUTED = "#b3c0d0"
POSITIVE = "#91e0bb"
HEX256 = re.compile(r"[0-9a-f]{64}\Z")


def public_result(run: dict[str, Any]) -> dict[str, str]:
    """Whitelist the non-PHI information allowed in the desktop preview."""
    if run.get("structural_status") != "valid" or run.get("malformed_exit") != 1:
        raise ValueError("synthetic validator or negative control did not pass")
    report = run.get("report_sha256")
    fixture = run.get("fixture_sha256")
    if not isinstance(report, str) or not HEX256.fullmatch(report):
        raise ValueError("invalid report digest")
    if not isinstance(fixture, str) or not HEX256.fullmatch(fixture):
        raise ValueError("invalid synthetic fixture digest")
    return {"status": "VALID", "report_sha256": report, "fixture_sha256": fixture}


def validate_installed(cli: Path, workspace_python: Path | None = None) -> dict[str, Any]:
    """Execute only the bundled synthetic fixture; discard all output on return."""
    with tempfile.TemporaryDirectory(prefix="medorigin-synthetic-ui-") as name:
        output = Path(name)
        result = public_result(run_one(cli, output, "desktop"))
        safe_workspace: dict[str, object] | None = None
        if workspace_python is not None:
            observed = verify_workspace_shell(workspace_python, output)
            if observed != {
                "application": "medscale-workspace",
                "version": "0.1.0.dev1",
                "data_class": "SYNTHETIC",
                "mode": "offline-shell",
                "ready": True,
            }:
                raise ValueError("optional synthetic Workspace status was not admitted")
            safe_workspace = {"version": "0.1.0.dev1", "mode": "SYNTHETIC / offline-shell"}
        return {"fhir": result, "workspace": safe_workspace}


class Desktop:
    """Small functional native desktop experience with safe synthetic demo limits."""

    def __init__(self, root: tk.Tk, cli: Path, workspace_python: Path | None = None) -> None:
        self.root = root
        self.cli = cli
        self.workspace_python = workspace_python
        self.last_result: dict[str, Any] | None = None
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.working = False
        self.active = "Overview"
        root.title("MedOrigin - Developer Beta")
        root.geometry("1100x760")
        root.minsize(850, 610)
        root.configure(bg=BACKGROUND)
        self.status = tk.StringVar(value="READY - SYNTHETIC ONLY")
        self.result_line = tk.StringVar(value="No synthetic validation has been run.")
        self.report_hash = tk.StringVar(value="Not generated")
        self.fixture_hash = tk.StringVar(value="Not generated")
        self.case_status = tk.StringVar(
            value="Synthetic fixture ready to load"
            if workspace_python is not None
            else "Optional Workspace not connected"
        )
        self.case_patient = tk.StringVar(value="Not loaded")
        self.case_encounter = tk.StringVar(value="Not loaded")
        self.workspace_line = tk.StringVar(
            value="Optional synthetic Workspace configured"
            if workspace_python
            else "Optional Workspace not connected"
        )
        self.nav_buttons: dict[str, tk.Button] = {}
        self.pages: dict[str, tk.Frame] = {}
        self._layout()
        self._switch("Overview")
        root.after(100, self._drain)

    def _label(
        self,
        parent: tk.Misc,
        text: str,
        size: int = 12,
        color: str = FOREGROUND,
        weight: str = "normal",
        **kwargs: Any,
    ) -> tk.Label:
        return tk.Label(
            parent,
            text=text,
            bg=kwargs.pop("bg", BACKGROUND),
            fg=color,
            font=("Segoe UI", size, weight),
            anchor="w",
            justify="left",
            **kwargs,
        )

    def _button(self, parent: tk.Misc, text: str, action: Any, *, fill: bool = True) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=action,
            relief="flat",
            bd=0,
            cursor="hand2",
            bg=PRIMARY if fill else SURFACE_LIGHT,
            fg="#141316" if fill else FOREGROUND,
            activebackground="#f6a879" if fill else BORDER,
            activeforeground="#141316" if fill else FOREGROUND,
            font=("Segoe UI", 11, "bold"),
            padx=18,
            pady=12,
        )

    def _layout(self) -> None:
        header = tk.Frame(self.root, bg=BACKGROUND, height=94)
        header.pack(fill="x")
        header.pack_propagate(False)
        self._label(header, "O", size=23, color=PRIMARY).pack(side="left", padx=(32, 7))
        self._label(header, "MedOrigin", size=21, weight="bold").pack(side="left")
        self._label(
            header, "DEVELOPER BETA - UNPUBLISHED", size=9, color=PRIMARY, weight="bold"
        ).pack(side="right", padx=35)

        line = tk.Frame(self.root, bg=BORDER, height=1)
        line.pack(fill="x")
        body = tk.Frame(self.root, bg=BACKGROUND)
        body.pack(fill="both", expand=True)
        side = tk.Frame(body, bg=SURFACE, width=232)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        self._label(side, "WORKSPACE", size=10, color=MUTED, weight="bold", bg=SURFACE).pack(
            anchor="w", padx=26, pady=(35, 14)
        )
        for name in ("Overview", "Synthetic cases", "Synthetic validation", "Safety & scope"):
            b = tk.Button(
                side,
                text=name,
                command=partial(self._switch, name),
                bg=SURFACE,
                fg=MUTED,
                activebackground=SURFACE_LIGHT,
                activeforeground=FOREGROUND,
                relief="flat",
                bd=0,
                anchor="w",
                padx=24,
                pady=13,
                cursor="hand2",
                font=("Segoe UI", 11),
            )
            b.pack(fill="x", padx=10, pady=3)
            self.nav_buttons[name] = b
        bottom = tk.Frame(side, bg=SURFACE)
        bottom.pack(side="bottom", fill="x", padx=23, pady=26)
        self._label(
            bottom,
            "SYNTHETIC DATA ONLY",
            size=9,
            color=POSITIVE,
            weight="bold",
            bg=SURFACE,
        ).pack(anchor="w")
        self._label(bottom, "No EHR or patient files", size=9, color=MUTED, bg=SURFACE).pack(
            anchor="w", pady=(5, 0)
        )

        host = tk.Frame(body, bg=BACKGROUND)
        host.pack(side="left", fill="both", expand=True, padx=38, pady=35)
        for name in ("Overview", "Synthetic cases", "Synthetic validation", "Safety & scope"):
            self.pages[name] = tk.Frame(host, bg=BACKGROUND)
        self._make_overview(self.pages["Overview"])
        self._make_cases(self.pages["Synthetic cases"])
        self._make_validation(self.pages["Synthetic validation"])
        self._make_safety(self.pages["Safety & scope"])

    def _subtitle(self, parent: tk.Frame, eyebrow: str, title: str, body: str) -> None:
        self._label(parent, eyebrow.upper(), 10, PRIMARY, "bold").pack(anchor="w")
        self._label(parent, title, 29, FOREGROUND, "bold").pack(anchor="w", pady=(14, 12))
        self._label(parent, body, 11, MUTED, wraplength=680).pack(anchor="w")

    def _panel(self, parent: tk.Frame) -> tk.Frame:
        panel = tk.Frame(parent, bg=SURFACE, highlightthickness=1, highlightbackground=BORDER)
        panel.pack(fill="x", pady=(20, 0))
        return panel

    def _make_overview(self, page: tk.Frame) -> None:
        self._subtitle(
            page,
            "Local developer toolkit",
            "Validate synthetic FHIR, offline.",
            "A native interactive preview of installed Python tools. "
            "Uses bundled fictional data only; no patient file selection or cloud service.",
        )
        p = self._panel(page)
        self._label(p, "CORE ENGINE", 10, PRIMARY, "bold", bg=SURFACE).pack(
            anchor="w", padx=25, pady=(23, 6)
        )
        self._label(p, "medscale 0.3.0 - Installed CLI", 16, FOREGROUND, "bold", bg=SURFACE).pack(
            anchor="w", padx=25
        )
        self._label(
            p,
            "Validate the bundled synthetic StructureDefinition and inspect SHA-256 evidence.",
            11,
            MUTED,
            bg=SURFACE,
            wraplength=620,
        ).pack(anchor="w", padx=25, pady=(8, 21))
        p2 = self._panel(page)
        self._label(p2, "SYNTHETIC WORKSPACE", 10, PRIMARY, "bold", bg=SURFACE).pack(
            anchor="w", padx=25, pady=(23, 6)
        )
        tk.Label(
            p2,
            textvariable=self.workspace_line,
            bg=SURFACE,
            fg=FOREGROUND,
            font=("Segoe UI", 13),
            anchor="w",
        ).pack(anchor="w", padx=25, pady=(0, 23))
        self._button(page, "Run synthetic FHIR validation >", self._begin_from_overview).pack(
            anchor="w", pady=(27, 0)
        )

    def _make_cases(self, page: tk.Frame) -> None:
        self._subtitle(
            page,
            "Workspace fixture explorer",
            "Explore a fictional case.",
            "Load the pinned Synthetic Patient Alpha and Synthetic Encounter 001 "
            "from a separately installed, synthetic-only Workspace. "
            "Real patient files are not accepted.",
        )
        panel = self._panel(page)
        self._label(panel, "FIXED SYNTHETIC CASE", 10, PRIMARY, "bold", bg=SURFACE).pack(
            anchor="w", padx=25, pady=(23, 7)
        )
        for title, variable in (
            ("Demo patient", self.case_patient),
            ("Demo encounter", self.case_encounter),
            ("Data classification", self.case_status),
        ):
            self._label(panel, title, 10, MUTED, bg=SURFACE).pack(anchor="w", padx=25, pady=(15, 5))
            tk.Label(
                panel,
                textvariable=variable,
                bg=SURFACE,
                fg=FOREGROUND,
                font=("Segoe UI", 13, "bold"),
                anchor="w",
                wraplength=600,
                justify="left",
            ).pack(fill="x", padx=25)
        controls = tk.Frame(panel, bg=SURFACE)
        controls.pack(anchor="w", padx=25, pady=24)
        self.case_button = self._button(controls, "Load synthetic case", self._load_case)
        if self.workspace_python is None:
            self.case_button.configure(state="disabled")
        self.case_button.pack(side="left")
        self._button(controls, "Run FHIR validation", self._begin_from_overview, fill=False).pack(
            side="left", padx=(12, 0)
        )
        self._label(
            page,
            "Demo-only identity is pinned to Workspace 0.1.0.dev1; "
            "unexpected object fields are rejected rather than shown.",
            10,
            MUTED,
            wraplength=660,
        ).pack(anchor="w", pady=(22, 0))

    def _make_validation(self, page: tk.Frame) -> None:
        self._subtitle(
            page,
            "Interactive validation",
            "Run the installed FHIR checker.",
            "Runs only the bundled synthetic JSON fixture. Local temporary report "
            "files are deleted automatically after validation.",
        )
        line = tk.Frame(page, bg=BACKGROUND)
        line.pack(fill="x", pady=(28, 0))
        self.run_button = self._button(line, "Validate synthetic fixture", self._begin)
        self.run_button.pack(side="left")
        tk.Label(
            line,
            textvariable=self.status,
            font=("Segoe UI", 10, "bold"),
            bg=BACKGROUND,
            fg=POSITIVE,
        ).pack(side="left", padx=22)
        panel = self._panel(page)
        self._label(panel, "RESULT", 10, PRIMARY, "bold", bg=SURFACE).pack(
            anchor="w", padx=26, pady=(24, 8)
        )
        tk.Label(
            panel,
            textvariable=self.result_line,
            font=("Segoe UI", 15, "bold"),
            bg=SURFACE,
            fg=FOREGROUND,
            justify="left",
            anchor="w",
            wraplength=640,
        ).pack(fill="x", padx=26)
        for label, variable in [
            ("Report SHA-256", self.report_hash),
            ("Synthetic fixture SHA-256", self.fixture_hash),
            ("Workspace status", self.workspace_line),
        ]:
            self._label(panel, label, 10, MUTED, bg=SURFACE).pack(anchor="w", padx=26, pady=(22, 3))
            tk.Label(
                panel,
                textvariable=variable,
                bg=SURFACE,
                fg=FOREGROUND,
                font=("Consolas", 10),
                anchor="w",
                justify="left",
                wraplength=630,
            ).pack(fill="x", padx=26)
        buttons = tk.Frame(panel, bg=SURFACE)
        buttons.pack(anchor="w", padx=25, pady=24)
        self.copy_button = self._button(buttons, "Copy report SHA-256", self._copy, fill=False)
        self.copy_button.configure(state="disabled")
        self.copy_button.pack(side="left")
        self.export_button = self._button(
            buttons, "Save synthetic evidence...", self._save_receipt, fill=False
        )
        self.export_button.configure(state="disabled")
        self.export_button.pack(side="left", padx=(12, 0))

    def _make_safety(self, page: tk.Frame) -> None:
        self._subtitle(
            page,
            "Deliberate boundaries",
            "Synthetic Developer Beta.",
            "This is a developer demonstration, not a clinical application or a "
            "general-purpose FHIR certification product.",
        )
        notes = [
            ("LOCAL ONLY", "No server, telemetry, model inference, microphone or EHR connection."),
            ("FIXED TEST DATA", "Only the included fictional StructureDefinition fixture is used."),
            ("NO PATIENT IMPORT", "No file picker or ability to select real patient records."),
            ("HISTORICAL DATA", "v0.2.0 stored datasets are incompatible; no automatic migration."),
            (
                "NO CLINICAL CLAIMS",
                "A valid structural report does not certify HL7 conformance or clinical safety.",
            ),
            (
                "UNPUBLISHED",
                "Independent security review and package/version decisions remain open.",
            ),
            (
                "EXPLICIT LOCAL EXPORT",
                "Only synthetic status and SHA-256 digests can be saved. "
                "Existing files are never overwritten.",
            ),
        ]
        for key, value in notes:
            p = self._panel(page)
            self._label(p, key, 10, PRIMARY, "bold", bg=SURFACE).pack(
                anchor="w", padx=20, pady=(14, 4)
            )
            self._label(p, value, 10, MUTED, bg=SURFACE, wraplength=620).pack(
                anchor="w", padx=20, pady=(0, 14)
            )

    def _switch(self, name: str) -> None:
        for page in self.pages.values():
            page.pack_forget()
        self.active = name
        self.pages[name].pack(fill="both", expand=True)
        for label, widget in self.nav_buttons.items():
            widget.configure(
                bg=SURFACE_LIGHT if label == name else SURFACE,
                fg=FOREGROUND if label == name else MUTED,
            )

    def _begin_from_overview(self) -> None:
        self._switch("Synthetic validation")
        self._begin()

    def _begin(self) -> None:
        if self.working:
            return
        self.working = True
        self.run_button.configure(state="disabled")
        self.case_button.configure(state="disabled")
        self.copy_button.configure(state="disabled")
        self.export_button.configure(state="disabled")
        self.status.set("RUNNING - LOCAL CHECK")
        self.result_line.set("Checking bundled synthetic fixture...")
        self.report_hash.set("Not generated")
        self.fixture_hash.set("Not generated")
        thread = threading.Thread(target=self._worker, daemon=True)
        thread.start()

    def _load_case(self) -> None:
        if self.working or self.workspace_python is None:
            return
        self.working = True
        self.run_button.configure(state="disabled")
        self.case_button.configure(state="disabled")
        self.case_status.set("Checking installed synthetic fixture...")
        threading.Thread(target=self._case_worker, daemon=True).start()

    def _case_worker(self) -> None:
        try:
            if self.workspace_python is None:
                raise ValueError("Synthetic Workspace not installed")
            with tempfile.TemporaryDirectory(prefix="medorigin-case-read-") as directory:
                admitted = load_synthetic_case(self.workspace_python, Path(directory))
            self.events.put(("case-success", admitted))
        except Exception:
            self.events.put(("case-error", "Synthetic case could not be verified."))

    def _worker(self) -> None:
        try:
            outcome = validate_installed(self.cli, self.workspace_python)
            self.events.put(("success", outcome))
        except Exception:
            # Refuse to render unsanitized subprocess or file content.
            self.events.put(("error", "Validation could not be verified; no report admitted."))

    def _drain(self) -> None:
        try:
            while True:
                kind, result = self.events.get_nowait()
                self.working = False
                self.run_button.configure(state="normal")
                if self.workspace_python is not None:
                    self.case_button.configure(state="normal")
                if kind == "case-success":
                    self.case_patient.set(result["patient"])
                    self.case_encounter.set(result["encounter"])
                    self.case_status.set("SYNTHETIC / verified fixture")
                    continue
                if kind == "case-error":
                    self.case_patient.set("Not loaded")
                    self.case_encounter.set("Not loaded")
                    self.case_status.set("Synthetic case could not be verified.")
                    continue
                if kind == "success":
                    self.last_result = result
                    safe = result["fhir"]
                    self.status.set("PASSED - SYNTHETIC")
                    self.result_line.set("Local FHIR structural validation passed")
                    self.report_hash.set(safe["report_sha256"])
                    self.fixture_hash.set(safe["fixture_sha256"])
                    if result["workspace"] is not None:
                        self.workspace_line.set("Workspace 0.1.0.dev1 - SYNTHETIC / offline-shell")
                    self.copy_button.configure(state="normal")
                    self.export_button.configure(state="normal")
                else:
                    self.last_result = None
                    self.copy_button.configure(state="disabled")
                    self.export_button.configure(state="disabled")
                    self.status.set("NOT QUALIFIED")
                    self.result_line.set(str(result))
        except queue.Empty:
            pass
        self.root.after(100, self._drain)

    def _save_receipt(self) -> None:
        if self.working or self.last_result is None:
            return
        filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save synthetic-only developer evidence",
            defaultextension=".json",
            initialfile="medorigin-synthetic-evidence.json",
            filetypes=[("JSON evidence (synthetic only)", "*.json")],
        )
        if not filename:
            return
        try:
            save_receipt_new(
                Path(filename),
                self.last_result,
                case_verified=self.case_status.get() == "SYNTHETIC / verified fixture",
            )
        except (OSError, ValueError):
            self.status.set("EXPORT NOT SAVED - EXISTING FILE PRESERVED")
            return
        self.status.set("SYNTHETIC EVIDENCE SAVED")

    def _copy(self) -> None:
        if not self.last_result:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.last_result["fhir"]["report_sha256"])
        self.status.set("REPORT SHA-256 COPIED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True, type=Path, help="Installed medscale.exe / medscale")
    parser.add_argument(
        "--workspace-python", type=Path, help="Optional installed synthetic Workspace Python"
    )
    args = parser.parse_args(argv)
    core = args.cli.resolve()
    workspace = args.workspace_python.resolve() if args.workspace_python else None
    if not core.is_file():
        parser.error("installed medscale CLI not found")
    if workspace is not None and not workspace.is_file():
        parser.error("optional installed Workspace interpreter not found")
    root = tk.Tk()
    Desktop(root, core, workspace)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
