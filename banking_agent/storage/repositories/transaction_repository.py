from ..json_store import JsonStore

class TransactionRepository:
    def __init__(self, store: JsonStore): self.store = store
    def list(self): return self.store.read("transactions.json", [])
    def add(self, transaction):
        rows = self.list(); rows.append(transaction); self.store.write("transactions.json", rows)
