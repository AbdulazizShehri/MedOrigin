"""No-credentials, synthetic cases for MedOrigin free security visibility audit."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_medorigin_security_visibility.py"


@pytest.fixture
def audit_tool() -> Any:
    spec = importlib.util.spec_from_file_location("medorigin_security_visibility", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("http_status", "payload", "state", "count"),
    [
        (200, [], "VISIBLE", 0),
        (200, [{"number": 1}], "VISIBLE", 1),
        (403, {"message": "Dependabot alerts are disabled for this repository."}, "DISABLED", None),
        (403, {"message": "Resource not accessible by integration"}, "ACCESS_DENIED", None),
        (401, {"message": "Bad credentials"}, "ACCESS_DENIED", None),
        (404, {"message": "Not Found"}, "UNAVAILABLE_OR_NOT_FOUND", None),
        (500, {"message": "Internal Server Error"}, "UNVERIFIABLE", None),
        (200, {"message": "not a list"}, "UNVERIFIABLE", None),
        (200, [{"number": 1}, "bad-item"], "UNVERIFIABLE", None),
        (200, [{}], "UNVERIFIABLE", None),
        (200, [{"number": True}], "UNVERIFIABLE", None),
        (200, [{"number": -2}], "UNVERIFIABLE", None),
        (200, [{"number": 5}, {"number": 5}], "UNVERIFIABLE", None),
        (200, [{"number": 9, "state": "dismissed"}], "UNVERIFIABLE", None),
    ],
)
def test_security_signal_status_is_never_implicitly_empty(
    audit_tool: Any, http_status: int, payload: Any, state: str, count: int | None
) -> None:
    result = audit_tool.classify(http_status, payload)
    assert result["status"] == state
    assert result["visible_alert_count"] == count


def test_missing_page_blocks_instead_of_truncating(audit_tool: Any) -> None:
    assert audit_tool.classify(200, [], complete=False)["status"] == "UNVERIFIABLE"
    assert audit_tool.classify(200, [], page_count=31)["status"] == "UNVERIFIABLE"


def test_visible_zero_across_all_scanners_does_not_mean_secure(audit_tool: Any) -> None:
    result = audit_tool.audit(
        {
            name: {
                "http_status": 200,
                "payload": [],
                "page_count": 1,
                "complete": True,
            }
            for name in ("dependabot", "code_scanning", "secret_scanning")
        }
    )
    assert result["status"] == "SECURITY_ALERT_SIGNALS_VISIBLE_ONLY"
    assert result["vulnerability_free"] is False
    assert result["publication_authorized"] is False
    assert result["independent_security_review_complete"] is False


def test_disabled_dependabot_fails_even_with_other_empty_signals(audit_tool: Any) -> None:
    sample = {
        name: {
            "http_status": 200,
            "payload": [],
            "page_count": 1,
            "complete": True,
        }
        for name in ("dependabot", "code_scanning", "secret_scanning")
    }
    sample["dependabot"] = {
        "http_status": 403,
        "payload": {"message": "Dependabot alerts are disabled for this repository."},
        "page_count": 1,
        "complete": False,
    }
    result = audit_tool.audit(sample)
    assert result["status"] == "BLOCKED"
    assert result["repository_security_signals"]["dependabot"]["status"] == "DISABLED"
    assert result["repository_security_signals"]["code_scanning"]["visible_alert_count"] == 0
    assert result["publication_authorized"] is False


def test_visible_alerts_need_triage(audit_tool: Any) -> None:
    data = {
        name: {
            "http_status": 200,
            "payload": [],
            "page_count": 1,
            "complete": True,
        }
        for name in ("dependabot", "code_scanning", "secret_scanning")
    }
    data["code_scanning"]["payload"] = [{"number": 4}]
    result = audit_tool.audit(data)
    assert result["status"] == "BLOCKED"
    assert "1 visible alerts" in result["issues"][0]


def test_paginated_fetch_preserves_counts(audit_tool: Any, monkeypatch: Any) -> None:
    calls: list[str] = []

    def response(endpoint: str) -> tuple[int, Any]:
        calls.append(endpoint)
        if endpoint.endswith("&page=1"):
            return 0, [{"number": index} for index in range(1, 101)]
        return 0, [{"number": 101}]

    monkeypatch.setattr(audit_tool, "_gh_json", response)
    monkeypatch.setattr(
        audit_tool,
        "_gh_cursor_json",
        lambda _: (
            0,
            [
                [{"number": index} for index in range(1, 101)],
                [{"number": 101}],
            ],
        ),
    )
    result = audit_tool.live("AbdulazizShehri/MedOrigin")
    assert result["status"] == "BLOCKED"
    assert all(
        result["repository_security_signals"][key]["visible_alert_count"] == 101
        for key in ("dependabot", "code_scanning", "secret_scanning")
    )
    assert len(calls) == 4


def test_error_payload_is_not_treated_as_no_alerts(audit_tool: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(
        audit_tool,
        "_gh_json",
        lambda _: (1, {"message": "Dependabot alerts are disabled for this repository."}),
    )
    monkeypatch.setattr(
        audit_tool,
        "_gh_cursor_json",
        lambda _: (1, {"message": "Dependabot alerts are disabled for this repository."}),
    )
    result = audit_tool.live("AbdulazizShehri/MedOrigin")
    assert result["status"] == "BLOCKED"
    assert all(
        item["status"] == "DISABLED" for item in result["repository_security_signals"].values()
    )


def test_invalid_repository_refused(audit_tool: Any) -> None:
    with pytest.raises(ValueError):
        audit_tool.live("somebody/../wrong")


def test_missing_scanner_signal_blocks(audit_tool: Any) -> None:
    result = audit_tool.audit({})
    assert result["status"] == "BLOCKED"
    assert len(result["issues"]) == 3


def test_duplicate_alert_numbers_across_pages_block(audit_tool: Any, monkeypatch: Any) -> None:
    def api(path: str) -> tuple[int, Any]:
        if path.endswith("&page=1"):
            return 0, [{"number": x} for x in range(1, 101)]
        return 0, [{"number": 100}]

    monkeypatch.setattr(audit_tool, "_gh_json", api)
    monkeypatch.setattr(
        audit_tool,
        "_gh_cursor_json",
        lambda _: (
            0,
            [
                [{"number": index} for index in range(1, 101)],
                [{"number": 100}],
            ],
        ),
    )
    result = audit_tool.live("AbdulazizShehri/MedOrigin")
    assert result["status"] == "BLOCKED"
    assert all(
        result["repository_security_signals"][key]["status"] == "UNVERIFIABLE"
        for key in ("dependabot", "code_scanning", "secret_scanning")
    )
    assert result["publication_authorized"] is False


def test_unknown_server_failure_not_relabelled_access_denied(
    audit_tool: Any, monkeypatch: Any
) -> None:
    monkeypatch.setattr(
        audit_tool,
        "_gh_json",
        lambda _: (1, {"message": "Internal Server Error"}),
    )
    monkeypatch.setattr(
        audit_tool,
        "_gh_cursor_json",
        lambda _: (1, {"message": "Internal Server Error"}),
    )
    result = audit_tool.live("AbdulazizShehri/MedOrigin")
    assert all(
        signal["status"] == "UNVERIFIABLE"
        for signal in result["repository_security_signals"].values()
    )
    assert result["status"] == "BLOCKED"


def test_access_denied_still_reported_distinctly(audit_tool: Any, monkeypatch: Any) -> None:
    monkeypatch.setattr(
        audit_tool,
        "_gh_json",
        lambda _: (1, {"message": "Resource not accessible by integration"}),
    )
    monkeypatch.setattr(
        audit_tool,
        "_gh_cursor_json",
        lambda _: (1, {"message": "Resource not accessible by integration"}),
    )
    result = audit_tool.live("AbdulazizShehri/MedOrigin")
    assert all(
        signal["status"] == "ACCESS_DENIED"
        for signal in result["repository_security_signals"].values()
    )


def test_dependabot_cursor_request_never_sends_unsupported_page(
    audit_tool: Any, monkeypatch: Any
) -> None:
    from types import SimpleNamespace

    seen: list[list[str]] = []

    def process(argv: list[str], **kwargs: Any) -> Any:
        seen.append(argv)
        return SimpleNamespace(
            stdout=b'[[{"number": 1}, {"number": 2}]]',
            stderr=b"",
            returncode=0,
        )

    monkeypatch.setattr(audit_tool.subprocess, "run", process)
    code, pages = audit_tool._gh_cursor_json(
        "repos/AbdulazizShehri/MedOrigin/dependabot/alerts?state=open&per_page=100"
    )
    assert code == 0
    assert len(pages) == 1 and len(pages[0]) == 2
    assert len(seen) == 1
    assert seen[0][0:4] == ["gh", "api", "--paginate", "--slurp"]
    assert not any("&page=" in arg or "?page=" in arg for arg in seen[0])


def test_dependabot_cursor_page_budget_and_malformed_pages_block(
    audit_tool: Any, monkeypatch: Any
) -> None:
    monkeypatch.setattr(audit_tool, "_gh_json", lambda _: (0, []))
    for pages in (
        [],
        [42],
        [[{"number": 1}] for _ in range(31)],
        [[{"number": 1}] * 101],
        [[{"number": 1}], [{"number": 1}]],
    ):
        monkeypatch.setattr(audit_tool, "_gh_cursor_json", lambda _, value=pages: (0, value))
        result = audit_tool.live("AbdulazizShehri/MedOrigin")
        assert result["status"] == "BLOCKED"
        assert result["repository_security_signals"]["dependabot"]["status"] == "UNVERIFIABLE"
        assert result["publication_authorized"] is False


def test_dependabot_cursor_visible_alerts_remain_release_blocked(
    audit_tool: Any, monkeypatch: Any
) -> None:
    monkeypatch.setattr(audit_tool, "_gh_json", lambda _: (0, []))
    monkeypatch.setattr(
        audit_tool,
        "_gh_cursor_json",
        lambda _: (0, [[{"number": n, "state": "open"} for n in range(1, 61)]]),
    )
    result = audit_tool.live("AbdulazizShehri/MedOrigin")
    assert result["repository_security_signals"]["dependabot"]["visible_alert_count"] == 60
    assert result["status"] == "BLOCKED"
    assert "60 visible alerts require assessment" in result["issues"][0]
    assert result["vulnerability_free"] is False


@pytest.mark.parametrize("paginated", [False, True])
def test_gh_json_utf8_bytes(audit_tool: Any, monkeypatch: Any, paginated: bool) -> None:
    """GitHub Unicode alerts must decode even with a legacy Windows locale."""
    import json
    from types import SimpleNamespace

    entry = {"number": 42, "summary": "بيانات تجريبية - café"}
    payload = [[entry]] if paginated else [entry]
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def response(argv: list[str], **kwargs: Any) -> Any:
        calls.append((argv, kwargs))
        return SimpleNamespace(
            stdout=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            stderr=b"",
            returncode=0,
        )

    monkeypatch.setattr(audit_tool.subprocess, "run", response)
    code, decoded = (
        audit_tool._gh_cursor_json("repos/owner/repo/dependabot/alerts")
        if paginated
        else audit_tool._gh_json("repos/owner/repo/code-scanning/alerts")
    )
    assert code == 0
    assert decoded == payload
    assert len(calls) == 1
    assert calls[0][1]["capture_output"] is True
    assert "text" not in calls[0][1] and "encoding" not in calls[0][1]


@pytest.mark.parametrize("paginated", [False, True])
def test_invalid_gh_utf8_fails_closed(audit_tool: Any, monkeypatch: Any, paginated: bool) -> None:
    """Never treat an undecodable CLI reply as zero visible alerts."""
    from types import SimpleNamespace

    monkeypatch.setattr(
        audit_tool.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(stdout=b"\xff", stderr=b"", returncode=0),
    )
    code, payload = (
        audit_tool._gh_cursor_json("repos/owner/repo/dependabot/alerts")
        if paginated
        else audit_tool._gh_json("repos/owner/repo/code-scanning/alerts")
    )
    assert code != 0
    assert payload == {"message": "GitHub CLI returned undecodable UTF-8 output"}
