"""Atomic encrypted, source-attested, synthetic-only R4 structural receipt.

This Workspace facade deliberately doesn't use Core private FHIR internals.
Only Core-prepared, fully redacted OperationOutcome issues are admissible,
and the full encrypted original source Bundle is reverified before commit.
Never a clinical validator, patient workflow, or production key-provider.
"""

from __future__ import annotations

import hashlib
import json

from medscale_workspace import fhir_r4 as fhir
from medscale_workspace.audit import (
    AuditEventType,
    AuditObjectRef,
    AuditTrail,
    prepare_next_event,
)
from medscale_workspace.binding import ObjectBinding
from medscale_workspace.fhir_readback import read_synthetic_fhir_bundle_in_memory
from medscale_workspace.identity import WorkspaceObjectType, synthetic_identity
from medscale_workspace.keyprovider import InMemoryTestKeyProvider
from medscale_workspace.provenance import (
    ProducerIdentity,
    ProducerKind,
    ReviewState,
    SourceKind,
    SourceRef,
    content_digest_of,
    describe_revision,
    provenance_binding_for,
    read_provenance,
)
from medscale_workspace.storage import ObjectWrite, WorkspaceStore


def _is_lower_sha256(value: object) -> bool:
    """Match exactly 64 ASCII lowercase hexadecimal characters, without regex imports."""
    return (
        isinstance(value, str)
        and len(value) == 64
        and all("0" <= char <= "9" or "a" <= char <= "f" for char in value)
    )


_ALLOWED_KEYWORDS = frozenset(
    [
        "additionalItems",
        "additionalProperties",
        "allOf",
        "anyOf",
        "const",
        "contains",
        "dependencies",
        "enum",
        "exclusiveMaximum",
        "exclusiveMinimum",
        "format",
        "items",
        "maxItems",
        "maxLength",
        "maxProperties",
        "maximum",
        "minItems",
        "minLength",
        "minProperties",
        "minimum",
        "multipleOf",
        "not",
        "oneOf",
        "pattern",
        "patternProperties",
        "properties",
        "propertyNames",
        "required",
        "type",
        "uniqueItems",
        "$ref",
    ]
)
_WARN = (
    "Structural-only JSON Schema result; not FHIR R4 conformance. "
    "Profiles, terminology, invariants, cross-references and clinical "
    "safety remain unverified."
)
_TRUNC = "Further structural errors were omitted after the fixed limit."
_PREFIX = "FHIR R4 JSON Schema structural keyword: "
_MAX_OBJECTS = 128
_MAX_ENVELOPES = 8 * 1024 * 1024


class SyntheticStructuralReceiptError(ValueError):
    """Fixed redacted failure reason; never echo source text, PHI or paths."""


def _admit_outcome(value: object, structural_status: str) -> bytes:
    """Admit only the finite, fully static Core structural Outcome vocabulary."""
    if not isinstance(value, dict) or set(value) != {"resourceType", "issue"}:
        raise SyntheticStructuralReceiptError("structural_outcome_shape_refused")
    if value["resourceType"] != "OperationOutcome":
        raise SyntheticStructuralReceiptError("structural_outcome_shape_refused")
    issues = value["issue"]
    if not isinstance(issues, list) or not 1 <= len(issues) <= 14:
        raise SyntheticStructuralReceiptError("structural_outcome_issue_count_refused")
    if structural_status not in ("invalid", "not_validated"):
        raise SyntheticStructuralReceiptError("structural_outcome_status_refused")
    errors = 0
    for pos, issue in enumerate(issues):
        if not isinstance(issue, dict) or set(issue) != {"severity", "code", "details"}:
            raise SyntheticStructuralReceiptError("structural_outcome_issue_shape_refused")
        details = issue["details"]
        if not isinstance(details, dict) or set(details) != {"text"}:
            raise SyntheticStructuralReceiptError("structural_outcome_details_refused")
        message = details["text"]
        if not isinstance(message, str):
            raise SyntheticStructuralReceiptError("structural_outcome_message_refused")
        if pos == len(issues) - 1:
            if (
                issue["severity"] != "warning"
                or issue["code"] != "informational"
                or message != _WARN
            ):
                raise SyntheticStructuralReceiptError("structural_outcome_warning_required")
            continue
        if issue["severity"] != "error" or issue["code"] != "structure":
            raise SyntheticStructuralReceiptError("structural_outcome_error_shape_refused")
        if message == _TRUNC:
            if pos != 12 or len(issues) != 14:
                raise SyntheticStructuralReceiptError("structural_outcome_truncation_refused")
        elif not message.startswith(_PREFIX) or message[len(_PREFIX) :] not in _ALLOWED_KEYWORDS:
            raise SyntheticStructuralReceiptError("structural_outcome_diagnostic_refused")
        errors += 1
    if (structural_status == "invalid") != bool(errors):
        raise SyntheticStructuralReceiptError("structural_outcome_status_mismatch")
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


def _admit_store(
    store: object, provider: object, source_sha: str, import_sha: str, head_sha: str
) -> WorkspaceStore:
    if not isinstance(store, WorkspaceStore):
        raise SyntheticStructuralReceiptError("workspace_store_required")
    if type(provider) is not InMemoryTestKeyProvider or store._key_provider is not provider:
        raise SyntheticStructuralReceiptError("in_memory_test_key_required")
    if not all(
        isinstance(v, str) and _is_lower_sha256(v) for v in (source_sha, import_sha, head_sha)
    ):
        raise SyntheticStructuralReceiptError("source_or_audit_anchor_refused")
    if store.object_count() > _MAX_OBJECTS or store.stored_envelope_bytes() > _MAX_ENVELOPES:
        raise SyntheticStructuralReceiptError("workspace_test_receipt_store_too_large")
    return store


def _binding(store: WorkspaceStore, source_sha: str, import_sha: str) -> ObjectBinding:
    identity = synthetic_identity(
        store.workspace_id,
        WorkspaceObjectType.FHIR_STRUCTURAL_OUTCOME,
        source_sha + ":" + import_sha,
    )
    return ObjectBinding(
        workspace_id=store.workspace_id,
        object_id=identity.object_id,
        object_type=WorkspaceObjectType.FHIR_STRUCTURAL_OUTCOME,
        object_revision="1",
    )


def commit_verified_synthetic_structural_outcome(
    *,
    store: object,
    test_key_provider: object,
    source_content_sha256: str,
    import_audit_event_digest: str,
    expected_current_audit_head_digest: str,
    outcome: object,
    structural_status: str,
    actor_id: str,
    occurred_at: str,
    synthetic_only: bool = False,
    allow_encrypted_receipt_write: bool = False,
) -> dict[str, object]:
    """Encrypted immutable Outcome + source provenance + audit, ONE transaction.

    A historical import must be reverified under a separately retained
    current head first; the new audit append then anchors the receipt.
    A second write to the same source+import is refused, never overwritten.
    """
    if synthetic_only is not True:
        raise SyntheticStructuralReceiptError("explicit_synthetic_attestation_required")
    if allow_encrypted_receipt_write is not True:
        raise SyntheticStructuralReceiptError("explicit_encrypted_receipt_write_required")
    store = _admit_store(
        store,
        test_key_provider,
        source_content_sha256,
        import_audit_event_digest,
        expected_current_audit_head_digest,
    )
    encoded_outcome = _admit_outcome(outcome, structural_status)
    try:
        actor = fhir._admit_identifier(actor_id, "actor id")
        moment = fhir._admit_occurred_at(occurred_at)
        read_synthetic_fhir_bundle_in_memory(
            store=store,
            test_key_provider=test_key_provider,
            source_content_sha256=source_content_sha256,
            expected_audit_head_digest=import_audit_event_digest,
            expected_current_audit_head_digest=expected_current_audit_head_digest,
            actor_id=actor,
            synthetic_only=True,
            allow_in_memory_readback=True,
        )
        value = {
            "schema": "medorigin-synthetic-r4-structural-outcome/v1",
            "source_content_sha256": source_content_sha256,
            "import_audit_event_digest": import_audit_event_digest,
            "structural_status": structural_status,
            "outcome": json.loads(encoded_outcome),
            "fhir_conformance_validated": False,
            "clinical_use_authorized": False,
            "release_authorized": False,
        }
        blob = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        ).encode("ascii")
        binding = _binding(store, source_content_sha256, import_audit_event_digest)
        provenance = describe_revision(
            binding=binding,
            payload=blob,
            producer=ProducerIdentity(
                kind=ProducerKind.IMPORT,
                identifier=actor,
                version="r4-structural-receipt-v1",
            ),
            source_refs=(
                SourceRef(
                    kind=SourceKind.IMPORT,
                    source_id=source_content_sha256,
                    source_revision=import_audit_event_digest,
                ),
            ),
            review_state=ReviewState.IMPORTED,
        )
        event = prepare_next_event(
            AuditTrail(store),
            event_type=AuditEventType.OBJECT_CREATE,
            actor_id=actor,
            occurred_at=moment,
            object_refs=(
                AuditObjectRef(
                    object_id=binding.object_id,
                    object_type=binding.object_type,
                    object_revision=binding.object_revision,
                    content_digest=content_digest_of(blob),
                ),
            ),
            metadata=(
                ("action", "synthetic_structural_outcome_saved"),
                ("source_sha256", source_content_sha256),
                ("structural_status", structural_status),
            ),
        )
        store.put_objects_atomic(
            (
                ObjectWrite(binding=binding, payload=blob),
                ObjectWrite(
                    binding=provenance_binding_for(binding),
                    payload=provenance.canonical_bytes(),
                ),
                ObjectWrite(binding=event.binding(), payload=event.canonical_bytes()),
            )
        )
    except SyntheticStructuralReceiptError:
        raise
    except Exception as exc:
        raise SyntheticStructuralReceiptError(
            "encrypted_structural_receipt_commit_refused"
        ) from exc
    return {
        "schema": "medorigin-encrypted-structural-receipt-write/v1",
        "status": "synthetic_structural_outcome_encrypted",
        "source_content_sha256": source_content_sha256,
        "import_audit_event_digest": import_audit_event_digest,
        "receipt_sha256": hashlib.sha256(blob).hexdigest(),
        "audit_head_digest": event.event_digest,
        "structural_status": structural_status,
        "objects_written": 3,
        "payload_included": False,
        "fhir_conformance_validated": False,
        "clinical_use_authorized": False,
        "release_authorized": False,
    }


def read_verified_synthetic_structural_outcome(
    *,
    store: object,
    test_key_provider: object,
    source_content_sha256: str,
    import_audit_event_digest: str,
    expected_current_audit_head_digest: str,
    expected_receipt_sha256: str,
    actor_id: str,
    synthetic_only: bool = False,
    allow_in_memory_readback: bool = False,
) -> dict[str, object]:
    """Re-read the source-linked encrypted receipt; never a plaintext export."""
    if synthetic_only is not True or allow_in_memory_readback is not True:
        raise SyntheticStructuralReceiptError("explicit_synthetic_receipt_read_required")
    store = _admit_store(
        store,
        test_key_provider,
        source_content_sha256,
        import_audit_event_digest,
        expected_current_audit_head_digest,
    )
    if not isinstance(expected_receipt_sha256, str) or not _is_lower_sha256(
        expected_receipt_sha256
    ):
        raise SyntheticStructuralReceiptError("receipt_digest_refused")
    try:
        actor = fhir._admit_identifier(actor_id, "actor id")
        read_synthetic_fhir_bundle_in_memory(
            store=store,
            test_key_provider=test_key_provider,
            source_content_sha256=source_content_sha256,
            expected_audit_head_digest=import_audit_event_digest,
            expected_current_audit_head_digest=expected_current_audit_head_digest,
            actor_id=actor,
            synthetic_only=True,
            allow_in_memory_readback=True,
        )
        binding = _binding(store, source_content_sha256, import_audit_event_digest)
        blob = store.get_object(binding)
        if hashlib.sha256(blob).hexdigest() != expected_receipt_sha256:
            raise SyntheticStructuralReceiptError("encrypted_receipt_sha_mismatch")
        document = json.loads(blob.decode("ascii"))
        if (
            not isinstance(document, dict)
            or set(document)
            != {
                "schema",
                "source_content_sha256",
                "import_audit_event_digest",
                "structural_status",
                "outcome",
                "fhir_conformance_validated",
                "clinical_use_authorized",
                "release_authorized",
            }
            or document["schema"] != "medorigin-synthetic-r4-structural-outcome/v1"
            or document["source_content_sha256"] != source_content_sha256
            or document["import_audit_event_digest"] != import_audit_event_digest
            or any(
                document[k] is not False
                for k in (
                    "fhir_conformance_validated",
                    "clinical_use_authorized",
                    "release_authorized",
                )
            )
            or _admit_outcome(document["outcome"], document["structural_status"])
            != json.dumps(
                document["outcome"], sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("ascii")
            or json.dumps(
                document, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            ).encode("ascii")
            != blob
        ):
            raise SyntheticStructuralReceiptError("encrypted_receipt_contract_refused")
        provenance_binding = provenance_binding_for(binding)
        provenance_bytes = store.get_object(provenance_binding)
        provenance = read_provenance(store, binding)
        provenance.verify_payload(blob)
        if (
            provenance.canonical_bytes() != provenance_bytes
            or provenance.producer.version != "r4-structural-receipt-v1"
            or provenance.binding != binding
            or provenance.review_state is not ReviewState.IMPORTED
            or provenance.producer.kind is not ProducerKind.IMPORT
            or provenance.producer.identifier != actor
            or len(provenance.source_refs) != 1
            or provenance.source_refs[0].kind is not SourceKind.IMPORT
            or provenance.source_refs[0].source_id != source_content_sha256
            or provenance.source_refs[0].source_revision != import_audit_event_digest
        ):
            raise SyntheticStructuralReceiptError("encrypted_receipt_provenance_refused")
        events = AuditTrail(store).events()
        if not events or events[-1].event_digest != expected_current_audit_head_digest:
            raise SyntheticStructuralReceiptError("encrypted_receipt_audit_anchor_mismatch")
        matching = tuple(
            item
            for item in events
            if item.event_type is AuditEventType.OBJECT_CREATE
            and item.actor_id == actor
            and item.metadata
            == (
                ("action", "synthetic_structural_outcome_saved"),
                ("source_sha256", source_content_sha256),
                ("structural_status", document["structural_status"]),
            )
        )
        if len(matching) != 1 or len(matching[0].object_refs) != 1:
            raise SyntheticStructuralReceiptError("encrypted_receipt_audit_event_refused")
        ref = matching[0].object_refs[0]
        if (
            ref.object_id != binding.object_id
            or ref.object_type != binding.object_type
            or ref.object_revision != binding.object_revision
            or ref.content_digest != content_digest_of(blob)
        ):
            raise SyntheticStructuralReceiptError("encrypted_receipt_audit_object_refused")
        # A later event affecting this receipt or its provenance is not a
        # read-only continuation. Accept only independently anchored benign
        # or disjoint events, never supersede this immutable source proof.
        for later in events:
            if later.sequence <= matching[0].sequence:
                continue
            if later.event_type not in (
                AuditEventType.WORKSPACE_OPEN,
                AuditEventType.WORKSPACE_CLOSE,
                AuditEventType.LOGIN,
                AuditEventType.OBJECT_CREATE,
            ):
                raise SyntheticStructuralReceiptError("post_receipt_audit_event_refused")
            if any(
                item.object_id in (binding.object_id, provenance_binding.object_id)
                for item in later.object_refs
            ):
                raise SyntheticStructuralReceiptError("post_receipt_content_audit_refused")
    except SyntheticStructuralReceiptError:
        raise
    except Exception as exc:
        raise SyntheticStructuralReceiptError("encrypted_receipt_read_integrity_refused") from exc
    return {
        "schema": "medorigin-encrypted-structural-receipt-read/v1",
        "status": "synthetic_structural_outcome_recovered",
        "source_content_sha256": source_content_sha256,
        "structural_status": document["structural_status"],
        "outcome": document["outcome"],
        "receipt_sha256": expected_receipt_sha256,
        "audit_head_digest": expected_current_audit_head_digest,
        "fhir_conformance_validated": False,
        "clinical_use_authorized": False,
        "release_authorized": False,
    }
