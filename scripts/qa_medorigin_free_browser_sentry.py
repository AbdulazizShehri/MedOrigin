"""Free, nonpublishing MedOrigin QA with Playwright and local-only Sentry.

Only bundled fictional FHIR records may be used. Network access is needed only
to provision QA packages in CI; the browser and Sentry run against local data
without telemetry or application-data uploads. No release side effects.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from importlib import import_module
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "synthetic_fhir_developer_beta"
sys.path.insert(0, str(DEMO))

import preview  # type: ignore[import-not-found]  # noqa: E402

VIEWPORTS = ((375, 667), (850, 610), (1440, 900))
HEX_256 = re.compile(r"[0-9a-f]{64}\Z")


def _run_local(args: list[str], *, timeout: int = 100) -> None:
    completed = subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        # Do not echo the process' arbitrary output or potentially sensitive paths.
        raise RuntimeError("local synthetic QA command failed")


def _assert_page(page: Any) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    external: list[str] = []
    page.on("pageerror", lambda error: failures.append(type(error).__name__))
    page.on(
        "request",
        lambda request: (
            external.append("outbound-request")
            if request.url.startswith(("https://", "http://"))
            else None
        ),
    )
    return failures, external


def _browser_checks(html: Path, edge: Path) -> None:
    # Import only during this optional QA job; the Core package and hosted
    # static environments intentionally do not depend on Playwright.
    sync_playwright = import_module("playwright.sync_api").sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=str(edge),
            args=["--no-first-run"],
        )
        try:
            for width, height in VIEWPORTS:
                page = browser.new_page(viewport={"width": width, "height": height})
                failures, external = _assert_page(page)
                page.goto(html.as_uri(), wait_until="load")
                page.locator("article.result").first.wait_for()
                if page.locator("article.result").count() != 2:
                    raise AssertionError("two verified cross-interpreter results required")
                if page.get_by_text("PASSED", exact=True).count() != 2:
                    raise AssertionError("two visible synthetic passes required")
                if page.evaluate("document.documentElement.scrollWidth > innerWidth"):
                    raise AssertionError("horizontal overflow on compact viewport")
                if page.locator("script, iframe, img").count():
                    raise AssertionError("unexpected executable or media content")
                if external or failures:
                    raise AssertionError("browser emitted an error or outbound request")
                page.close()

            # Only the pure renderer is used here. A malicious receipt MUST NOT be
            # admitted by preview.admit_receipt() or any publication workflow.
            adversarial_label = (
                "test "
                + "MEDORIGIN_UNBROKEN_SYNTHETIC_LABEL_" * 20
                + '<img src=x onerror="window.__medorigin_xss=1">'
            )
            adversarial = preview.render(
                {
                    "runs": [
                        {
                            "label": adversarial_label,
                            "report_sha256": "</code><script>window.__medorigin_xss=2</script>",
                            "fixture_sha256": '<iframe src="https://example.invalid/">',
                            "structural_status": "valid",
                            "malformed_exit": 1,
                        }
                    ]
                }
            )
            # Regression for #620: even an unusually long HTML-escaped label
            # must remain visible without horizontal scroll at phone widths.
            for width, height in VIEWPORTS:
                page = browser.new_page(viewport={"width": width, "height": height})
                failures, external = _assert_page(page)
                page.set_content(adversarial)
                if page.locator("article.result h3").inner_text() != adversarial_label:
                    raise AssertionError("escaped synthetic label was lost or altered")
                if page.evaluate("document.documentElement.scrollWidth > innerWidth + 1"):
                    raise AssertionError("long escaped label overflows viewport")
                if page.evaluate("window.__medorigin_xss") is not None:
                    raise AssertionError("injected script executed")
                if page.locator("img, iframe, script").count() or external or failures:
                    raise AssertionError("injected HTML became active or escaped browser")
                page.close()
        finally:
            browser.close()


def _sentry_offline() -> None:
    import sentry_sdk  # type: ignore[import-not-found]

    captured: list[Any] = []

    class InMemoryTransport(sentry_sdk.transport.Transport):  # type: ignore[misc]
        def capture_envelope(self, envelope: Any) -> None:
            captured.append(envelope)

    def before_send(event: dict[str, Any], _hint: Any) -> dict[str, Any]:
        for key in ("user", "request", "contexts", "breadcrumbs", "tags", "extra"):
            event.pop(key, None)
        return event

    sentry_sdk.init(
        dsn="https://public@example.invalid/1",
        transport=InMemoryTransport(),
        send_default_pii=False,
        traces_sample_rate=0.0,
        auto_session_tracking=False,
        default_integrations=False,
        environment="medorigin-offline-synthetic-only",
        before_send=before_send,
    )
    sentinel = "SYNTHETIC-PII-SENTINEL"
    try:
        try:
            preview.admit_receipt({"runs": [], "patient_name": sentinel}, directory=DEMO)
        except ValueError as exc:
            event_id = sentry_sdk.capture_exception(exc)
        else:
            raise AssertionError("untrusted receipt unexpectedly accepted")
        if not event_id or len(captured) != 1:
            raise AssertionError("Sentry memory-only event was not captured")
        if sentinel in str(captured[0]) or "patient_name" in str(captured[0]):
            raise AssertionError("unexpected synthetic input leaked into Sentry event")
    finally:
        sentry_sdk.get_client().close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli311", required=True, type=Path)
    parser.add_argument("--cli312", required=True, type=Path)
    parser.add_argument("--edge", required=True, type=Path)
    args = parser.parse_args()
    for path in (args.cli311, args.cli312, args.edge):
        if not path.is_file():
            parser.error("installed QA executable unavailable")

    with tempfile.TemporaryDirectory(prefix="medorigin-free-qa-") as scratch:
        evidence = Path(scratch) / "evidence"
        html = Path(scratch) / "preview.html"
        _run_local(
            [
                sys.executable,
                str(DEMO / "reproduce.py"),
                "--cli",
                str(args.cli311),
                "--alt-cli",
                str(args.cli312),
                "--out",
                str(evidence),
            ]
        )
        receipt_file = evidence / "evidence.json"
        if not receipt_file.is_file():
            raise AssertionError("synthetic installed-Core evidence not produced")
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        verified = preview.admit_receipt(receipt, directory=evidence)
        if len(verified["runs"]) != 2 or any(
            HEX_256.fullmatch(run["report_sha256"]) is None for run in verified["runs"]
        ):
            raise AssertionError("invalid cross-Python installed-Core results")
        _run_local(
            [
                sys.executable,
                str(DEMO / "preview.py"),
                "--receipt",
                str(receipt_file),
                "--out",
                str(html),
            ],
            timeout=40,
        )
        _browser_checks(html, args.edge)
        _sentry_offline()

    print("MEDORIGIN_FREE_AUTOMATED_REVIEW_PASS")
    print("PLAYWRIGHT_VIEWPORTS=3 INJECTION_CASES=3")
    print("SENTRY_MEMORY_EVENTS=1 SENTRY_NETWORK_EVENTS=0")
    print("SYNTHETIC_INSTALLED_CORE_RUNTIMES=2")
    print("PUBLICATION_AUTHORIZED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
