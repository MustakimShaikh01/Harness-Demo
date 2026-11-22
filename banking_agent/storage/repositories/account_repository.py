from pathlib import Path
from ..json_store import JsonStore

class AccountRepository:
    def __init__(self, store: JsonStore): self.store = store
    def list(self): return self.store.read("accounts.json", [])
    def get(self, account_id: str):
        return next((a for a in self.list() if a["account_id"] == account_id), None)
    def save_all(self, accounts): self.store.write("accounts.json", accounts)
