"""Source-bound, payload-free filtered review of cold-reopened fictional FHIR imports.

The caller selects a UTC date window and/or Encounter/Observation kind.
All decrypted imports and the audit chain MUST be verified before this view.
Never join identities across independently imported fictional Bundles.
"""

from __future__ import annotations

from typing import Any


class SyntheticFileBatchFilterError(ValueError):
    """A fixed, data-free refusal of untrusted downstream review output."""


_FILTER_RESULT_KEYS = frozenset(
    {
        "schema",
        "status",
        "current_audit_head_digest",
        "from_day_utc",
        "through_day_utc",
        "resource_type_filter",
        "date_missing_included",
        "import_count",
        "source_total_event_count",
        "visible_total_event_count",
        "hidden_total_event_count",
        "imports",
        "cross_import_patient_identity_join_performed",
        "patient_identity_included",
        "resource_payload_included",
        "filesystem_export_performed",
        "network_access_performed",
        "fhir_r4_conformance_validated",
        "clinical_use_authorized",
        "release_authorized",
    }
)
_PER_IMPORT_KEYS = frozenset(
    {
        "import_ordinal",
        "audit_sequence",
        "source_content_sha256",
        "import_audit_event_digest",
        "patient_count_within_import",
        "patient_selection_mode",
        "source_event_count",
        "visible_event_count",
        "hidden_event_count",
        "events",
    }
)
_EVENT_KEYS = frozenset({"ordinal", "resource_type", "day_utc", "date_available"})


def build_source_checked_fictional_filtered_view(
    original: dict[str, Any],
    filtered: dict[str, Any],
    committed: list[dict[str, object]],
    *,
    audit_head: str,
    from_day_utc: str | None,
    through_day_utc: str | None,
    resource_type: str | None,
) -> dict[str, object]:
    """Independently reconstruct filtering from already decrypted full sources.

    A malicious downstream adapter cannot inject patient data, forged
    entries, altered ordinals, or unverified hidden import counts.
    """
    if (
        type(original) is not dict
        or type(filtered) is not dict
        or set(filtered) != _FILTER_RESULT_KEYS
        or filtered.get("schema")
        != "medorigin-core-verified-fictional-multiimport-filtered-timelines/v1"
        or filtered.get("status") != "verified_source_scoped_fictional_timeline_view"
        or filtered.get("current_audit_head_digest") != audit_head
        or filtered.get("from_day_utc") != from_day_utc
        or filtered.get("through_day_utc") != through_day_utc
        or filtered.get("resource_type_filter") != resource_type
        or filtered.get("date_missing_included")
        is not (from_day_utc is None and through_day_utc is None)
        or type(filtered.get("import_count")) is not int
        or filtered["import_count"] != len(committed)
        or type(filtered.get("imports")) is not list
        or len(filtered["imports"]) != len(committed)
        or type(original.get("imports")) is not list
        or len(original["imports"]) != len(committed)
        or type(filtered.get("source_total_event_count")) is not int
        or filtered["source_total_event_count"] != original.get("total_event_count")
        or type(filtered.get("visible_total_event_count")) is not int
        or type(filtered.get("hidden_total_event_count")) is not int
        or any(
            filtered.get(key) is not False
            for key in (
                "cross_import_patient_identity_join_performed",
                "patient_identity_included",
                "resource_payload_included",
                "filesystem_export_performed",
                "network_access_performed",
                "fhir_r4_conformance_validated",
                "clinical_use_authorized",
                "release_authorized",
            )
        )
    ):
        raise SyntheticFileBatchFilterError("fictional_file_filtered_contract_refused")
    visible_total = 0
    hidden_total = 0
    groups: list[dict[str, object]] = []
    for index, (saved, original_group, reported) in enumerate(
        zip(committed, original["imports"], filtered["imports"], strict=True), 1
    ):
        if (
            type(saved) is not dict
            or type(original_group) is not dict
            or type(reported) is not dict
            or set(reported) != _PER_IMPORT_KEYS
            or reported.get("import_ordinal") != index
            or reported.get("audit_sequence") != original_group.get("audit_sequence")
            or reported.get("source_content_sha256") != saved.get("source_content_sha256")
            or reported.get("source_content_sha256") != original_group.get("source_content_sha256")
            or reported.get("import_audit_event_digest") != saved.get("import_audit_event_digest")
            or reported.get("import_audit_event_digest")
            != original_group.get("import_audit_event_digest")
            or reported.get("patient_count_within_import") != 1
            or reported.get("patient_selection_mode") != "single_unique_patient"
            or type(original_group.get("event_count")) is not int
            or reported.get("source_event_count") != original_group["event_count"]
            or type(original_group.get("events")) is not list
            or len(original_group["events"]) != original_group["event_count"]
            or type(reported.get("visible_event_count")) is not int
            or type(reported.get("hidden_event_count")) is not int
            or type(reported.get("events")) is not list
        ):
            raise SyntheticFileBatchFilterError("fictional_file_filtered_source_refused")
        expected: list[dict[str, object]] = []
        for event_index, raw_event in enumerate(original_group["events"], 1):
            if (
                type(raw_event) is not dict
                or set(raw_event) != _EVENT_KEYS
                or type(raw_event.get("ordinal")) is not int
                or raw_event["ordinal"] != event_index
                or raw_event.get("resource_type") not in ("Encounter", "Observation")
                or type(raw_event.get("date_available")) is not bool
                or (raw_event.get("day_utc") is None) != (not raw_event["date_available"])
            ):
                raise SyntheticFileBatchFilterError("fictional_file_filtered_event_refused")
            day = raw_event["day_utc"]
            if day is not None:
                from medscale.fhirkit.workspace_multi_timeline import _checked_day

                try:
                    if _checked_day(day) != day:
                        raise SyntheticFileBatchFilterError("fictional_file_filtered_event_refused")
                except Exception as exc:
                    raise SyntheticFileBatchFilterError(
                        "fictional_file_filtered_event_refused"
                    ) from exc
            matches_day = (from_day_utc is None and through_day_utc is None) or (
                day is not None
                and (from_day_utc is None or day >= from_day_utc)
                and (through_day_utc is None or day <= through_day_utc)
            )
            if matches_day and (
                resource_type is None or raw_event["resource_type"] == resource_type
            ):
                expected.append(
                    {
                        "ordinal": event_index,
                        "resource_type": raw_event["resource_type"],
                        "day_utc": day,
                        "date_available": raw_event["date_available"],
                    }
                )
        hidden = original_group["event_count"] - len(expected)
        if (
            reported["events"] != expected
            or reported["visible_event_count"] != len(expected)
            or reported["hidden_event_count"] != hidden
        ):
            raise SyntheticFileBatchFilterError("fictional_file_filtered_reconciliation_refused")
        visible_total += len(expected)
        hidden_total += hidden
        groups.append(
            {
                "import_ordinal": index,
                "source_content_sha256": saved["source_content_sha256"],
                "import_audit_event_digest": saved["import_audit_event_digest"],
                "source_event_count": original_group["event_count"],
                "visible_event_count": len(expected),
                "hidden_event_count": hidden,
                "events": expected,
            }
        )
    if (
        visible_total + hidden_total != original["total_event_count"]
        or filtered["visible_total_event_count"] != visible_total
        or filtered["hidden_total_event_count"] != hidden_total
    ):
        raise SyntheticFileBatchFilterError("fictional_file_filtered_totals_refused")
    return {
        "schema": "medorigin-core-caller-file-filtered-verified-review/v1",
        "status": "FICTIONAL_SOURCE_VERIFIED_FILTERED_REVIEW",
        "from_day_utc": from_day_utc,
        "through_day_utc": through_day_utc,
        "resource_type_filter": resource_type,
        "source_total_event_count": original["total_event_count"],
        "visible_total_event_count": visible_total,
        "hidden_total_event_count": hidden_total,
        "imports": groups,
        "cross_import_patient_identity_join_performed": False,
        "patient_identity_included": False,
        "resource_payload_included": False,
        "clinical_use_authorized": False,
        "fhir_r4_conformance_validated": False,
    }
