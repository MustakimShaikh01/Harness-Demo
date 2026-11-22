import json
from pathlib import Path

import pytest

from banking_agent.harness.audit_integrity import (
    AuditIntegrityError,
    GENESIS_HASH,
    append_integrity_fields,
    verify_document,
)
from banking_agent.harness.observability import AuditLogger
from banking_agent.storage.json_store import JsonStore

FIXTURES = Path(__file__).parents[1] / "fixtures"


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


def test_shared_python_rust_fixture_verifies_and_matches_trusted_head():
    events = json.loads((FIXTURES / "audit_chain_valid.json").read_text(encoding="utf-8"))
    verified = verify_document(
        events,
        expected_head="ef64c56db877472454c6f6297b636e0a55bd1bcf02667017bf86c435a4008fde",
    )

    assert verified["event_count"] == 2
    assert verified["head_hash"] == "ef64c56db877472454c6f6297b636e0a55bd1bcf02667017bf86c435a4008fde"


def test_shared_tampered_fixture_is_rejected():
    events = json.loads(
        (FIXTURES / "audit_chain_tampered.json").read_text(encoding="utf-8")
    )

    with pytest.raises(AuditIntegrityError, match="invalid event_hash"):
        verify_document(events)


def test_trusted_checkpoint_detects_truncated_tail():
    events = json.loads((FIXTURES / "audit_chain_valid.json").read_text(encoding="utf-8"))

    with pytest.raises(AuditIntegrityError, match="trusted checkpoint"):
        verify_document(
            events[:1],
            expected_head="ef64c56db877472454c6f6297b636e0a55bd1bcf02667017bf86c435a4008fde",
        )


@pytest.mark.parametrize("value", [1.25, 2**53])
def test_hashing_rejects_numbers_without_stable_cross_language_representation(value):
    with pytest.raises(AuditIntegrityError, match="Floating-point|safe range"):
        append_integrity_fields({"amount": value}, GENESIS_HASH)
