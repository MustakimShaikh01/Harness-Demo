from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from pathlib import Path

from ..harness.validation import ToolValidationError
from ..harness.policy_engine import PolicyEngine
from ..harness.authorization import AuthorizationEngine
from ..harness.approval_manager import ApprovalManager
from ..harness.idempotency import IdempotencyManager
from ..storage.json_store import JsonStore
from ..storage.file_lock import file_lock

class TransferService:
    def __init__(self, store: JsonStore, policy: PolicyEngine, auth: AuthorizationEngine,
                 approval: ApprovalManager, idem: IdempotencyManager):
        self.store=store; self.policy=policy; self.auth=auth; self.approval=approval; self.idem=idem

    def request(self, source_account_id: str, beneficiary_id: str, amount: Decimal, request_id: str=None) -> dict:
        lock_path=self.store.data_dir/'.bankguard.lock'
        with file_lock(lock_path):
            accounts=self.store.read("accounts.json",[])
            source=next((a for a in accounts if a["account_id"]==source_account_id),None)
            self.auth.own_account(source)
            beneficiaries=self.store.read("beneficiaries.json",[])
            beneficiary=next((b for b in beneficiaries if b["beneficiary_id"]==beneficiary_id),None)
            self.auth.beneficiary_owned_by_customer(beneficiary)
            existing=self.idem.get(request_id) if request_id else None
            if existing:
                if existing["status"]=="completed": raise ToolValidationError("DUPLICATE_REQUEST","This transfer request was already completed")
                if existing["status"]=="reserved":
                    pending=next((row for row in self.approval.repo.list()
                                  if row["transaction_request_id"]==request_id and row["status"]=="pending"),None)
                    if pending:
                        return {"success":True,"status":"approval_required","approval_id":pending["approval_id"],
                                "transaction_request_id":request_id,"details":pending["details"]}
                    raise ToolValidationError("REQUEST_IN_PROGRESS","This transfer request is already being processed")
            txs=self.store.read("transactions.json",[])
            today=datetime.now(timezone.utc).date().isoformat()
            daily=sum((Decimal(t["amount"]) for t in txs if t.get("from_account")==source_account_id and t.get("date","").startswith(today)),Decimal("0"))
            policy=self.policy.evaluate_transfer(amount,daily,source.get("status")=="active",beneficiary is not None)
            if policy["decision"]=="deny": raise ToolValidationError("POLICY_DENIED",", ".join(policy["reasons"]))
            if Decimal(str(source["balance"])) < amount: raise ToolValidationError("INSUFFICIENT_FUNDS","Available balance is insufficient")
            rid=request_id or str(uuid4())
            self.idem.reserve(rid,"transfer")
            approval_id=str(uuid4())
            details={"type":"transfer","source_account_id":source_account_id,"beneficiary_id":beneficiary_id,
                     "amount":format(amount,'.2f'),"currency":"INR","request_id":rid}
            approval=self.approval.create(approval_id,rid,details)
            return {"success":True,"status":"approval_required","approval_id":approval_id,
                    "transaction_request_id":rid,"details":details}

    def execute(self, approval_id: str, request_id: str, source_account_id: str, beneficiary_id: str, amount: Decimal) -> dict:
        lock_path=self.store.data_dir/'.bankguard.lock'
        with file_lock(lock_path):
            exact={"type":"transfer","source_account_id":source_account_id,"beneficiary_id":beneficiary_id,
                   "amount":format(amount,'.2f'),"currency":"INR","request_id":request_id}
            approved=self.approval.approve(approval_id,exact)
            idem=self.idem.get(request_id)
            if not idem or idem["status"]=="completed": raise ToolValidationError("DUPLICATE_REQUEST","This transfer has already completed")
            accounts=self.store.read("accounts.json",[])
            source=next((a for a in accounts if a["account_id"]==source_account_id),None)
            beneficiary=next((b for b in self.store.read("beneficiaries.json",[]) if b["beneficiary_id"]==beneficiary_id),None)
            self.auth.own_account(source); self.auth.beneficiary_owned_by_customer(beneficiary)
            destination=next((a for a in accounts if a["account_id"]==beneficiary["account_id"]),None)
            if not destination: raise ToolValidationError("INVALID_BENEFICIARY","Beneficiary account was not found")
            txs=self.store.read("transactions.json",[])
            today=datetime.now(timezone.utc).date().isoformat()
            daily=sum((Decimal(t["amount"]) for t in txs if t.get("from_account")==source_account_id and t.get("date","").startswith(today)),Decimal("0"))
            policy=self.policy.evaluate_transfer(amount,daily,source.get("status")=="active",beneficiary is not None)
            if policy["decision"]=="deny": raise ToolValidationError("POLICY_DENIED",", ".join(policy["reasons"]))
            if Decimal(str(source["balance"])) < amount: raise ToolValidationError("INSUFFICIENT_FUNDS","Available balance is insufficient")

            source["balance"]=((Decimal(str(source["balance"]))-amount).quantize(Decimal("0.01"))).__format__(".2f")
            destination["balance"]=((Decimal(str(destination["balance"]))+amount).quantize(Decimal("0.01"))).__format__(".2f")
            transaction_id=str(uuid4())
            now=datetime.now(timezone.utc).isoformat()
            # Write-ahead journal makes a crash recoverable; account and transaction commits remain atomic per files.
            journal=self.store.read("transfer_journal.json",[])
            journal.append({"status":"prepared","transaction_id":transaction_id,"request_id":request_id,"details":exact,"timestamp":now})
            self.store.write("transfer_journal.json",journal)
            self.store.write("accounts.json",accounts)
            txs.append({"transaction_id":transaction_id,"account_id":source_account_id,"from_account":source_account_id,
                        "to_account":destination["account_id"],"beneficiary_id":beneficiary_id,"amount":format(amount,'.2f'),
                        "currency":"INR","type":"debit","status":"completed","date":now,"description":"Simulated transfer"})
            txs.append({"transaction_id":transaction_id,"account_id":destination["account_id"],"from_account":source_account_id,
                        "to_account":destination["account_id"],"beneficiary_id":beneficiary_id,"amount":format(amount,'.2f'),
                        "currency":"INR","type":"credit","status":"completed","date":now,"description":"Simulated transfer received"})
            self.store.write("transactions.json",txs)
            journal[-1]["status"]="committed"; self.store.write("transfer_journal.json",journal)
            self.idem.complete(request_id,{"transaction_id":transaction_id})
            return {"success":True,"status":"completed","transaction_id":transaction_id,"amount":format(amount,'.2f'),"currency":"INR"}
