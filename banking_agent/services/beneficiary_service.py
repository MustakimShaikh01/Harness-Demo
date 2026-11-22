from ..storage.json_store import JsonStore
from ..harness.authorization import AuthorizationEngine

class BeneficiaryService:
    def __init__(self, store: JsonStore, auth: AuthorizationEngine): self.store=store; self.auth=auth
    def list(self):
        return [b for b in self.store.read("beneficiaries.json",[]) if b.get("customer_id")==self.auth.trusted_customer_id]
    def get(self, beneficiary_id: str):
        beneficiary=next((b for b in self.store.read("beneficiaries.json",[]) if b["beneficiary_id"]==beneficiary_id),None)
        self.auth.beneficiary_owned_by_customer(beneficiary); return beneficiary
