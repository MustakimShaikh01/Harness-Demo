import yaml
from decimal import Decimal
from pathlib import Path

class PolicyEngine:
    def __init__(self, policy_path: Path):
        with policy_path.open("r", encoding="utf-8") as handle:
            self.policies = yaml.safe_load(handle)

    def evaluate_transfer(self, amount: Decimal, daily_total: Decimal, account_active: bool, beneficiary_exists: bool) -> dict:
        reasons=[]
        transfer=self.policies["transfer"]
        if not account_active: reasons.append("SOURCE_ACCOUNT_INACTIVE")
        if not beneficiary_exists: reasons.append("BENEFICIARY_NOT_FOUND")
        if amount < Decimal(transfer["min_amount"]): reasons.append("BELOW_MINIMUM")
        if amount > Decimal(transfer["max_amount"]): reasons.append("ABOVE_MAXIMUM")
        if daily_total + amount > Decimal(transfer["daily_limit"]): reasons.append("DAILY_LIMIT_EXCEEDED")
        return {"decision":"allow" if not reasons else "deny", "reasons":reasons}
