import json, logging
from datetime import datetime, timezone
from pathlib import Path
from ..storage.json_store import JsonStore

logger=logging.getLogger("bankguard")

class AuditLogger:
    def __init__(self, store: JsonStore): self.store=store
    def record(self, event: dict) -> None:
        event={"timestamp":datetime.now(timezone.utc).isoformat(),**event}
        logger.info(json.dumps(event, sort_keys=True, default=str))
        rows=self.store.read("audit_logs.json", [])
        rows.append(event); self.store.write("audit_logs.json", rows)
