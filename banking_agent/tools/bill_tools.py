from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from ..config.settings import ACTIVE_CUSTOMER_ID, DATA_DIR
from ..harness.approval_manager import ApprovalManager
from ..harness.authorization import AuthorizationEngine
from ..harness.error_handler import error_contract
from ..harness.observability import AuditLogger
from ..harness.validation import ToolValidationError, account_id, positive_money
from ..harness.idempotency import IdempotencyManager
from ..harness.policy_engine import PolicyEngine
from ..services.bill_service import BillService
from ..storage.file_lock import file_lock
from ..storage.json_store import JsonStore
from ..storage.recovery import recover_pending_operations
from ..storage.repositories.account_repository import AccountRepository
from ..storage.repositories.approval_repository import ApprovalRepository

_store = JsonStore(DATA_DIR)
_auth = AuthorizationEngine(ACTIVE_CUSTOMER_ID)
_service = BillService(_store, _auth)
_policy = PolicyEngine(Path(__file__).resolve().parents[1] / "config" / "policies.yaml")
_approval = ApprovalManager(ApprovalRepository(_store), int(_policy.policies["approval"]["ttl_seconds"]))
_accounts = AccountRepository(_store)
_idempotency = IdempotencyManager(_store)
_audit = AuditLogger(_store)


def list_pending_bills() -> dict:
    """List pending bills owned by the active demo customer."""
    try:
        return {"success": True, "bills": [bill for bill in _service.list() if bill.get("status") == "pending"]}
    except Exception as exc:
        return error_contract(exc)


def get_bill_details(bill_id: str) -> dict:
    """Return one bill belonging to the active demo customer."""
    try:
        return {"success": True, "bill": _service.get(bill_id)}
    except Exception as exc:
        return error_contract(exc)


def request_bill_payment(bill_id: str) -> dict:
    """Create an approval request for exact pending bill details; does not pay it."""
    try:
        bill = _service.get(bill_id)
        if bill.get("status") != "pending":
            raise ToolValidationError("BILL_NOT_PENDING", "Bill is not pending")
        account_id(bill.get("account_id"))
        amount = positive_money(bill.get("amount"), bill.get("currency", "INR"))
        details = {
            "type": "bill_payment",
            "bill_id": bill_id,
            "account_id": bill["account_id"],
            "amount": format(amount, ".2f"),
            "currency": "INR",
            "biller": bill["biller"],
        }
        approval = _approval.create(str(uuid4()), bill_id, details)
        _audit.record({
            "request_id": bill_id,
            "tool": "request_bill_payment",
            "operation": "bill_payment",
            "approval_decision": "pending",
            "execution_result": "approval_required",
        })
        return {"success": True, "status": "approval_required", "approval_id": approval["approval_id"], "details": details}
    except Exception as exc:
        return error_contract(exc)


def execute_confirmed_bill_payment(approval_id: str, bill_id: str) -> dict:
    """Pay one pending bill after ADK UI confirmation and matching approval."""
    try:
        recover_pending_operations(_store)
        with file_lock(_store.data_dir / ".bankguard.lock"):
            bill = _service.get(bill_id)
            if bill.get("status") != "pending":
                raise ToolValidationError("BILL_NOT_PENDING", "Bill is not pending")

            payment_account_id = account_id(bill.get("account_id"))
            account = _accounts.get(payment_account_id)
            _auth.own_account(account)
            amount = positive_money(bill.get("amount"), bill.get("currency", "INR"))
            if account.get("status") != "active":
                raise ToolValidationError("ACCOUNT_INACTIVE", "Payment account is inactive")
            if Decimal(str(account["balance"])) < amount:
                raise ToolValidationError("INSUFFICIENT_FUNDS", "Available balance is insufficient")

            exact_details = {
                "type": "bill_payment",
                "bill_id": bill_id,
                "account_id": payment_account_id,
                "amount": format(amount, ".2f"),
                "currency": "INR",
                "biller": bill["biller"],
            }
            _approval.approve(approval_id, exact_details)

            accounts = _store.read("accounts.json", [])
            for row in accounts:
                if row["account_id"] == payment_account_id:
                    row["balance"] = format(Decimal(str(row["balance"])) - amount, ".2f")

            paid_at = datetime.now(timezone.utc).isoformat()
            transaction_id = str(uuid4())
            transactions = _store.read("transactions.json", [])
            transactions.append({
                "transaction_id": transaction_id,
                "account_id": payment_account_id,
                "amount": format(amount, ".2f"),
                "currency": "INR",
                "type": "debit",
                "status": "completed",
                "date": paid_at,
                "description": f"Simulated bill payment: {bill['biller']}",
                "bill_id": bill_id,
            })

            bills = _store.read("bills.json", [])
            for row in bills:
                if row["bill_id"] == bill_id:
                    row["status"] = "paid"
                    row["paid_at"] = paid_at

            journal = _store.read("bill_payment_journal.json", [])
            _idempotency.reserve(bill_id, "bill_payment")
            idem_row = _idempotency.get(bill_id)
            if idem_row and idem_row.get("status") == "completed":
                raise ToolValidationError("DUPLICATE_REQUEST", "This bill payment was already completed")
            journal.append({
                "transaction_id": transaction_id,
                "bill_id": bill_id,
                "approval_id": approval_id,
                "status": "prepared",
                "accounts_after": accounts,
                "transactions_after": transactions,
                "bills_after": bills,
                "timestamp": paid_at,
            })
            _store.write("bill_payment_journal.json", journal)
            _store.write("accounts.json", accounts)
            _store.write("transactions.json", transactions)
            _store.write("bills.json", bills)
            _idempotency.complete(bill_id, {"transaction_id": transaction_id})
            _approval.consume(approval_id)
            journal[-1]["status"] = "committed"
            _store.write("bill_payment_journal.json", journal)

        result = {"success": True, "status": "completed", "bill_id": bill_id, "transaction_id": transaction_id}
        _audit.record({
            "request_id": bill_id,
            "tool": "execute_confirmed_bill_payment",
            "operation": "bill_payment",
            "approval_decision": "approved",
            "execution_result": "completed",
        })
        return result
    except Exception as exc:
        contract = error_contract(exc)
        _audit.record({
            "request_id": bill_id,
            "tool": "execute_confirmed_bill_payment",
            "operation": "bill_payment",
            "execution_result": "rejected",
            "error_category": contract["error"]["category"],
        })
        return contract
