#!/usr/bin/env python3
"""Real Linux AT-SPI acceptance for the fixed, nonclinical native D2 fixture UI.

Run only inside a disposable Xvfb + dbus-run-session. No real FHIR files,
network measurement, UI input injection into a user's desktop or publication.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

CASES = [
    (
        "patient-minimal",
        57,
        "747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0",
        "FHIR_ENVELOPE_OK",
    ),
    (
        "patient-invalid-utf8",
        1,
        "a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89",
        "INVALID_UTF8",
    ),
    (
        "patient-over-limit",
        32769,
        "b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538",
        "RESOURCE_TOO_LARGE",
    ),
    (
        "patient-exact-limit",
        32768,
        "ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e",
        "FHIR_ENVELOPE_OK",
    ),
    (
        "observation-minimal",
        251,
        "527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19",
        "FHIR_ENVELOPE_OK",
    ),
    (
        "observation-bad-subject",
        253,
        "d2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838",
        "INVALID_REFERENCE",
    ),
    (
        "bundle-valid",
        531,
        "3a530a66c0f2b71908b1282985432e405f0f2f412c7ccc0143aa1972d9447983",
        "BUNDLE_GRAPH_OK",
    ),
    (
        "bundle-bad-reference",
        528,
        "4aabcfa54309c83052d62b4fdcf1c6635a6cd3d937551e2ab947899345f9f082",
        "INVALID_REFERENCE",
    ),
    (
        "bundle-duplicate",
        531,
        "813f8a3b8fee59ba74abdb293c6cac5cca103b390153730e6e3bc4656540f15b",
        "DUPLICATE_ENTRY",
    ),
    (
        "bundle-wrong-type",
        532,
        "293c10c8abf055e8c1f84bae4913c7246bf9be5bf53dee0fb3c918e32a8346a7",
        "INVALID_BUNDLE_TYPE",
    ),
    (
        "bundle-linked",
        559,
        "1d24976b74ab0481ce2acc1010d58ec5e4b9da9ba93071e1042afeb299a03d88",
        "BUNDLE_GRAPH_OK",
    ),
    (
        "bundle-dangling",
        559,
        "1bbc0bac94b3ff19dce3502164f3243748cf5aa7e869433bdb09e7ec2266b229",
        "INVALID_REFERENCE",
    ),
]


class FatalQualificationError(RuntimeError):
    """An actual negative acceptance receipt; never retry and obscure it."""


def refuse(message: str) -> None:
    raise FatalQualificationError("LINUX_D2_ATSPI_NO_GO: " + message)


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


def find_native_frame(desktop: object) -> object | None:
    """Select the real AT-SPI application and its uniquely identified frame.

    AccessKit's Linux AT-SPI window frame may have an EMPTY accessible name;
    the window heading is a child label, while the executable application
    object owns the stable process identity. Never require a title on frame.
    """
    apps = [
        node
        for node in tree(desktop)
        if role(node) == "application" and name(node) == "medorigin-desktop-d2-native-egui"
    ]
    if len(apps) != 1:
        return None
    frames = [node for node in tree(apps[0]) if role(node) == "frame"]
    identified: list[object] = []
    for frame in frames:
        descendants = tree(frame)
        names = {name(node) for node in descendants}
        if (
            "MedOrigin — Native Rust Experiment" in names
            and "patient-minimal (57 bytes)" in names
            and "Verify synthetic SHA-256" in names
        ):
            identified.append(frame)
    return identified[0] if len(identified) == 1 else None


def find(window: object, text: str, hints: tuple[str, ...] = ()) -> list[object]:
    nodes = tree(window)
    return [
        node
        for node in nodes
        if text in name(node) and (not hints or any(h in role(node) for h in hints))
    ]


def unique(window: object, text: str, hints: tuple[str, ...]) -> object:
    matches = find(window, text, hints)
    if len(matches) != 1:
        refuse(
            f"expected one AT-SPI control {text!r}, roles={hints}, found={len(matches)}; "
            f"visible={[name(n)[:90] for n in tree(window)[:60]]}"
        )
    return matches[0]


def press(node: object, label: str) -> None:
    try:
        action = node.queryAction()
        options = [action.getName(i).lower() for i in range(action.nActions)]
        selected = next(
            (
                i
                for i, value in enumerate(options)
                if "click" in value or "press" in value or "toggle" in value
            ),
            None,
        )
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
        except FatalQualificationError:
            raise
        except (AttributeError, RuntimeError, IndexError) as exc:
            last = type(exc).__name__
        time.sleep(0.2)
    refuse(f"timed out: {label}; last={last}")


def verification_receipts_cleared(window: object) -> bool:
    """No stale result may survive a fixture selection before Verify."""
    labels = [name(n) for n in tree(window) if role(n) == "label"]
    return not any(
        item.startswith("Synthetic raw SHA-256 verified:")
        or item.startswith("Fictional FHIR envelope:")
        for item in labels
    )


def verify_linux_keyboard_only(window: object, pyatspi: object) -> None:
    """Exercise real XTest Tab/Shift+Tab/Space, NEVER AT-SPI Action.

    The AT-SPI tree is read-only evidence of keyboard focus/results. Only the
    disposable Xvfb desktop receives simulated keyboard events.
    """

    def focused_names() -> list[str]:
        result = []
        for node in tree(window):
            try:
                if node.getState().contains(pyatspi.STATE_FOCUSED):
                    result.append(name(node))
            except (AttributeError, RuntimeError):
                continue
        return result

    def send_key(key: str) -> None:
        permitted = {"Tab", "shift+Tab", "space"}
        if key not in permitted:
            refuse("unexpected virtual keyboard shortcut")
        sent = subprocess.run(
            ["xdotool", "key", "--clearmodifiers", "--delay", "80", key],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if sent.returncode != 0:
            refuse(f"X11 real keyboard injection refused {key}: {sent.stderr[-250:]!r}")
        time.sleep(0.12)

    def focus_target(label: str, direction: str = "Tab") -> None:
        for _ in range(18):
            names = focused_names()
            if names == [label]:
                return
            if len(names) > 1:
                refuse(f"ambiguous AT-SPI keyboard focus {names}")
            send_key(direction)
        refuse(f"keyboard-only tab traversal never focused {label!r}; last_focus={focused_names()}")

    # Do not use AT-SPI programmatic presses anywhere on this path: only
    # inspect accessible focus state and expected post-action labels.
    for case_id, count, digest, status in CASES[:4]:
        label = f"{case_id} ({count} bytes)"
        focus_target(label)
        send_key("space")
        focus_target("Verify synthetic SHA-256")
        send_key("space")
        expected_sha = f"Synthetic raw SHA-256 verified: {digest}"
        expected_envelope = f"Fictional FHIR envelope: {status} (NOT full FHIR R4 validation)"

        def verified_separate_nodes(
            expected_sha: str = expected_sha, expected_envelope: str = expected_envelope
        ) -> bool:
            current = [name(n) for n in tree(window) if role(n) == "label"]
            return current.count(expected_sha) == 1 and current.count(expected_envelope) == 1

        wait_for(
            verified_separate_nodes,
            f"keyboard-only exact accessible SHA and FHIR envelope for {case_id}",
        )
        print(f"LINUX_D2_KEYBOARD_FICTIONAL_CASE_PASS={case_id}", flush=True)

    # Explicit reverse traversal check independent of the passed fixture
    # receipts: from Verify, Shift+Tab must reach the last primary selector.
    focus_target("patient-exact-limit (32768 bytes)", "shift+Tab")
    print("LINUX_D2_KEYBOARD_REVERSE_SHIFT_TAB_PASS_NONPUBLISHING", flush=True)
    print("LINUX_D2_KEYBOARD_4_OF_4_PASS_NONPUBLISHING", flush=True)


def main() -> int:
    if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != "--keyboard"):
        refuse(
            "usage: linux-native-fhir-atspi-qualification.py ABSOLUTE_BINARY "
            "EXACT_SHA256 [--keyboard]"
        )
    keyboard_mode = len(sys.argv) == 4
    path = Path(sys.argv[1])
    sha = sys.argv[2].lower()
    if (
        not path.is_absolute()
        or path.name != "medorigin-desktop-d2-native-egui"
        or not path.is_file()
    ):
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
    # AccessKit/AT-SPI does not publish UI controls while the *private CI*
    # org.a11y.Status.IsEnabled property is false. Set this only on the
    # dbus-run-session bus in a disposable hosted runner, NEVER on the
    # user's system bus or persistent desktop settings.
    command = [
        "dbus-send",
        "--session",
        "--print-reply",
        "--dest=org.a11y.Bus",
        "/org/a11y/bus",
        "org.freedesktop.DBus.Properties.Set",
        "string:org.a11y.Status",
        "string:IsEnabled",
        "variant:boolean:true",
    ]
    enabled = subprocess.run(command, capture_output=True, text=True, timeout=8, check=False)
    if enabled.returncode != 0:
        refuse("private AT-SPI bus declined enabling IsEnabled; no app launched")
    readback = subprocess.run(
        [
            "dbus-send",
            "--session",
            "--print-reply",
            "--dest=org.a11y.Bus",
            "/org/a11y/bus",
            "org.freedesktop.DBus.Properties.Get",
            "string:org.a11y.Status",
            "string:IsEnabled",
        ],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    if readback.returncode != 0 or "boolean true" not in readback.stdout:
        refuse(f"private AT-SPI bus IsEnabled did not attest TRUE: {readback.stdout[:300]!r}")
    # Mark the isolated test session as having an assistive client so
    # AccessKit does not suppress lazy accessibility initialization.
    screen_reader = subprocess.run(
        [
            "dbus-send",
            "--session",
            "--print-reply",
            "--dest=org.a11y.Bus",
            "/org/a11y/bus",
            "org.freedesktop.DBus.Properties.Set",
            "string:org.a11y.Status",
            "string:ScreenReaderEnabled",
            "variant:boolean:true",
        ],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    if screen_reader.returncode != 0:
        refuse("private AT-SPI bus declined ScreenReaderEnabled")
    print("PRIVATE_ATSPI_BUS_ENABLED_IN_DISPOSABLE_RUNNER_ONLY", flush=True)
    # Some AccessKit/X11 adapters publish the tree only after WM mapping.
    # This manager lives solely inside the Xvfb environment of this CI job.
    wm = subprocess.Popen(
        ["fluxbox", "-display", os.environ["DISPLAY"]],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        close_fds=True,
    )
    time.sleep(0.6)
    if wm.poll() is not None:
        details = wm.stderr.read(1000).decode("utf-8", errors="replace") if wm.stderr else ""
        refuse(f"disposable X11 window manager exited rc={wm.returncode}: {details[-500:]!r}")
    proc = subprocess.Popen(
        [str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, close_fds=True
    )
    try:
        # Real X11 window mapping is distinct from AT-SPI registration.
        # Trigger a focus event solely on this disposable virtual display.
        def x11_window():
            if proc.poll() is not None:
                err = (
                    proc.stderr.read(2000).decode("utf-8", errors="replace") if proc.stderr else ""
                )
                refuse(f"native app exited rc={proc.returncode} stderr={err[-900:]!r}")
            found = subprocess.run(
                ["xdotool", "search", "--onlyvisible", "--name", "MedOrigin Native Rust"],
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            ids = [i.strip() for i in found.stdout.splitlines() if i.strip().isdigit()]
            return ids[0] if found.returncode == 0 and len(ids) == 1 else None

        try:
            x11_id = wait_for(x11_window, "native window mapped on disposable X11", 15)
        except FatalQualificationError:
            raise
        except RuntimeError as exc:
            x11 = subprocess.run(
                ["xwininfo", "-root", "-tree"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            refuse(f"{exc}; native_proc_poll={proc.poll()}, X11 tree={x11.stdout[-2400:]!r}")
        # In headless Xvfb a minimal window manager may not publish the
        # EWMH _NET_ACTIVE_WINDOW path required by windowactivate. First use
        # the X11 core SetInputFocus fallback; do NOT call an attempted
        # activation successful unless xdotool confirms the focus operation.
        focus = subprocess.run(
            ["xdotool", "windowfocus", "--sync", str(x11_id)],
            capture_output=True,
            text=True,
            timeout=6,
            check=False,
        )
        if focus.returncode != 0:
            refuse(
                f"X11 native window focus refused on disposable display: "
                f"stdout={focus.stdout[-250:]!r} stderr={focus.stderr[-300:]!r}"
            )
        print(f"DISPOSABLE_X11_WINDOW_FOCUSED={x11_id}", flush=True)

        def find_window():
            if proc.poll() is not None:
                err = (
                    proc.stderr.read(2500).decode("utf-8", errors="replace") if proc.stderr else ""
                )
                refuse(f"native GUI exited unexpectedly rc={proc.returncode} stderr={err[-900:]!r}")
            return find_native_frame(desktop)

        try:
            window = wait_for(find_window, "native D2 AT-SPI frame", 20)
        except FatalQualificationError as exc:
            # Inspect only this disposable session, not the user's DBus.
            visible = [(name(n)[:90], role(n)) for n in tree(desktop)[:50]]
            services = subprocess.run(
                [
                    "dbus-send",
                    "--session",
                    "--print-reply",
                    "--dest=org.freedesktop.DBus",
                    "/org/freedesktop/DBus",
                    "org.freedesktop.DBus.ListNames",
                ],
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
            atspi_status = subprocess.run(
                [
                    "dbus-send",
                    "--session",
                    "--print-reply",
                    "--dest=org.a11y.Bus",
                    "/org/a11y/bus",
                    "org.freedesktop.DBus.Properties.Get",
                    "string:org.a11y.Status",
                    "string:ScreenReaderEnabled",
                ],
                capture_output=True,
                text=True,
                timeout=6,
                check=False,
            )
            refuse(
                f"{exc}; desktop_nodes={visible}; "
                f"screen_reader={atspi_status.stdout[-200:]!r}; "
                f"session_dbus_names={services.stdout[-1300:]!r}"
            )

        def existing_controls():
            return find(
                window, "patient-minimal (57 bytes)", ("check", "radio", "toggle")
            ) and find(window, "Verify synthetic SHA-256", ("push", "button"))

        wait_for(existing_controls, "original native D2 AT-SPI controls")
        if keyboard_mode:
            verify_linux_keyboard_only(window, pyatspi)
            return 0
        for index, (case_id, size, digest, status) in enumerate(CASES):
            if index == 4:
                expand = unique(
                    window,
                    "Additional fictional FHIR/Bundle cases (8)",
                    ("push", "button", "toggle", "check"),
                )
                press(expand, "Advanced fictional cases")
            label = f"{case_id} ({size} bytes)"
            control = wait_for(
                lambda label=label: find(window, label, ("check", "radio", "toggle")),
                f"selector {label}",
            )
            if len(control) != 1:
                refuse(f"ambiguous AT-SPI selector {label}")
            press(control[0], label)
            # This UI redraws asynchronously. The previous fixture's result
            # must have disappeared *before* the next Verify action; without
            # this guard back-to-back AT-SPI clicks can race eframe rendering.
            wait_for(
                lambda: verification_receipts_cleared(window),
                f"clear prior receipt before {case_id}",
            )
            verify = unique(window, "Verify synthetic SHA-256", ("push", "button"))
            press(verify, "Verify synthetic SHA-256")
            sha_text = f"Synthetic raw SHA-256 verified: {digest}"
            expected = f"Fictional FHIR envelope: {status} (NOT full FHIR R4 validation)"

            def distinct_texts(sha_text: str = sha_text, expected: str = expected) -> bool:
                texts = [n for n in tree(window) if "text" in role(n) or "label" in role(n)]
                sha_matches = [n for n in texts if name(n) == sha_text]
                status_matches = [n for n in texts if name(n) == expected]
                return (
                    len(sha_matches) == 1
                    and len(status_matches) == 1
                    and sha_matches[0] is not status_matches[0]
                )

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
        wm.terminate()
        try:
            wm.wait(timeout=4)
        except subprocess.TimeoutExpired:
            wm.kill()
            wm.wait(timeout=4)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
