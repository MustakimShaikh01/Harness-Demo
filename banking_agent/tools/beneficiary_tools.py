from ..config.settings import DATA_DIR, ACTIVE_CUSTOMER_ID
from ..storage.json_store import JsonStore
from ..harness.authorization import AuthorizationEngine
from ..services.beneficiary_service import BeneficiaryService
from ..harness.error_handler import error_contract
from ..harness.validation import account_id
from ..harness.observability import AuditLogger
from ..storage.file_lock import file_lock
_store=JsonStore(DATA_DIR); _auth=AuthorizationEngine(ACTIVE_CUSTOMER_ID); _service=BeneficiaryService(_store,_auth)
_audit=AuditLogger(_store)

def list_beneficiaries() -> dict:
    """List beneficiaries belonging to the active demo customer."""
    try: return {"success":True,"beneficiaries":_service.list()}
    except Exception as exc: return error_contract(exc)

def add_beneficiary(name: str, destination_account_id: str) -> dict:
    """Add an active demo account as a beneficiary after duplicate and ownership-scope checks."""
    audit_reference = "beneficiary_registration"
    try:
        account_id(destination_account_id)
        with file_lock(_store.data_dir / ".bankguard.lock"):
            beneficiary = _service.add(name, destination_account_id)
        _audit.record({
            "request_id": beneficiary["beneficiary_id"],
            "tool": "add_beneficiary",
            "operation": "beneficiary_registration",
            "execution_result": "completed",
        })
        return {"success":True,"beneficiary":beneficiary}
    except Exception as exc:
        contract = error_contract(exc)
        _audit.record({
            "tool": "add_beneficiary",
            "operation": audit_reference,
            "execution_result": "rejected",
            "error_category": contract["error"]["category"],
        })
        return contract
