from ..config.settings import DATA_DIR, ACTIVE_CUSTOMER_ID
from ..storage.json_store import JsonStore
from ..storage.repositories.account_repository import AccountRepository
from ..harness.authorization import AuthorizationEngine
from ..harness.validation import account_id, ToolValidationError
from ..services.account_service import AccountService
from ..harness.error_handler import error_contract

_store=JsonStore(DATA_DIR); _auth=AuthorizationEngine(ACTIVE_CUSTOMER_ID); _service=AccountService(AccountRepository(_store),_auth)

def get_account(account_id_value: str) -> dict:
    """Return an account owned by the active demo customer."""
    try:
        account_id(account_id_value)
        account=_service.get_account(account_id_value)
        if account is None: raise ToolValidationError("ACCOUNT_NOT_FOUND","Account was not found")
        return {"success":True,"account":account}
    except Exception as exc:
        return error_contract(exc)

def get_balance(account_id_value: str) -> dict:
    """Return the available balance for an owned demo account."""
    result=get_account(account_id_value)
    if not result["success"]: return result
    account=result["account"]
    return {"success":True,"account_id":account["account_id"],"available_balance":account["balance"],"currency":account["currency"]}

def get_account_summary(account_id_value: str) -> dict:
    """Return the account type, status and available balance for an owned demo account."""
    result=get_account(account_id_value)
    if not result["success"]: return result
    account=result["account"]
    return {
        "success":True,
        "account_id":account["account_id"],
        "account_type":account["account_type"],
        "status":account["status"],
        "available_balance":account["balance"],
        "currency":account["currency"],
    }
