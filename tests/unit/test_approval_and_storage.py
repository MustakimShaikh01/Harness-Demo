import pytest

from banking_agent.harness.approval_manager import ApprovalManager
from banking_agent.harness.validation import ToolValidationError, positive_money
from banking_agent.harness.error_handler import error_contract
from banking_agent.storage.json_store import CorruptedJsonError, JsonStore
from banking_agent.storage.repositories.approval_repository import ApprovalRepository


def _approval_manager(tmp_path, ttl_seconds=300):
    store = JsonStore(tmp_path)
    store.write("approvals.json", [])
    return ApprovalManager(ApprovalRepository(store), ttl_seconds=ttl_seconds)


def test_approval_rejects_modified_details(tmp_path):
    manager = _approval_manager(tmp_path)
    details = {"type": "transfer", "amount": "500.00", "request_id": "request-1"}
    manager.create("approval-1", "request-1", details)

    with pytest.raises(ToolValidationError) as error:
        manager.approve("approval-1", {**details, "amount": "501.00"})

    assert error.value.code == "APPROVAL_MODIFIED"


def test_approval_rejects_replay(tmp_path):
    manager = _approval_manager(tmp_path)
    details = {"type": "transfer", "amount": "500.00", "request_id": "request-1"}
    manager.create("approval-1", "request-1", details)
    manager.approve("approval-1", details)

    with pytest.raises(ToolValidationError) as error:
        manager.approve("approval-1", details)

    assert error.value.code == "APPROVAL_REPLAY"


def test_approval_rejects_expired_request(tmp_path):
    manager = _approval_manager(tmp_path, ttl_seconds=-1)
    details = {"type": "transfer", "amount": "500.00", "request_id": "request-1"}
    manager.create("approval-1", "request-1", details)

    with pytest.raises(ToolValidationError) as error:
        manager.approve("approval-1", details)

    assert error.value.code == "APPROVAL_EXPIRED"


def test_json_store_reports_malformed_json(tmp_path):
    store = JsonStore(tmp_path)
    (tmp_path / "accounts.json").write_text("{broken", encoding="utf-8")

    with pytest.raises(CorruptedJsonError) as error:
        store.read("accounts.json")
    assert error_contract(error.value)["error"]["category"] == "CORRUPTED_JSON"


def test_money_validation_rejects_excess_precision():
    with pytest.raises(ToolValidationError) as error:
        positive_money("1.001")

    assert error.value.code == "INVALID_AMOUNT"


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_money_validation_rejects_non_finite_values(value):
    with pytest.raises(ToolValidationError) as error:
        positive_money(value)

    assert error.value.code == "INVALID_AMOUNT"
