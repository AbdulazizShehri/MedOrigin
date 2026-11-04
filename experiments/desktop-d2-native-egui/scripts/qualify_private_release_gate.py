#!/usr/bin/env python3
"""GitHub-backed private release NO-GO monitor for MedOrigin, NEVER approval.

This QA tool never ships in D2, requires authorized gh access and does not
change any issue, security alert, branch, release, artifact, or remote setting.
"""
from __future__ import annotations

from collections import Counter
import json
import shutil
import subprocess
import sys

REPO = "AbdulazizShehri/MedOrigin"
BLOCKER_ISSUES = (574, 603, 622, 662, 673, 676)
SEVERITIES = frozenset({"critical", "high", "medium", "low"})
MAX_OPEN_ALERTS = 1000
STATUS = "NO_GO_INDEPENDENT_SECURITY_CLINICAL_AND_OWNER_RELEASE_GATES_UNMET"
MAX_GH_API_BYTES = 8_000_000


class QualificationRefused(ValueError):
    """Refuse a missing or implausible source of release evidence."""


def gh_json(resource: str) -> object:
    if not resource.startswith("repos/" + REPO + "/"):
        raise QualificationRefused("unapproved_github_resource")
    if shutil.which("gh") is None:
        raise QualificationRefused("authenticated_github_cli_unavailable")
    proc = subprocess.run(
        ["gh", "api", resource],
        capture_output=True, timeout=25, check=False,
    )
    if proc.returncode != 0:
        raise QualificationRefused("github_security_evidence_unavailable")
    if not proc.stdout or len(proc.stdout) > MAX_GH_API_BYTES:
        raise QualificationRefused("github_security_response_size_refused")
    try:
        return json.loads(proc.stdout)
    except ValueError as exc:
        raise QualificationRefused("github_security_response_not_json") from exc


def live_security_snapshot() -> tuple[list[dict], dict[int, dict]]:
    # Dependabot's REST endpoint uses cursor-based Link pagination, not a
    # `page=` query parameter. gh --paginate follows its trusted Link headers.
    endpoint = "repos/" + REPO + "/dependabot/alerts?state=open&per_page=100"
    if shutil.which("gh") is None:
        raise QualificationRefused("authenticated_github_cli_unavailable")
    proc = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", endpoint],
        capture_output=True, timeout=90, check=False,
    )
    if proc.returncode != 0 or not proc.stdout or len(proc.stdout) > MAX_GH_API_BYTES:
        raise QualificationRefused("github_security_alert_inventory_unavailable")
    try:
        pages = json.loads(proc.stdout)
    except ValueError as exc:
        raise QualificationRefused("github_security_alert_pages_invalid_json") from exc
    if not isinstance(pages, list) or not pages or len(pages) > 11:
        raise QualificationRefused("github_security_alert_pages_invalid")
    alerts: list[dict] = []
    for page_data in pages:
        if not isinstance(page_data, list) or len(page_data) > 100:
            raise QualificationRefused("github_security_alert_page_invalid")
        alerts.extend(page_data)
        if len(alerts) > MAX_OPEN_ALERTS:
            raise QualificationRefused("github_security_alert_inventory_over_limit")
    issues: dict[int, dict] = {}
    for issue_number in BLOCKER_ISSUES:
        item = gh_json(f"repos/{REPO}/issues/{issue_number}")
        if not isinstance(item, dict):
            raise QualificationRefused("github_blocker_issue_unavailable")
        issues[issue_number] = item
    return alerts, issues


def determine_release_status(alerts: list[dict], issues: dict[int, dict]) -> dict:
    if not isinstance(alerts, list) or len(alerts) > MAX_OPEN_ALERTS:
        raise QualificationRefused("invalid_alert_inventory")
    seen: set[int] = set()
    severity_count: Counter[str] = Counter()
    by_manifest: Counter[str] = Counter()
    by_package: Counter[str] = Counter()
    for alert in alerts:
        if not isinstance(alert, dict):
            raise QualificationRefused("invalid_alert_record")
        number = alert.get("number")
        state = alert.get("state")
        if type(number) is not int or number <= 0 or number in seen or state != "open":
            raise QualificationRefused("duplicate_or_nonopen_alert_record")
        seen.add(number)
        dependency = alert.get("dependency")
        advisory = alert.get("security_advisory")
        if not isinstance(dependency, dict) or not isinstance(advisory, dict):
            raise QualificationRefused("missing_alert_advisory_dependency")
        package = dependency.get("package")
        manifest = dependency.get("manifest_path")
        severity = advisory.get("severity")
        if (
            not isinstance(package, dict)
            or not isinstance(package.get("name"), str)
            or not package["name"].strip()
            or not isinstance(manifest, str) or not manifest.strip()
            or severity not in SEVERITIES
        ):
            raise QualificationRefused("alert_security_scope_undetermined")
        severity_count[severity] += 1
        by_manifest[manifest] += 1
        by_package[package["name"].lower()] += 1

    if set(issues) != set(BLOCKER_ISSUES):
        raise QualificationRefused("incomplete_release_issue_set")
    open_issues: list[int] = []
    for expected, item in issues.items():
        if not isinstance(item, dict) or type(item.get("number")) is not int:
            raise QualificationRefused("invalid_release_issue_record")
        if item["number"] != expected or item.get("state") not in ("open", "closed"):
            raise QualificationRefused("release_issue_identity_or_state_invalid")
        if item["state"] == "open":
            open_issues.append(expected)

    return {
        "status": STATUS,
        "release_authorized": False,
        "clinical_data_authorized": False,
        "independent_security_review_qualified": False,
        "full_fhir_r4_validator_qualified": False,
        "native_three_os_packet_isolation_qualified": False,
        "clinical_workspace_product_qualified": False,
        "founder_release_approval_verified": False,
        "dependabot_open_total": len(alerts),
        "dependabot_open_by_severity": {
            key: severity_count[key] for key in ("critical", "high", "medium", "low")
        },
        "dependabot_affected_manifests": dict(sorted(by_manifest.items())),
        "dependabot_affected_packages": sorted(by_package),
        "dependency_reachability_to_native_d2": "NOT_DETERMINED_FROM_ALERT_API",
        "open_release_blocker_issues": sorted(open_issues),
        "all_required_issue_ids_checked": list(BLOCKER_ISSUES),
        "require_independent_review_even_if_issues_and_alerts_close": True,
    }


def main() -> int:
    try:
        alerts, issues = live_security_snapshot()
        result = determine_release_status(alerts, issues)
        print(json.dumps(result, sort_keys=True))
        print("MEDORIGIN_PRIVATE_RELEASE_GUARD_ENFORCED_NO_GO")
    except (QualificationRefused, OSError, subprocess.SubprocessError) as exc:
        print("MEDORIGIN_RELEASE_GUARD_NO_GO_EVIDENCE_UNAVAILABLE:" + str(exc),
              file=sys.stderr)
    # Deliberately no path to exit zero; independent sign-offs and clinical
    # approvals cannot be generated or self-awarded by an assistant or script.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
