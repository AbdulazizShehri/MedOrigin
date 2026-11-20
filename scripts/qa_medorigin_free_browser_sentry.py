"""Free, nonpublishing MedOrigin QA with Playwright and local-only Sentry.

Only bundled fictional FHIR records may be used. Network access is needed only
to provision QA packages in CI; the browser and Sentry run against local data
without telemetry or application-data uploads. No release side effects.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from importlib import import_module
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "synthetic_fhir_developer_beta"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(DEMO))

import check_installed_core_fhir_provenance as core_gate  # noqa: E402
import core_truth_preview  # type: ignore[import-not-found]  # noqa: E402
import preview  # type: ignore[import-not-found]  # noqa: E402
from qualify_medorigin_developer_beta import qualify  # noqa: E402

VIEWPORTS = ((375, 667), (850, 610), (1440, 900))
HEX_256 = re.compile(r"[0-9a-f]{64}\Z")


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


def _browser_checks(html: Path, edge: Path, known_sha: str, unknown_sha: str) -> None:
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
                page.locator("article").first.wait_for()
                if (
                    page.locator("style").count() != 1
                    or page.locator('meta[http-equiv="Content-Security-Policy"]').count() != 1
                    or page.evaluate("document.styleSheets.length") != 1
                    or page.evaluate("getComputedStyle(document.body).margin") != "0px"
                ):
                    raise AssertionError("truthful preview CSS/CSP markup was not parsed")
                if page.locator("article").count() != 2:
                    raise AssertionError("two independently proven fictional cases required")
                if page.locator("article strong").all_inner_texts() != [
                    "NOT VALIDATED",
                    "NOT VALIDATED",
                ]:
                    raise AssertionError("both fictional reports must be NOT VALIDATED")
                if page.locator("article code").all_inner_texts() != [known_sha, unknown_sha]:
                    raise AssertionError("rendered source-qualified report SHA digests differ")
                if "NOT AUTHORIZED" not in page.locator("footer").inner_text():
                    raise AssertionError("nonclinical/nonpublication warning must be visible")
                if page.evaluate("document.documentElement.scrollWidth > innerWidth"):
                    raise AssertionError("horizontal overflow on compact viewport")
                if page.locator("script, iframe, img, form, link").count():
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
                            # Pure renderer receives intentionally
                            # hostile text with a valid v2 *control* shape.
                            # The authoritative admit_receipt() still rejects
                            # these malicious digests at its trust boundary.
                            "provenance_status": "not_validated",
                            "validation_exit": 2,
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
            core_truth_preview.admit_installed_core_proof(
                {"status": "valid", "patient_name": sentinel}
            )
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
    parser.add_argument("--python311", required=True, type=Path)
    parser.add_argument("--python312", required=True, type=Path)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--sdist", required=True, type=Path)
    parser.add_argument("--edge", required=True, type=Path)
    args = parser.parse_args()
    for path in (args.python311, args.python312, args.wheel, args.sdist, args.edge):
        if not path.is_file():
            parser.error("source-bound QA artifact or executable unavailable")

    # The whole source/installer gate must pass before a browser can inspect
    # metadata. A legacy false-'valid' FHIR preview is NEVER a fallback.
    qualified = qualify(
        ROOT,
        args.wheel,
        args.sdist,
        args.python311,
        args.python312,
        core_negative_truth_preview=True,
    )
    if (
        qualified.get("status") != "TECHNICAL_CORE_NEGATIVE_TRUTH_PREVIEW_ONLY"
        or qualified.get("installed_python_source_files_verified_per_runtime", 0) < 50
        or any(
            qualified.get(key) is not False
            for key in (
                "fhir_conformance_validated",
                "prepublication_rehearsal_qualified",
                "clinical_use_authorized",
                "publication_authorized",
                "native_launcher_identity_attested",
                "full_beta_preview_qualified",
                "merge_or_tag_authorized",
            )
        )
    ):
        raise AssertionError("source-qualified Core negative-truth gate refused")
    suffix = ".exe" if sys.platform == "win32" else ""
    clis = [
        args.python311.parent / ("medscale" + suffix),
        args.python312.parent / ("medscale" + suffix),
    ]
    with tempfile.TemporaryDirectory(prefix="medorigin-free-qa-") as scratch:
        evidence = Path(scratch) / "evidence"
        proof = core_gate.qualify(clis, interpreters=[args.python311, args.python312])
        created = core_truth_preview.write_negative_truth_preview(evidence, proof)
        record = evidence / "core-negative-truth.json"
        html = evidence / "core-negative-truth.html"
        receipt = json.loads(record.read_text(encoding="utf-8"))
        if receipt != core_truth_preview.admit_installed_core_proof(proof):
            raise AssertionError("source-verified evidence does not match recorded receipt")
        if any(
            not isinstance(receipt[key], str)
            or HEX_256.fullmatch(receipt[key]) is None
            or receipt[key] != qualified[key]
            for key in ("known_report_sha256", "unknown_report_sha256")
        ):
            raise AssertionError("independent installed-Core SHA proofs differ")
        if (
            hashlib.sha256(record.read_bytes()).hexdigest() != qualified["record_sha256"]
            or hashlib.sha256(html.read_bytes()).hexdigest() != qualified["preview_sha256"]
            or created["record_sha256"] != qualified["record_sha256"]
            or created["preview_sha256"] != qualified["preview_sha256"]
            or html.read_text(encoding="utf-8")
            != core_truth_preview.render_negative_truth_preview(receipt)
        ):
            raise AssertionError("source-bound inert preview bytes differ")
        _browser_checks(
            html,
            args.edge,
            receipt["known_report_sha256"],
            receipt["unknown_report_sha256"],
        )
        _sentry_offline()

    print("MEDORIGIN_SOURCE_BOUND_NEGATIVE_TRUTH_BROWSER_SENTRY_PASS_NOT_RELEASE")
    print("PLAYWRIGHT_VIEWPORTS=3 INJECTION_CASES=3")
    print("SENTRY_MEMORY_EVENTS=1 SENTRY_NETWORK_EVENTS=0")
    print("SYNTHETIC_INSTALLED_CORE_RUNTIMES=2")
    print("FHIR_CONFORMANCE_VALIDATED=false")
    print("FULL_BETA_PREPUBLICATION_QUALIFIED=false")
    print("PUBLICATION_AUTHORIZED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
