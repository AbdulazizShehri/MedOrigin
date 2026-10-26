"""Read-only MedOrigin GitHub security alert coverage and visibility audit.

A 200 response with zero items means *zero visible alerts*, never "secure".
A disabled Dependabot endpoint, missing access, truncated pages, and unavailable
secret scanning must not silently become empty alert inventories.

This diagnostic never changes repository settings, installs dependencies,
publishes artifacts, or decides clinical/release readiness.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from typing import Any

_ENDPOINTS = {
    "dependabot": "dependabot/alerts",
    "code_scanning": "code-scanning/alerts",
    "secret_scanning": "secret-scanning/alerts",
}
_MAX_PAGES = 30
_PAGE_SIZE = 100


def classify(
    status_code: int,
    payload: Any,
    *,
    page_count: int = 1,
    complete: bool = True,
) -> dict[str, Any]:
    """Classify GitHub security telemetry; never translate errors into zero."""
    if status_code == 200:
        if (
            not isinstance(payload, list)
            or any(not isinstance(item, dict) for item in payload)
            or page_count < 1
            or page_count > _MAX_PAGES
            or not complete
            or any(
                type(item.get("number")) is not int
                or item["number"] < 1
                or item.get("state", "open") != "open"
                for item in payload
            )
            or len({item["number"] for item in payload}) != len(payload)
        ):
            return {"status": "UNVERIFIABLE", "visible_alert_count": None}
        return {"status": "VISIBLE", "visible_alert_count": len(payload)}
    msg = ""
    if isinstance(payload, dict):
        msg = str(payload.get("message", "")).casefold()
    if status_code == 403 and "alerts are disabled" in msg:
        state = "DISABLED"
    elif status_code in {401, 403}:
        state = "ACCESS_DENIED"
    elif status_code == 404:
        state = "UNAVAILABLE_OR_NOT_FOUND"
    else:
        state = "UNVERIFIABLE"
    return {"status": state, "visible_alert_count": None}


def audit(reports: dict[str, dict[str, Any]]) -> dict[str, Any]:
    issues: list[str] = []
    summary: dict[str, Any] = {}
    for key in _ENDPOINTS:
        item = reports.get(key)
        if not isinstance(item, dict):
            entry = {"status": "UNVERIFIABLE", "visible_alert_count": None}
        else:
            entry = classify(
                item.get("http_status", 0),
                item.get("payload"),
                page_count=item.get("page_count", 0),
                complete=item.get("complete", False),
            )
        summary[key] = entry
        if entry["status"] != "VISIBLE":
            issues.append(f"{key}: {entry['status']}; alert visibility not established")
        elif entry["visible_alert_count"]:
            issues.append(
                f"{key}: {entry['visible_alert_count']} visible alerts require assessment"
            )
    return {
        "status": "SECURITY_ALERT_SIGNALS_VISIBLE_ONLY" if not issues else "BLOCKED",
        "repository_security_signals": summary,
        "issues": issues,
        "vulnerability_free": False,
        "independent_security_review_complete": False,
        "publication_authorized": False,
    }


def _gh_json(path: str) -> Any:
    process = subprocess.run(
        ["gh", "api", path],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    try:
        payload = json.loads(process.stdout)
    except (json.JSONDecodeError, TypeError):
        payload = {"message": process.stderr.strip()}
    return process.returncode, payload


def _gh_cursor_json(path: str) -> tuple[int, Any]:
    """Use GitHub Link cursors (not unsupported page=N) for Dependabot."""
    process = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", path],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    try:
        payload = json.loads(process.stdout)
    except (json.JSONDecodeError, TypeError):
        payload = {"message": process.stderr.strip()}
    return process.returncode, payload


def _failure_status(result_code: int, result: Any) -> int:
    message = str(result.get("message", "")) if isinstance(result, dict) else ""
    lowered = message.casefold()
    if result_code != 0 and "alerts are disabled" in lowered:
        return 403
    if result_code != 0 and "not found" in lowered:
        return 404
    if result_code != 0 and any(
        word in lowered for word in ("forbidden", "resource not accessible", "bad credentials")
    ):
        return 403
    return 0


def live(repository: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("invalid repository")
    reports: dict[str, dict[str, Any]] = {}
    for key, endpoint in _ENDPOINTS.items():
        if key == "dependabot":
            # GitHub removed offset page=N pagination in October 2025.
            # The CLI follows the cursor Link headers and --slurp groups
            # pages, allowing a bounded, complete local validation.
            code, slurped = _gh_cursor_json(
                f"repos/{repository}/{endpoint}?state=open&per_page={_PAGE_SIZE}"
            )
            valid = (
                code == 0
                and isinstance(slurped, list)
                and 1 <= len(slurped) <= _MAX_PAGES
                and all(isinstance(page, list) and len(page) <= _PAGE_SIZE for page in slurped)
            )
            if valid:
                alerts = [alert for page in slurped for alert in page]
                reports[key] = {
                    "http_status": 200,
                    "payload": alerts,
                    "page_count": len(slurped),
                    "complete": True,
                }
            else:
                reports[key] = {
                    "http_status": _failure_status(code, slurped),
                    "payload": slurped,
                    "page_count": len(slurped) if isinstance(slurped, list) else 0,
                    "complete": False,
                }
            continue
        pages: list[dict[str, Any]] = []
        status = 200
        payload: Any = []
        complete = False
        count = 0
        for page in range(1, _MAX_PAGES + 1):
            count = page
            result_code, result = _gh_json(
                f"repos/{repository}/{endpoint}?state=open&per_page={_PAGE_SIZE}&page={page}"
            )
            # gh returns nonzero on 403; status is not preserved by default.
            # Distinguish a returned success JSON array from denied access,
            # never silently call a denied result "zero alerts".
            if result_code != 0 or not isinstance(result, list):
                status = _failure_status(result_code, result)
                payload = result
                break
            pages.extend(result)
            if len(result) < _PAGE_SIZE:
                complete = True
                payload = pages
                break
        else:
            status = 0
            payload = {"message": "pagination budget exceeded"}
        reports[key] = {
            "http_status": status,
            "payload": payload,
            "page_count": count,
            "complete": complete,
        }
    result = audit(reports)
    result["repository"] = repository
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default="AbdulazizShehri/MedOrigin")
    args = parser.parse_args(argv)
    try:
        result = live(args.repository)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        result = {
            "status": "BLOCKED",
            "issues": [f"unverifiable security visibility: {exc.__class__.__name__}"],
            "vulnerability_free": False,
            "independent_security_review_complete": False,
            "publication_authorized": False,
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["status"] == "SECURITY_ALERT_SIGNALS_VISIBLE_ONLY" else 2


if __name__ == "__main__":
    sys.exit(main())
