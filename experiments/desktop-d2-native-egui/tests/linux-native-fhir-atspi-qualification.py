#!/usr/bin/env python3
"""Real Linux AT-SPI acceptance for the fixed, nonclinical native D2 fixture UI.

Run only inside a disposable Xvfb + dbus-run-session. No real FHIR files,
network measurement, UI input injection into a user's desktop or publication.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time

CASES = [
    ("patient-minimal", 57, "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0", "FHIR_ENVELOPE_OK"),
    ("patient-invalid-utf8", 1, "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89", "INVALID_UTF8"),
    ("patient-over-limit", 32769, "b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538", "RESOURCE_TOO_LARGE"),
    ("patient-exact-limit", 32768, "ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e", "FHIR_ENVELOPE_OK"),
    ("observation-minimal", 251, "527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19", "FHIR_ENVELOPE_OK"),
    ("observation-bad-subject", 253, "d2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838", "INVALID_REFERENCE"),
    ("bundle-valid", 531, "3a530a66c0f2b71908b1282985432e405f0f2f412c7ccc0143aa1972d9447983", "BUNDLE_GRAPH_OK"),
    ("bundle-bad-reference", 528, "4aabcfa54309c83052d62b4fdcf1c6635a6cd3d937551e2ab947899345f9f082", "INVALID_REFERENCE"),
    ("bundle-duplicate", 531, "813f8a3b8fee59ba74abdb293c6cac5cca103b390153730e6e3bc4656540f15b", "DUPLICATE_ENTRY"),
    ("bundle-wrong-type", 532, "293c10c8abf055e8c1f84bae4913c7246bf9be5bf53dee0fb3c918e32a8346a7", "INVALID_BUNDLE_TYPE"),
    ("bundle-linked", 559, "1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88", "BUNDLE_GRAPH_OK"),
    ("bundle-dangling", 559, "1bbc0bac94b3ff19dce3502164f3243748cf5aa7e869433bdb09e7ec2266b229", "INVALID_REFERENCE"),
]


def refuse(message: str) -> None:
    raise RuntimeError("LINUX_D2_ATSPI_NO_GO: " + message)


def tree(root: object, depth: int = 0, budget: list[int] | None = None) -> list[object]:
    if budget is None:
        budget = [0]
    if depth > 22 or budget[0] >= 750:
        return []
    budget[0] += 1
    result = [root]
    try:
        count = root.childCount
    except (AttributeError, RuntimeError):
        return result
    for index in range(min(count, 125)):
        try:
            child = root.getChildAtIndex(index)
            if child is not None:
                result.extend(tree(child, depth + 1, budget))
        except (AttributeError, RuntimeError):
            continue
    return result


def name(node: object) -> str:
    try:
        return str(node.name)
    except (AttributeError, RuntimeError):
        return ""


def role(node: object) -> str:
    try:
        return str(node.getRoleName()).lower()
    except (AttributeError, RuntimeError):
        return ""


def find(window: object, text: str, hints: tuple[str, ...] = ()) -> list[object]:
    nodes = tree(window)
    return [node for node in nodes if text in name(node) and
            (not hints or any(h in role(node) for h in hints))]


def unique(window: object, text: str, hints: tuple[str, ...]) -> object:
    matches = find(window, text, hints)
    if len(matches) != 1:
        refuse(f"expected one AT-SPI control {text!r}, roles={hints}, found={len(matches)}; "
               f"visible={[name(n)[:90] for n in tree(window)[:60]]}")
    return matches[0]


def press(node: object, label: str) -> None:
    try:
        action = node.queryAction()
        options = [action.getName(i).lower() for i in range(action.nActions)]
        selected = next((i for i, value in enumerate(options)
                         if "click" in value or "press" in value or "toggle" in value), None)
        if selected is None or not action.doAction(selected):
            refuse(f"AT-SPI action missing/refused for {label}: {options}")
    except (AttributeError, RuntimeError) as exc:
        refuse(f"AT-SPI action failed for {label}: {type(exc).__name__}")


def wait_for(fn, label: str, seconds: float = 12) -> object:
    until = time.monotonic() + seconds
    last = None
    while time.monotonic() < until:
        try:
            value = fn()
            if value:
                return value
        except (AttributeError, RuntimeError, IndexError) as exc:
            last = type(exc).__name__
        time.sleep(0.2)
    refuse(f"timed out: {label}; last={last}")


def main() -> int:
    if len(sys.argv) != 3:
        refuse("usage: linux-native-fhir-atspi-qualification.py ABSOLUTE_BINARY EXACT_SHA256")
    path = Path(sys.argv[1])
    sha = sys.argv[2].lower()
    if not path.is_absolute() or path.name != "medorigin-desktop-d2-native-egui" or not path.is_file():
        refuse("expected explicit native Rust D2 executable path")
    if len(sha) != 64 or any(x not in "0123456789abcdef" for x in sha):
        refuse("malformed expected binary SHA256")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != sha:
        refuse("binary identity mismatch before application launch")
    if not os.environ.get("DISPLAY") or not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        refuse("requires disposable Xvfb and private D-Bus session")
    import pyatspi  # type: ignore[import-not-found]

    # Start the private AT-SPI Registry BEFORE the native eframe program:
    # AccessKit may decide whether to register its adapter at startup.
    desktop = pyatspi.Registry.getDesktop(0)
    proc = subprocess.Popen([str(path)], stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, close_fds=True)
    try:

        def find_window():
            if proc.poll() is not None:
                err = proc.stderr.read(2500).decode("utf-8", errors="replace") if proc.stderr else ""
                refuse(f"native GUI exited unexpectedly rc={proc.returncode} stderr={err[-900:]!r}")
            found = [n for n in tree(desktop)
                     if "MedOrigin Native Rust" in name(n)
                     and ("frame" in role(n) or "window" in role(n))]
            return found[0] if len(found) == 1 else None

        try:
            window = wait_for(find_window, "native D2 AT-SPI frame", 20)
        except RuntimeError as exc:
            visible = [(name(n)[:90], role(n)) for n in tree(desktop)[:50]]
            refuse(f"{exc}; AT-SPI desktop visible nodes={visible}")
        def existing_controls():
            return find(window, "patient-minimal (57 bytes)", ("check", "radio", "toggle")) and find(
                window, "Verify synthetic SHA-256", ("push", "button"))
        wait_for(existing_controls, "original native D2 AT-SPI controls")
        for index, (case_id, size, digest, status) in enumerate(CASES):
            if index == 4:
                expand = unique(window, "Additional fictional FHIR/Bundle cases (8)",
                                ("push", "button", "toggle", "check"))
                press(expand, "Advanced fictional cases")
            label = f"{case_id} ({size} bytes)"
            control = wait_for(
                lambda label=label: find(window, label, ("check", "radio", "toggle")),
                f"selector {label}")
            if len(control) != 1:
                refuse(f"ambiguous AT-SPI selector {label}")
            press(control[0], label)
            verify = unique(window, "Verify synthetic SHA-256", ("push", "button"))
            press(verify, "Verify synthetic SHA-256")
            sha_text = f"Synthetic raw SHA-256 verified: {digest}"
            expected = f"Fictional FHIR envelope: {status} (NOT full FHIR R4 validation)"
            def distinct_texts():
                texts = [n for n in tree(window) if "text" in role(n) or "label" in role(n)]
                sha_matches = [n for n in texts if name(n) == sha_text]
                status_matches = [n for n in texts if name(n) == expected]
                return len(sha_matches) == 1 and len(status_matches) == 1 and sha_matches[0] is not status_matches[0]
            wait_for(distinct_texts, f"separate accessible SHA and envelope nodes for {case_id}")
            print(f"LINUX_D2_ATSPI_FICTIONAL_CASE_PASS={case_id} status={status}", flush=True)
        print("LINUX_D2_ATSPI_12_OF_12_PASS_NONPUBLISHING", flush=True)
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=4)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
