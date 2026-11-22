import copy

import pytest

from banking_agent.harness.audit_integrity import (
    AuditIntegrityError,
    GENESIS_HASH,
    append_integrity_fields,
    verify_document,
)
from banking_agent.harness.observability import AuditLogger
from banking_agent.storage.json_store import JsonStore


def test_audit_logger_writes_a_verifiable_hash_chain(tmp_path):
    store = JsonStore(tmp_path)
    audit = AuditLogger(store)

    audit.record({"operation": "balance_lookup", "account_id": "acct_demo_001"})
    audit.record({"operation": "transfer", "result": "completed"})

    events = store.read("audit_logs.json")
    verified = verify_document(events)
    assert verified["valid"] is True
    assert verified["event_count"] == 2
    assert events[0]["previous_hash"] == GENESIS_HASH
    assert events[1]["previous_hash"] == events[0]["event_hash"]


def test_verification_rejects_modified_event_content():
    events = [
        append_integrity_fields({"operation": "balance_lookup"}, GENESIS_HASH)
    ]
    events[0]["operation"] = "tampered"

    with pytest.raises(AuditIntegrityError, match="invalid event_hash"):
        verify_document(events)


def test_verification_rejects_reordered_events():
    first = append_integrity_fields({"operation": "first"}, GENESIS_HASH)
    second = append_integrity_fields(
        {"operation": "second"}, first["event_hash"]
    )

    with pytest.raises(AuditIntegrityError, match="invalid previous_hash"):
        verify_document([second, first])


@pytest.mark.parametrize("document", [{"events": []}, [None], ["not an object"]])
def test_verification_rejects_malformed_documents(document):
    with pytest.raises(AuditIntegrityError):
        verify_document(document)
