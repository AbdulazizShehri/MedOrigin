"""Real Edge browser UI smoke with a fully mocked *synthetic* Tauri IPC bridge.

No application launch, external HTTP, packet-level evidence, PHI, or release approval.
Run only after the locked frontend has been built: python tests/browser_fhir_preview_e2e.py
"""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import threading
import unittest
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, expect

DIST = Path(__file__).resolve().parents[1] / "dist"

MOCK_BRIDGE = r"""
(() => {
  const samples = {
    "patient-minimal": ["747e1e038d6cc9a39a9cee209f621841cf6a9748d82be42fa545f19cfd6877a0", 57, "FHIR_ENVELOPE_OK"],
    "patient-invalid-utf8": ["a8100ae6aa1940d0b663bb31cd466142ebbdbd5187131b92d93818987832eb89", 1, "INVALID_UTF8"],
    "patient-over-limit": ["b929f15ca4f3fa28f54991ed0cb8ac5f430e388ee08bf401a853d8af91e44538", 32769, "RESOURCE_TOO_LARGE"],
    "patient-exact-limit": ["ea711ce560191a81c0722c4a26592e0e2d9abb2186b6fd3af6897cd89d417d4e", 32768, "FHIR_ENVELOPE_OK"],
    "observation-minimal": ["527806e5427cc45e55424d1b8dc8ddcdc86a2b37df2ae116735e6832268b5e19", 251, "FHIR_ENVELOPE_OK"],
    "observation-bad-subject": ["d2332ed753a59b46d19a11849cccd96a4250120ad3eab455580ce45b1d91b838", 253, "INVALID_REFERENCE"]
  };
  window.__testInspectCalls = 0;
  window.__testForgeEnvelope = false;
  window.__testForgeHash = false;
  window.__TAURI_INTERNALS__ = {
    invoke: async (command, args = {}) => {
      if (command === "preview_status") {
        return {mode: "SYNTHETIC_DEVELOPER_PREVIEW", data_access: "six_allowlisted_in_memory_fixtures_only",
          release_authorized: false, production_parity_qualified: false,
          app_network_plugins_enabled: false, webview_runtime_egress_qualified: false};
      }
      const item = samples[args.fixtureId];
      if (!item || args.maxInputBytes !== 65536) throw "unknown_fixture";
      if (command === "hash_fixture") {
        return {contract: "medorigin-desktop-d0-raw-sha256-v1", fixture_id: args.fixtureId,
          bytes: item[1], sha256_hex: window.__testForgeHash ? "0".repeat(64) : item[0],
          synthetic_only: true, release_authorized: false};
      }
      if (command === "inspect_fhir_fixture_envelope") {
        window.__testInspectCalls++;
        return {contract: "medorigin-d0-synthetic-fhir-envelope-v1", fixture_id: args.fixtureId,
          bytes: item[1], status: window.__testForgeEnvelope ? "INVALID_REFERENCE" : item[2],
          synthetic_only: true, full_fhir_r4_validated: false, release_authorized: false};
      }
      throw "unexpected_command";
    }
  };
})();
"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass


class PreviewBrowserChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not (DIST / "index.html").is_file():
            raise AssertionError("Build the checked-out Tauri frontend with npm run build first")
        cls.http = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(QuietHandler, directory=str(DIST))
        )
        cls.server_thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.local_url = f"http://127.0.0.1:{cls.http.server_address[1]}/"
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            channel="msedge", headless=True, args=["--disable-background-networking", "--no-first-run"]
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.browser.close()
        cls.playwright.stop()
        cls.http.shutdown()
        cls.http.server_close()
        cls.server_thread.join(timeout=5)

    def setUp(self) -> None:
        self.page = self.browser.new_page(viewport={"width": 375, "height": 800})
        self.outbound: list[str] = []
        self.page.add_init_script(script=MOCK_BRIDGE)

        def route(request_route) -> None:
            url = urlparse(request_route.request.url)
            if url.hostname != "127.0.0.1" or url.port != urlparse(self.local_url).port:
                self.outbound.append(request_route.request.url)
                request_route.abort()
            else:
                request_route.continue_()

        self.page.route("**/*", route)
        self.page.goto(self.local_url, wait_until="networkidle")
        expect(self.page.get_by_role("button", name="Verify with Rust")).to_be_enabled()

    def tearDown(self) -> None:
        self.assertEqual(self.outbound, [], "No nonlocal web requests allowed")
        self.page.close()

    def choose_and_verify(self, label: str) -> None:
        self.page.get_by_role("button", name=re.compile(label)).click()
        self.page.get_by_role("button", name="Verify with Rust").click()

    def test_valid_and_broken_subject_responses(self) -> None:
        self.assertEqual(self.page.locator(".fixture").count(), 6)
        self.choose_and_verify("Fictional Observation")
        expect(self.page.locator(".envelope-result")).to_contain_text(
            "Basic fictional resource fields found"
        )
        self.choose_and_verify("Broken patient reference")
        expect(self.page.locator(".envelope-result")).to_contain_text("INVALID REFERENCE")
        expect(self.page.locator(".outcome-success")).to_have_count(1)

    def test_forged_second_bridge_response_never_shows_success(self) -> None:
        self.page.evaluate("window.__testForgeEnvelope = true")
        self.choose_and_verify("Fictional Observation")
        expect(self.page.locator(".outcome-success")).to_have_count(0)
        expect(self.page.locator(".envelope-result")).to_have_count(0)
        expect(self.page.locator(".outcome-error")).to_contain_text(
            "The local Rust command refused this request"
        )

    def test_hash_mismatch_never_invokes_structural_check(self) -> None:
        self.page.evaluate("window.__testForgeHash = true")
        self.choose_and_verify("Fictional Observation")
        expect(self.page.locator(".outcome-error")).to_contain_text("MISMATCH")
        self.assertEqual(self.page.evaluate("window.__testInspectCalls"), 0)
        expect(self.page.locator(".envelope-result")).to_have_count(0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
