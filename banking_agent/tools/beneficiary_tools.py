from ..config.settings import DATA_DIR, ACTIVE_CUSTOMER_ID
from ..storage.json_store import JsonStore
from ..harness.authorization import AuthorizationEngine
from ..services.beneficiary_service import BeneficiaryService
from ..harness.error_handler import error_contract
_store=JsonStore(DATA_DIR); _auth=AuthorizationEngine(ACTIVE_CUSTOMER_ID); _service=BeneficiaryService(_store,_auth)

def list_beneficiaries() -> dict:
    """List beneficiaries belonging to the active demo customer."""
    try: return {"success":True,"beneficiaries":_service.list()}
    except Exception as exc: return error_contract(exc)
