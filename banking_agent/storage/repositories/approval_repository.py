from ..json_store import JsonStore

class ApprovalRepository:
    def __init__(self, store: JsonStore): self.store = store
    def list(self): return self.store.read("approvals.json", [])
    def save_all(self, rows): self.store.write("approvals.json", rows)
