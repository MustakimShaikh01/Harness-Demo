from pathlib import Path

from banking_agent.harness.approval_manager import ApprovalManager
from banking_agent.harness.authorization import AuthorizationEngine
from banking_agent.harness.observability import AuditLogger
from banking_agent.services.bill_service import BillService
from banking_agent.storage.json_store import JsonStore
from banking_agent.storage.repositories.account_repository import AccountRepository
from banking_agent.storage.repositories.approval_repository import ApprovalRepository
from banking_agent.harness.idempotency import IdempotencyManager
import banking_agent.tools.bill_tools as bill_tools


def _configure_bill_tools(monkeypatch, tmp_path):
    store = JsonStore(Path(tmp_path))
    store.write("accounts.json", [
        {"account_id": "acct_owned", "customer_id": "cust_demo_001", "balance": "5000.00", "status": "active"},
        {"account_id": "acct_other", "customer_id": "cust_demo_002", "balance": "9999.00", "status": "active"},
    ])
    store.write("bills.json", [
        {"bill_id": "bill_owned", "customer_id": "cust_demo_001", "account_id": "acct_owned",
         "biller": "Demo Power", "amount": "850.00", "currency": "INR", "status": "pending"},
        {"bill_id": "bill_other", "customer_id": "cust_demo_002", "account_id": "acct_other",
         "biller": "Other Power", "amount": "100.00", "currency": "INR", "status": "pending"},
    ])
    store.write("transactions.json", [])
    store.write("approvals.json", [])
    store.write("audit_logs.json", [])
    store.write("bill_payment_journal.json", [])
    auth = AuthorizationEngine("cust_demo_001")
    monkeypatch.setattr(bill_tools, "_store", store)
    monkeypatch.setattr(bill_tools, "_auth", auth)
    monkeypatch.setattr(bill_tools, "_service", BillService(store, auth))
    monkeypatch.setattr(bill_tools, "_approval", ApprovalManager(ApprovalRepository(store), 300))
    monkeypatch.setattr(bill_tools, "_accounts", AccountRepository(store))
    monkeypatch.setattr(bill_tools, "_idempotency", IdempotencyManager(store))
    monkeypatch.setattr(bill_tools, "_audit", AuditLogger(store))
    return store


def test_bill_payment_uses_bill_account_and_records_transaction(monkeypatch, tmp_path):
    store = _configure_bill_tools(monkeypatch, tmp_path)
    request = bill_tools.request_bill_payment("bill_owned")
    result = bill_tools.execute_confirmed_bill_payment(request["approval_id"], "bill_owned")

    accounts = store.read("accounts.json")
    assert result["success"] is True
    assert accounts[0]["balance"] == "4150.00"
    assert accounts[1]["balance"] == "9999.00"
    assert store.read("bills.json")[0]["status"] == "paid"
    assert store.read("transactions.json")[0]["bill_id"] == "bill_owned"


def test_bill_payment_replay_is_rejected(monkeypatch, tmp_path):
    _configure_bill_tools(monkeypatch, tmp_path)
    request = bill_tools.request_bill_payment("bill_owned")
    bill_tools.execute_confirmed_bill_payment(request["approval_id"], "bill_owned")

    result = bill_tools.execute_confirmed_bill_payment(request["approval_id"], "bill_owned")

    assert result["success"] is False
    assert result["error"]["category"] == "BILL_NOT_PENDING"


def test_foreign_bill_cannot_be_requested(monkeypatch, tmp_path):
    _configure_bill_tools(monkeypatch, tmp_path)

    result = bill_tools.request_bill_payment("bill_other")

    assert result["success"] is False
    assert result["error"]["category"] == "PERMISSION_DENIED"
