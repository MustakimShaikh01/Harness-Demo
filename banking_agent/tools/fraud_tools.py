from decimal import Decimal
from ..config.settings import DATA_DIR
from ..storage.json_store import JsonStore
from ..harness.policy_engine import PolicyEngine
from ..services.fraud_service import FraudService
_store=JsonStore(DATA_DIR); _policy=PolicyEngine(__import__('pathlib').Path(__file__).resolve().parents[1]/'config'/'policies.yaml')
_service=FraudService(_policy)

def assess_transfer_risk(account_status: str, amount: str, recent_attempt_count: int=0) -> dict:
    """Return deterministic fraud indicators for a proposed transfer."""
    account={"status":account_status}
    return {"success":True,"assessment":_service.assess_transfer(account,Decimal(str(amount)),recent_attempt_count)}
