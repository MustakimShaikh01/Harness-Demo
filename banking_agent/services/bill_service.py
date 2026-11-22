from ..storage.json_store import JsonStore
from ..harness.authorization import AuthorizationEngine

class BillService:
    def __init__(self, store: JsonStore, auth: AuthorizationEngine): self.store=store; self.auth=auth
    def list(self):
        return [b for b in self.store.read("bills.json",[]) if b.get("customer_id")==self.auth.trusted_customer_id]
    def get(self, bill_id: str):
        bill=next((b for b in self.store.read("bills.json",[]) if b["bill_id"]==bill_id),None)
        if not bill or bill.get("customer_id")!=self.auth.trusted_customer_id: raise PermissionError("Bill is outside the active customer scope")
        return bill
