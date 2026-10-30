"""Browser regression for the unpublished synthetic-only Developer Beta preview.

No PHI, external URLs, cloud backend, browser uploads, or JavaScript is required.
Run with: python scripts/qa/preview_mobile_playwright.py
Requires a separately installed Playwright Chromium test browser.
"""

from __future__ import annotations

from pathlib import Path
import runpy

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[2]
RENDERER = ROOT / "examples" / "synthetic_fhir_developer_beta" / "preview.py"
WIDTHS = (320, 375, 390, 768, 1280)


def _preview(label: str) -> str:
    render = runpy.run_path(str(RENDERER))["render"]
    receipt = {
        "runs": [
            {
                "label": label,
                "structural_status": "valid",
                "valid_exit": 0,
                "malformed_exit": 1,
                "report_sha256": "a" * 64,
                "fixture_sha256": "b" * 64,
            },
            {
                "label": "run_2",
                "structural_status": "valid",
                "valid_exit": 0,
                "malformed_exit": 1,
                "report_sha256": "a" * 64,
                "fixture_sha256": "b" * 64,
            },
        ]
    }
    return render(receipt)


def main() -> None:
    attack = 'test <img src=x onerror=window.__medoriginInjected=true>'
    cases = {
        "normal": "run_1",
        "escaped-html": attack,
        "continuous-long-token": "synthetic-" + "x" * 250,
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for case_name, label in cases.items():
                html = _preview(label)
                # No markup injection in the original renderer output.
                assert "<img src=x" not in html, case_name
                assert "<script" not in html.lower(), case_name
                for width in WIDTHS:
                    page = browser.new_page(
                        viewport={"width": width, "height": 700},
                        device_scale_factor=1,
                    )
                    requests: list[str] = []
                    errors: list[str] = []
                    page.on("request", lambda request, requests=requests: requests.append(request.url))
                    page.on("pageerror", lambda error, errors=errors: errors.append(str(error)))
                    try:
                        page.set_content(html, wait_until="load")
                        assert page.locator("article.result").count() == 2
                        assert page.locator("article.result h3").first.text_content() == label
                        assert page.locator("article.result .status").all_text_contents() == [
                            "PASSED",
                            "PASSED",
                        ]
                        assert page.locator("img, script, iframe, object, embed").count() == 0
                        assert page.evaluate(
                            "typeof window.__medoriginInjected === 'undefined'"
                        )
                        metrics = page.evaluate(
                            """() => ({
                              viewport: window.innerWidth,
                              html: document.documentElement.scrollWidth,
                              body: document.body.scrollWidth
                            })"""
                        )
                        assert metrics["viewport"] == width
                        assert metrics["html"] <= width + 1, (
                            case_name,
                            width,
                            metrics,
                        )
                        assert metrics["body"] <= width + 1, (
                            case_name,
                            width,
                            metrics,
                        )
                        assert requests == [], (case_name, width, requests)
                        assert errors == [], (case_name, width, errors)
                        print(f"PASS: {case_name}, {width}px, no overflow/network/injection")
                    finally:
                        page.close()
        finally:
            browser.close()


if __name__ == "__main__":
    main()
