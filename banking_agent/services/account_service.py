from ..storage.repositories.account_repository import AccountRepository
from ..harness.authorization import AuthorizationEngine

class AccountService:
    def __init__(self, accounts: AccountRepository, auth: AuthorizationEngine): self.accounts=accounts; self.auth=auth
    def get_account(self, account_id: str):
        account=self.accounts.get(account_id)
        if account is None:
            raise LookupError("Account was not found")
        self.auth.own_account(account)
        return account
