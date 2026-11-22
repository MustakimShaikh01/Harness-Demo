# Audit and observability

BankGuard emits structured application log events and appends audit events for simulated financial operations and beneficiary registration to `banking_agent/data/audit_logs.json`. Read-only lookups are not individually audited. These are demo operational traces, not a tamper-proof compliance audit system.

Each event carries `previous_hash` and `event_hash`. The first event links to a 64-character zero genesis hash; later events link to the preceding event hash. `event_hash` is SHA-256 over compact UTF-8 JSON with keys sorted lexicographically, excluding `event_hash` itself. Python creates the chain; the standalone Rust CLI verifies its links and event contents without changing the log:

```bash
cargo run --manifest-path rust/audit-verifier/Cargo.toml -- verify banking_agent/data/audit_logs.json
```

Exit status is zero for a valid chain and nonzero for invalid input or a broken chain. Legacy events without hash fields are rejected; reset demo data with `python scripts/seed_demo_data.py` to generate a fresh chain.

## Fields captured

- UTC timestamp
- Request or bill reference where applicable
- Tool and operation name
- Policy and approval decisions where applicable
- Completion or rejection outcome
- Machine-readable error category on failed tool calls

The audit log deliberately does not record API keys, passwords, full account records, account balances, raw prompts, or free-form tool arguments. IDs in these examples are fictional placeholders.

## Redacted example

```json
{
  "timestamp": "2026-01-15T12:00:00+00:00",
  "request_id": "request-demo-001",
  "tool": "execute_confirmed_transfer",
  "operation": "transfer",
  "policy_decision": "allow",
  "approval_decision": "approved",
  "execution_result": "completed",
  "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "event_hash": "<64-character SHA-256 digest>"
}
```

```json
{
  "timestamp": "2026-01-15T12:01:00+00:00",
  "tool": "execute_confirmed_transfer",
  "operation": "transfer",
  "execution_result": "rejected",
  "error_category": "POLICY_DENIED"
}
```

Inspect the local demo events with:

```bash
python -m json.tool banking_agent/data/audit_logs.json
```

Reset this fictional activity by running `python scripts/seed_demo_data.py`; that script overwrites all data in the configured seed folder.

## Limitations

The hash chain detects accidental or unauthorized edits, deletions, insertions, and reordering when checked against a trusted chain head. An editor with access to the entire file can rewrite all events and recalculate every hash. The chain is not anchored or signed externally, so it is not strong tamper evidence. There is no remote log shipping, retention management, personal-data classification, or guaranteed persistence after disk failure. Do not use this design for real financial or personal data.
