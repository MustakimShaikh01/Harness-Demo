import banking_agent.tools.account_tools as account_tools
import banking_agent.tools.transaction_tools as transaction_tools
from banking_agent.harness.authorization import AuthorizationEngine
from banking_agent.services.account_service import AccountService
from banking_agent.services.transaction_service import TransactionService
from banking_agent.storage.json_store import JsonStore
from banking_agent.storage.repositories.account_repository import AccountRepository
from banking_agent.storage.repositories.transaction_repository import TransactionRepository


def _configure_read_tools(monkeypatch, tmp_path):
    store = JsonStore(tmp_path)
    store.write("accounts.json", [
        {"account_id": "acct_owned", "customer_id": "cust_demo_001", "balance": "1234.50",
         "currency": "INR", "status": "active", "account_type": "savings"},
        {"account_id": "acct_foreign", "customer_id": "cust_other", "balance": "9999.00",
         "currency": "INR", "status": "active", "account_type": "checking"},
    ])
    store.write("transactions.json", [
        {"transaction_id": "tx_debit", "account_id": "acct_owned", "amount": "10.00",
         "type": "debit", "date": "2026-11-20T10:00:00+00:00"},
        {"transaction_id": "tx_credit", "account_id": "acct_owned", "amount": "5.00",
         "type": "credit", "date": "2026-11-21T10:00:00+00:00"},
    ])
    auth = AuthorizationEngine("cust_demo_001")
    monkeypatch.setattr(account_tools, "_service", AccountService(AccountRepository(store), auth))
    monkeypatch.setattr(transaction_tools, "_service", TransactionService(
        TransactionRepository(store), AccountRepository(store), auth
    ))
    return store


def test_account_tools_return_account_facts_without_model_inference(monkeypatch, tmp_path):
    _configure_read_tools(monkeypatch, tmp_path)

    balance = account_tools.get_balance("acct_owned")
    summary = account_tools.get_account_summary("acct_owned")

    assert balance == {
        "success": True, "account_id": "acct_owned",
        "available_balance": "1234.50", "currency": "INR",
    }
    assert summary["account_type"] == "savings"
    assert summary["status"] == "active"


def test_account_and_transaction_tools_reject_unknown_and_foreign_accounts(monkeypatch, tmp_path):
    _configure_read_tools(monkeypatch, tmp_path)

    unknown = account_tools.get_account("acct_unknown")
    foreign_balance = account_tools.get_balance("acct_foreign")
    foreign_history = transaction_tools.get_transaction_history("acct_foreign")

    assert unknown["error"]["category"] == "NOT_FOUND"
    assert foreign_balance["error"]["category"] == "PERMISSION_DENIED"
    assert foreign_history["error"]["category"] == "PERMISSION_DENIED"


def test_transaction_history_filters_by_date_and_type(monkeypatch, tmp_path):
    _configure_read_tools(monkeypatch, tmp_path)

    result = transaction_tools.get_transaction_history(
        "acct_owned", date="2026-11-20", transaction_type="debit"
    )

    assert [row["transaction_id"] for row in result["transactions"]] == ["tx_debit"]


def test_transaction_search_is_scoped_to_owned_account(monkeypatch, tmp_path):
    _configure_read_tools(monkeypatch, tmp_path)

    found = transaction_tools.search_transaction("acct_owned", "tx_credit")
    missing = transaction_tools.search_transaction("acct_owned", "tx_missing")

    assert found["transaction"]["transaction_id"] == "tx_credit"
    assert missing["error"]["category"] == "NOT_FOUND"
