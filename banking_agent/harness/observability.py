import json, logging
from datetime import datetime, timezone
from .audit_integrity import GENESIS_HASH, append_integrity_fields, verify_document
from ..storage.json_store import JsonStore

logger=logging.getLogger("bankguard")

class AuditLogger:
    def __init__(self, store: JsonStore): self.store=store
    def record(self, event: dict) -> None:
        event={"timestamp":datetime.now(timezone.utc).isoformat(),**event}
        rows=self.store.read("audit_logs.json", [])
        if rows:
            head = verify_document(rows)["head_hash"]
        else:
            head = GENESIS_HASH
        linked_event = append_integrity_fields(event, head)
        logger.info(json.dumps(linked_event, sort_keys=True, default=str))
        rows.append(linked_event)
        self.store.write("audit_logs.json", rows)
