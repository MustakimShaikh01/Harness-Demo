from ..storage.repositories.transaction_repository import TransactionRepository
from ..harness.authorization import AuthorizationEngine
from ..harness.validation import ToolValidationError

class TransactionService:
    def __init__(self, transactions: TransactionRepository, accounts, auth: AuthorizationEngine):
        self.transactions=transactions; self.accounts=accounts; self.auth=auth
    def history(self, account_id: str, date=None, transaction_type=None):
        if transaction_type not in (None, "debit", "credit"):
            raise ToolValidationError("INVALID_TRANSACTION_TYPE", "Transaction type must be debit or credit")
        account=self.accounts.get(account_id); self.auth.own_account(account)
        rows=[r for r in self.transactions.list() if r.get("account_id")==account_id]
        if date: rows=[r for r in rows if r.get("date","").startswith(date)]
        if transaction_type: rows=[r for r in rows if r.get("type")==transaction_type]
        return rows
