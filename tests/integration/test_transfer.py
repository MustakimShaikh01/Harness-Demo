from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from banking_agent.harness.approval_manager import ApprovalManager
from banking_agent.harness.authorization import AuthorizationEngine
from banking_agent.harness.idempotency import IdempotencyManager
from banking_agent.harness.policy_engine import PolicyEngine
from banking_agent.harness.validation import ToolValidationError
from banking_agent.services.transfer_service import TransferService
from banking_agent.storage.json_store import JsonStore
from banking_agent.storage.repositories.approval_repository import ApprovalRepository


def build_service(tmp_path, balance="100000.00", status="active", customer_id="cust_demo_001"):
    store = JsonStore(Path(tmp_path))
    store.write("accounts.json", [
        {"account_id": "acct_demo_001", "customer_id": customer_id, "balance": balance,
         "status": status, "currency": "INR", "account_type": "savings"},
        {"account_id": "acct_demo_002", "customer_id": "cust_demo_002", "balance": "100.00",
         "status": "active", "currency": "INR", "account_type": "savings"},
    ])
    store.write("beneficiaries.json", [
        {"beneficiary_id": "ben_1", "customer_id": "cust_demo_001", "account_id": "acct_demo_002", "status": "active"},
    ])
    store.write("transactions.json", [])
    store.write("approvals.json", [])
    store.write("idempotency.json", [])
    store.write("transfer_journal.json", [])
    policy = PolicyEngine(Path("banking_agent/config/policies.yaml"))
    auth = AuthorizationEngine("cust_demo_001")
    approvals = ApprovalManager(ApprovalRepository(store), 300)
    idempotency = IdempotencyManager(store)
    return store, TransferService(store, policy, auth, approvals, idempotency)


def test_confirmed_transfer_updates_both_accounts_and_records_pair(tmp_path):
    store, service = build_service(tmp_path)
    request = service.request("acct_demo_001", "ben_1", Decimal("500.00"), "req-1")

    result = service.execute(
        request["approval_id"], "req-1", "acct_demo_001", "ben_1", Decimal("500.00")
    )

    accounts = store.read("accounts.json")
    transactions = store.read("transactions.json")
    assert result["success"] is True
    assert accounts[0]["balance"] == "99500.00"
    assert accounts[1]["balance"] == "600.00"
    assert len(transactions) == 2
    assert {row["type"] for row in transactions} == {"debit", "credit"}
    assert all(row["transaction_id"] == result["transaction_id"] for row in transactions)
    assert store.read("idempotency.json")[0]["status"] == "completed"


def test_duplicate_completed_request_is_rejected(tmp_path):
    _, service = build_service(tmp_path)
    request = service.request("acct_demo_001", "ben_1", Decimal("100"), "req-done")
    service.execute(request["approval_id"], "req-done", "acct_demo_001", "ben_1", Decimal("100"))

    with pytest.raises(ToolValidationError, match="already completed"):
        service.request("acct_demo_001", "ben_1", Decimal("100"), "req-done")


def test_repeated_pending_request_returns_same_approval(tmp_path):
    _, service = build_service(tmp_path)

    first = service.request("acct_demo_001", "ben_1", Decimal("100"), "req-pending")
    second = service.request("acct_demo_001", "ben_1", Decimal("100"), "req-pending")

    assert first["approval_id"] == second["approval_id"]


def test_transfer_request_creates_pending_approval_without_moving_money(tmp_path):
    store, service = build_service(tmp_path)

    result = service.request("acct_demo_001", "ben_1", Decimal("50"), "req-approval")

    assert result["status"] == "approval_required"
    assert store.read("accounts.json")[0]["balance"] == "100000.00"


@pytest.mark.parametrize(
    ("amount", "expected_reason"),
    [(Decimal("25001"), "ABOVE_MAXIMUM")],
)
def test_transfer_limit_denials_are_deterministic(tmp_path, amount, expected_reason):
    _, service = build_service(tmp_path)

    with pytest.raises(ToolValidationError, match=expected_reason):
        service.request("acct_demo_001", "ben_1", amount, "req-limit")


def test_daily_limit_is_enforced(tmp_path):
    store, service = build_service(tmp_path)
    store.write("transactions.json", [{
        "transaction_id": "tx-today",
        "from_account": "acct_demo_001",
        "amount": "49950.00",
        "date": datetime.now(timezone.utc).isoformat(),
    }])

    with pytest.raises(ToolValidationError, match="DAILY_LIMIT_EXCEEDED"):
        service.request("acct_demo_001", "ben_1", Decimal("100"), "req-daily")


def test_inactive_account_is_rejected(tmp_path):
    _, inactive_service = build_service(tmp_path, status="inactive")
    with pytest.raises(ToolValidationError, match="SOURCE_ACCOUNT_INACTIVE"):
        inactive_service.request("acct_demo_001", "ben_1", Decimal("50"), "req-inactive")


def test_insufficient_funds_are_rejected(tmp_path):
    _, low_balance_service = build_service(tmp_path, balance="50.00")
    with pytest.raises(ToolValidationError) as error:
        low_balance_service.request("acct_demo_001", "ben_1", Decimal("100"), "req-funds")
    assert error.value.code == "INSUFFICIENT_FUNDS"


def test_cross_customer_source_account_is_denied(tmp_path):
    _, service = build_service(tmp_path, customer_id="cust_demo_002")

    with pytest.raises(PermissionError):
        service.request("acct_demo_001", "ben_1", Decimal("50"), "req-owner")


def test_unknown_beneficiary_is_denied(tmp_path):
    _, service = build_service(tmp_path)

    with pytest.raises(PermissionError):
        service.request("acct_demo_001", "ben_unknown", Decimal("50"), "req-beneficiary")


def test_modified_approval_does_not_change_balances(tmp_path):
    store, service = build_service(tmp_path)
    request = service.request("acct_demo_001", "ben_1", Decimal("500"), "req-modified")

    with pytest.raises(ToolValidationError) as error:
        service.execute(request["approval_id"], "req-modified", "acct_demo_001", "ben_1", Decimal("501"))

    assert error.value.code == "APPROVAL_MODIFIED"
    assert store.read("accounts.json")[0]["balance"] == "100000.00"
