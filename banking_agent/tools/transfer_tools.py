from uuid import uuid4
from pathlib import Path
from ..config.settings import DATA_DIR, ACTIVE_CUSTOMER_ID
from ..storage.json_store import JsonStore
from ..storage.repositories.approval_repository import ApprovalRepository
from ..harness.policy_engine import PolicyEngine
from ..harness.authorization import AuthorizationEngine
from ..harness.approval_manager import ApprovalManager
from ..harness.idempotency import IdempotencyManager
from ..harness.validation import positive_money, account_id
from ..harness.error_handler import error_contract
from ..harness.observability import AuditLogger
from ..services.transfer_service import TransferService
_store=JsonStore(DATA_DIR); _auth=AuthorizationEngine(ACTIVE_CUSTOMER_ID)
_policy=PolicyEngine(Path(__file__).resolve().parents[1]/'config'/'policies.yaml')
_approval=ApprovalManager(ApprovalRepository(_store),ttl_seconds=int(_policy.policies["approval"]["ttl_seconds"])); _idem=IdempotencyManager(_store)
_service=TransferService(_store,_policy,_auth,_approval,_idem); _audit=AuditLogger(_store)

def request_transfer(source_account_id: str, beneficiary_id: str, amount: str, currency: str="INR", request_id: str=None) -> dict:
    """Create an exact-details approval request; this function never moves money."""
    try:
        account_id(source_account_id); value=positive_money(amount,currency)
        result=_service.request(source_account_id,beneficiary_id,value,request_id)
        _audit.record({"request_id":request_id or result["transaction_request_id"],"tool":"request_transfer","operation":"transfer","policy_decision":"allow","approval_decision":"pending","execution_result":"approval_required"})
        return result
    except Exception as exc:
        contract=error_contract(exc); _audit.record({"tool":"request_transfer","operation":"transfer","execution_result":"rejected","error_category":contract["error"]["category"]}); return contract

def execute_confirmed_transfer(approval_id: str, source_account_id: str, beneficiary_id: str, amount: str, request_id: str, currency: str="INR") -> dict:
    """Execute a transfer only after a matching, approved, unexpired approval."""
    try:
        account_id(source_account_id); value=positive_money(amount,currency)
        result=_service.execute(approval_id,request_id,source_account_id,beneficiary_id,value)
        _audit.record({"request_id":request_id,"tool":"execute_confirmed_transfer","operation":"transfer","policy_decision":"allow","approval_decision":"approved","execution_result":"completed"})
        return result
    except Exception as exc:
        contract=error_contract(exc); _audit.record({"request_id":request_id,"tool":"execute_confirmed_transfer","operation":"transfer","execution_result":"rejected","error_category":contract["error"]["category"]}); return contract
