import hashlib
import json
from typing import Any

GENESIS_HASH = "0" * 64


class AuditIntegrityError(ValueError):
    """Raised when an audit event has an invalid or broken hash link."""


def canonical_event_bytes(event: dict[str, Any]) -> bytes:
    event_without_hash = {key: value for key, value in event.items() if key != "event_hash"}
    return json.dumps(
        event_without_hash,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def event_hash(event: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_event_bytes(event)).hexdigest()


def append_integrity_fields(event: dict[str, Any], previous_hash: str) -> dict[str, Any]:
    if "previous_hash" in event or "event_hash" in event:
        raise AuditIntegrityError("New audit event already contains integrity fields")
    linked_event = {**event, "previous_hash": previous_hash}
    linked_event["event_hash"] = event_hash(linked_event)
    return linked_event


def verify_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    previous_hash = GENESIS_HASH
    for index, event in enumerate(events):
        if not isinstance(event, dict):
            raise AuditIntegrityError(f"Event {index} is not a JSON object")
        if event.get("previous_hash") != previous_hash:
            raise AuditIntegrityError(f"Event {index} has an invalid previous_hash")
        recorded_hash = event.get("event_hash")
        if not isinstance(recorded_hash, str) or recorded_hash != event_hash(event):
            raise AuditIntegrityError(f"Event {index} has an invalid event_hash")
        previous_hash = recorded_hash
    return {
        "valid": True,
        "event_count": len(events),
        "head_hash": previous_hash,
    }


def verify_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, list):
        raise AuditIntegrityError("Audit log root must be a JSON array")
    return verify_events(document)
