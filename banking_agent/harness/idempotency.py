from ..storage.json_store import JsonStore

class IdempotencyManager:
    def __init__(self, store: JsonStore): self.store=store
    def get(self, request_id: str):
        rows=self.store.read("idempotency.json", [])
        return next((r for r in rows if r["request_id"]==request_id),None)
    def reserve(self, request_id: str, operation: str) -> dict:
        rows=self.store.read("idempotency.json", [])
        existing=next((r for r in rows if r["request_id"]==request_id),None)
        if existing:
            return existing
        row={"request_id":request_id,"operation":operation,"status":"reserved","result":None}
        rows.append(row); self.store.write("idempotency.json", rows); return row
    def complete(self, request_id: str, result: dict) -> None:
        rows=self.store.read("idempotency.json", [])
        for row in rows:
            if row["request_id"]==request_id:
                row["status"]="completed"; row["result"]={"success":True,"transaction_id":result.get("transaction_id")}
        self.store.write("idempotency.json", rows)
