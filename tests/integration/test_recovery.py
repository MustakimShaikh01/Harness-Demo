from decimal import Decimal
from pathlib import Path

import pytest

from banking_agent.harness.approval_manager import ApprovalManager
from banking_agent.harness.authorization import AuthorizationEngine
from banking_agent.harness.idempotency import IdempotencyManager
from banking_agent.harness.policy_engine import PolicyEngine
from banking_agent.services.transfer_service import TransferService
from banking_agent.storage.json_store import JsonStore
from banking_agent.storage.recovery import recover_pending_operations
from banking_agent.storage.repositories.approval_repository import ApprovalRepository


def test_prepared_transfer_is_redone_exactly_once_after_partial_write(tmp_path, monkeypatch):
    store = JsonStore(tmp_path)
    store.write("accounts.json", [
        {"account_id": "acct_source", "customer_id": "cust_demo_001", "balance": "1000.00", "status": "active"},
        {"account_id": "acct_target", "customer_id": "cust_demo_002", "balance": "50.00", "status": "active"},
    ])
    store.write("beneficiaries.json", [
        {"beneficiary_id": "ben_target", "customer_id": "cust_demo_001", "account_id": "acct_target"},
    ])
    store.write("transactions.json", [])
    store.write("approvals.json", [])
    store.write("idempotency.json", [])
    store.write("transfer_journal.json", [])
    store.write("bills.json", [])
    store.write("bill_payment_journal.json", [])

    approvals = ApprovalManager(ApprovalRepository(store), 300)
    service = TransferService(
        store,
        PolicyEngine(Path("banking_agent/config/policies.yaml")),
        AuthorizationEngine("cust_demo_001"),
        approvals,
        IdempotencyManager(store),
    )
    request = service.request("acct_source", "ben_target", Decimal("100.00"), "recover-me")
    original_write = store.write
    fail_once = True

    def interrupted_write(name, data):
        nonlocal fail_once
        if name == "transactions.json" and fail_once:
            fail_once = False
            raise OSError("simulated interruption after account balance write")
        original_write(name, data)

    monkeypatch.setattr(store, "write", interrupted_write)
    with pytest.raises(OSError, match="simulated interruption"):
        service.execute(request["approval_id"], "recover-me", "acct_source", "ben_target", Decimal("100.00"))

    monkeypatch.setattr(store, "write", original_write)
    result = recover_pending_operations(store)

    assert result == [{"operation": "transfer", "request_id": "recover-me", "status": "recovered"}]
    assert store.read("accounts.json")[0]["balance"] == "900.00"
    assert store.read("accounts.json")[1]["balance"] == "150.00"
    assert len(store.read("transactions.json")) == 2
    assert store.read("idempotency.json")[0]["status"] == "completed"
    assert store.read("transfer_journal.json")[0]["status"] == "committed"

    assert recover_pending_operations(store) == []
    assert len(store.read("transactions.json")) == 2


def test_prepared_bill_payment_is_redone_from_wal_snapshot(tmp_path):
    store = JsonStore(tmp_path)
    accounts = [{"account_id": "acct_source", "customer_id": "cust_demo_001", "balance": "900.00", "status": "active"}]
    transactions = [{"transaction_id": "tx_bill", "account_id": "acct_source", "amount": "100.00", "type": "debit"}]
    bills = [{"bill_id": "bill-1", "customer_id": "cust_demo_001", "account_id": "acct_source", "status": "paid"}]
    store.write("accounts.json", [{"account_id": "acct_source", "customer_id": "cust_demo_001", "balance": "1000.00", "status": "active"}])
    store.write("transactions.json", [])
    store.write("bills.json", [{"bill_id": "bill-1", "customer_id": "cust_demo_001", "account_id": "acct_source", "status": "pending"}])
    store.write("idempotency.json", [{"request_id": "bill-1", "operation": "bill_payment", "status": "reserved"}])
    store.write("transfer_journal.json", [])
    store.write("bill_payment_journal.json", [])

    approval_manager = ApprovalManager(ApprovalRepository(store), 300)
    details = {
        "type": "bill_payment", "bill_id": "bill-1", "account_id": "acct_source",
        "amount": "100.00", "currency": "INR", "biller": "Demo Power",
    }
    approval = approval_manager.create("approval-bill", "bill-1", details)
    approval_manager.approve(approval["approval_id"], details)
    store.write("bill_payment_journal.json", [{
        "transaction_id": "tx_bill",
        "bill_id": "bill-1",
        "approval_id": "approval-bill",
        "status": "prepared",
        "accounts_after": accounts,
        "transactions_after": transactions,
        "bills_after": bills,
    }])

    result = recover_pending_operations(store)

    assert result == [{"operation": "bill_payment", "request_id": "bill-1", "status": "recovered"}]
    assert store.read("accounts.json")[0]["balance"] == "900.00"
    assert store.read("bills.json")[0]["status"] == "paid"
    assert store.read("transactions.json") == transactions
    assert store.read("idempotency.json")[0]["status"] == "completed"
    assert store.read("approvals.json")[0]["status"] == "consumed"


def test_recovery_refuses_unapproved_journal_without_mutating_data(tmp_path):
    store = JsonStore(tmp_path)
    original_accounts = [{"account_id": "acct_source", "balance": "1000.00"}]
    store.write("accounts.json", original_accounts)
    store.write("transactions.json", [])
    store.write("bills.json", [])
    store.write("idempotency.json", [{"request_id": "req-1", "status": "reserved"}])
    store.write("approvals.json", [{"approval_id": "approval-1", "status": "pending"}])
    store.write("transfer_journal.json", [{
        "request_id": "req-1",
        "transaction_id": "tx-1",
        "approval_id": "approval-1",
        "status": "prepared",
        "accounts_after": [{"account_id": "acct_source", "balance": "0.00"}],
        "transactions_after": [{"transaction_id": "tx-1"}],
    }])
    store.write("bill_payment_journal.json", [])

    with pytest.raises(RuntimeError, match="not approved"):
        recover_pending_operations(store)

    assert store.read("accounts.json") == original_accounts
