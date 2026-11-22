from datetime import datetime, timezone, timedelta
from hashlib import sha256
import json
from .validation import ToolValidationError

class ApprovalManager:
    def __init__(self, repo, ttl_seconds=300): self.repo=repo; self.ttl_seconds=ttl_seconds
    def fingerprint(self, details: dict) -> str:
        canonical=json.dumps(details, sort_keys=True, separators=(",", ":"), default=str)
        return sha256(canonical.encode()).hexdigest()
    def create(self, approval_id: str, transaction_request_id: str, details: dict) -> dict:
        row={"approval_id":approval_id,"transaction_request_id":transaction_request_id,"details":details,
             "fingerprint":self.fingerprint(details),"status":"pending","created_at":datetime.now(timezone.utc).isoformat(),"expires_at":(datetime.now(timezone.utc)+timedelta(seconds=self.ttl_seconds)).isoformat()}
        rows=self.repo.list(); rows.append(row); self.repo.save_all(rows); return row
    def approve(self, approval_id: str, exact_details: dict) -> dict:
        rows=self.repo.list(); row=next((r for r in rows if r["approval_id"]==approval_id),None)
        if not row: raise ToolValidationError("APPROVAL_NOT_FOUND","Approval request was not found")
        if row["status"]!="pending": raise ToolValidationError("APPROVAL_REPLAY","Approval is not pending")
        expires=datetime.fromisoformat(row["expires_at"])
        if datetime.now(timezone.utc) >= expires: raise ToolValidationError("APPROVAL_EXPIRED","Approval has expired")
        if row["fingerprint"]!=self.fingerprint(exact_details): raise ToolValidationError("APPROVAL_MODIFIED","Approval details do not match")
        row["status"]="approved"; row["approved_at"]=datetime.now(timezone.utc).isoformat()
        self.repo.save_all(rows); return row

    def consume(self, approval_id: str) -> None:
        rows=self.repo.list()
        row=next((r for r in rows if r["approval_id"]==approval_id),None)
        if not row or row.get("status")!="approved":
            raise ToolValidationError("APPROVAL_REPLAY","Approval is not in an executable state")
        row["status"]="consumed"
        row["consumed_at"]=datetime.now(timezone.utc).isoformat()
        self.repo.save_all(rows)
