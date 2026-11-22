from ..config.settings import DATA_DIR, ACTIVE_CUSTOMER_ID
from ..storage.json_store import JsonStore
from ..storage.repositories.account_repository import AccountRepository
from ..storage.repositories.transaction_repository import TransactionRepository
from ..harness.authorization import AuthorizationEngine
from ..services.transaction_service import TransactionService
from ..harness.error_handler import error_contract
from ..harness.validation import account_id
_store=JsonStore(DATA_DIR); _auth=AuthorizationEngine(ACTIVE_CUSTOMER_ID)
_service=TransactionService(TransactionRepository(_store),AccountRepository(_store),_auth)

def get_transaction_history(account_id_value: str, date: str=None, transaction_type: str=None) -> dict:
    """Get owned-account history, optionally filtering by ISO date prefix or debit/credit type."""
    try:
        account_id(account_id_value)
        return {"success":True,"transactions":_service.history(account_id_value,date,transaction_type)}
    except Exception as exc: return error_contract(exc)

def search_transaction(account_id_value: str, transaction_id: str) -> dict:
    """Find one transaction by ID after verifying ownership of the supplied account."""
    try:
        account_id(account_id_value)
        rows=_service.history(account_id_value)
        transaction=next((row for row in rows if row.get("transaction_id")==transaction_id),None)
        if transaction is None:
            return {"success":False,"error":{"category":"NOT_FOUND","message":"Transaction was not found"}}
        return {"success":True,"transaction":transaction}
    except Exception as exc: return error_contract(exc)
