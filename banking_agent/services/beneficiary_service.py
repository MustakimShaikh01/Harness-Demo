from uuid import uuid4

from ..storage.json_store import JsonStore
from ..harness.authorization import AuthorizationEngine
from ..harness.validation import ToolValidationError, account_id

class BeneficiaryService:
    def __init__(self, store: JsonStore, auth: AuthorizationEngine): self.store=store; self.auth=auth
    def list(self):
        return [b for b in self.store.read("beneficiaries.json",[]) if b.get("customer_id")==self.auth.trusted_customer_id]
    def get(self, beneficiary_id: str):
        beneficiary=next((b for b in self.store.read("beneficiaries.json",[]) if b["beneficiary_id"]==beneficiary_id),None)
        self.auth.beneficiary_owned_by_customer(beneficiary)
        return beneficiary

    def add(self, name: str, destination_account_id: str) -> dict:
        normalized_name = name.strip() if isinstance(name, str) else ""
        if not normalized_name or len(normalized_name) > 80:
            raise ToolValidationError(
                "INVALID_BENEFICIARY_NAME",
                "Beneficiary name must contain 1 to 80 non-whitespace characters",
            )
        destination_id = account_id(destination_account_id)
        accounts = self.store.read("accounts.json", [])
        destination = next((row for row in accounts if row.get("account_id") == destination_id), None)
        if destination is None:
            raise ToolValidationError("ACCOUNT_NOT_FOUND", "Destination account was not found")
        if destination.get("status") != "active":
            raise ToolValidationError("ACCOUNT_INACTIVE", "Destination account is inactive")
        if destination.get("customer_id") == self.auth.trusted_customer_id:
            raise ToolValidationError("SELF_BENEFICIARY", "Choose another demo customer's account")

        beneficiaries = self.store.read("beneficiaries.json", [])
        if any(
            row.get("customer_id") == self.auth.trusted_customer_id
            and row.get("account_id") == destination_id
            for row in beneficiaries
        ):
            raise ToolValidationError(
                "DUPLICATE_BENEFICIARY",
                "This destination account is already registered as a beneficiary",
            )

        beneficiary = {
            "beneficiary_id": f"ben_{uuid4().hex}",
            "customer_id": self.auth.trusted_customer_id,
            "name": normalized_name,
            "account_id": destination_id,
            "status": "active",
            "verified": False,
        }
        beneficiaries.append(beneficiary)
        self.store.write("beneficiaries.json", beneficiaries)
        return beneficiary
