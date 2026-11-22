from .validation import ToolValidationError

class AuthorizationEngine:
    def __init__(self, trusted_customer_id: str): self.trusted_customer_id = trusted_customer_id
    def own_account(self, account: dict) -> None:
        if not account:
            raise LookupError("Account was not found")
        if account.get("customer_id") != self.trusted_customer_id:
            raise PermissionError("Account does not belong to the active demo customer")
    def beneficiary_owned_by_customer(self, beneficiary: dict) -> None:
        if not beneficiary or beneficiary.get("customer_id") != self.trusted_customer_id:
            raise PermissionError("Beneficiary is outside the active customer's scope")
