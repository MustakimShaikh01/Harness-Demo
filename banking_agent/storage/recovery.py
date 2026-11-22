from pathlib import Path
from typing import Any

from .file_lock import file_lock
from .json_store import JsonStore


class RecoveryError(RuntimeError):
    """Raised when a prepared write-ahead record cannot be safely replayed."""


def _apply_snapshot(store: JsonStore, entry: dict[str, Any], key: str, filename: str) -> None:
    snapshot = entry.get(key)
    if not isinstance(snapshot, list):
        raise RecoveryError(f"Prepared journal entry is missing a valid {key} snapshot")
    store.write(filename, snapshot)


def _complete_idempotency(store: JsonStore, request_id: str, transaction_id: str) -> None:
    rows = store.read("idempotency.json", [])
    for row in rows:
        if row.get("request_id") == request_id:
            row["status"] = "completed"
            row["result"] = {"success": True, "transaction_id": transaction_id}
            store.write("idempotency.json", rows)
            return
    raise RecoveryError(f"No idempotency record exists for prepared request {request_id}")


def _consume_approval(store: JsonStore, approval_id: str) -> None:
    rows = store.read("approvals.json", [])
    approval = next((row for row in rows if row.get("approval_id") == approval_id), None)
    if approval is None:
        raise RecoveryError(f"No approval record exists for prepared approval {approval_id}")
    if approval.get("status") not in {"approved", "consumed"}:
        raise RecoveryError(f"Prepared approval {approval_id} is not approved")
    approval["status"] = "consumed"
    store.write("approvals.json", rows)


def _validate_recovery_refs(store: JsonStore, entry: dict[str, Any], operation: str) -> tuple[str, str, str]:
    request_id = entry.get("request_id") or entry.get("bill_id")
    transaction_id = entry.get("transaction_id")
    approval_id = entry.get("approval_id")
    if not all(isinstance(value, str) and value for value in (request_id, transaction_id, approval_id)):
        raise RecoveryError(f"Prepared {operation} journal entry lacks required identifiers")

    approvals = store.read("approvals.json", [])
    approval = next((row for row in approvals if row.get("approval_id") == approval_id), None)
    if not approval or approval.get("status") not in {"approved", "consumed"}:
        raise RecoveryError(f"Prepared approval {approval_id} is not approved")
    requests = store.read("idempotency.json", [])
    if not any(row.get("request_id") == request_id for row in requests):
        raise RecoveryError(f"No idempotency record exists for prepared request {request_id}")
    return request_id, transaction_id, approval_id


def _recover_journal(
    store: JsonStore,
    journal_name: str,
    snapshots: tuple[tuple[str, str], ...],
    operation: str,
) -> list[dict[str, str]]:
    entries = store.read(journal_name, [])
    recovered: list[dict[str, str]] = []
    for entry in entries:
        if entry.get("status") != "prepared":
            continue
        request_id, transaction_id, approval_id = _validate_recovery_refs(store, entry, operation)
        for snapshot_key, _ in snapshots:
            if not isinstance(entry.get(snapshot_key), list):
                raise RecoveryError(f"Prepared journal entry is missing a valid {snapshot_key} snapshot")
        for snapshot_key, filename in snapshots:
            _apply_snapshot(store, entry, snapshot_key, filename)
        if operation in {"transfer", "bill_payment"}:
            _complete_idempotency(store, request_id, transaction_id)
        _consume_approval(store, approval_id)

        entry["status"] = "committed"
        store.write(journal_name, entries)
        recovered.append({"operation": operation, "request_id": request_id, "status": "recovered"})
    return recovered


def recover_pending_operations(data_dir: Path | str | JsonStore) -> list[dict[str, str]]:
    """Redo prepared transfer and bill-payment snapshots while holding the operation lock."""
    store = data_dir if isinstance(data_dir, JsonStore) else JsonStore(Path(data_dir))
    with file_lock(store.data_dir / ".bankguard.lock"):
        recovered = _recover_journal(
            store,
            "transfer_journal.json",
            (("accounts_after", "accounts.json"), ("transactions_after", "transactions.json")),
            "transfer",
        )
        recovered.extend(_recover_journal(
            store,
            "bill_payment_journal.json",
            (
                ("accounts_after", "accounts.json"),
                ("transactions_after", "transactions.json"),
                ("bills_after", "bills.json"),
            ),
            "bill_payment",
        ))
        return recovered
