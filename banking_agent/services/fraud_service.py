from decimal import Decimal

class FraudService:
    def __init__(self, policy_engine): self.policy=policy_engine
    def assess_transfer(self, account: dict, amount: Decimal, recent_attempt_count: int) -> dict:
        threshold=Decimal(self.policy.policies["fraud"]["large_transfer_threshold"])
        reasons=[]
        if amount >= threshold: reasons.append("LARGE_TRANSFER")
        if recent_attempt_count >= 3: reasons.append("REPEATED_TRANSFER_ATTEMPTS")
        if account.get("status") != "active": reasons.append("INACTIVE_ACCOUNT_ACTIVITY")
        score=sum({"LARGE_TRANSFER":40,"REPEATED_TRANSFER_ATTEMPTS":35,"INACTIVE_ACCOUNT_ACTIVITY":50}[r] for r in reasons)
        return {"risk_level":"high" if score>=70 else "medium" if score else "low","risk_score":score,"reasons":reasons}
