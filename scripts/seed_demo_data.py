from pathlib import Path
import json

def main() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "banking_agent" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    accounts = [
        {"account_id": "acct_demo_001", "customer_id": "cust_demo_001", "name": "Aarav Sharma",
         "balance": "100000.00", "currency": "INR", "status": "active", "account_type": "savings"},
        {"account_id": "acct_demo_002", "customer_id": "cust_demo_001", "name": "Aarav Sharma",
         "balance": "25000.00", "currency": "INR", "status": "active", "account_type": "checking"},
        {"account_id": "acct_demo_003", "customer_id": "cust_demo_002", "name": "Meera Iyer",
         "balance": "50000.00", "currency": "INR", "status": "active", "account_type": "savings"},
    ]
    beneficiaries = [
        {"beneficiary_id": "ben_demo_001", "customer_id": "cust_demo_001", "name": "Family Savings",
         "account_id": "acct_demo_002", "status": "active", "verified": True},
        {"beneficiary_id": "ben_demo_002", "customer_id": "cust_demo_001", "name": "Utility Partner",
         "account_id": "acct_demo_003", "status": "active", "verified": True},
    ]
    transactions = [
        {"transaction_id": "tx_seed_001", "account_id": "acct_demo_001", "amount": "2500.00",
         "currency": "INR", "type": "debit", "status": "completed",
         "date": "2026-11-20T10:00:00+00:00", "description": "Demo grocery payment"},
    ]
    bills = [
        {"bill_id": "bill_demo_001", "customer_id": "cust_demo_001", "account_id": "acct_demo_001",
         "biller": "Metro Electric", "amount": "1850.00", "currency": "INR",
         "due_date": "2026-11-30", "status": "pending"},
    ]
    files = {
        "accounts.json": accounts,
        "beneficiaries.json": beneficiaries,
        "transactions.json": transactions,
        "bills.json": bills,
        "approvals.json": [],
        "idempotency.json": [],
        "audit_logs.json": [],
        "transfer_journal.json": [],
        "bill_payment_journal.json": [],
    }
    for name, data in files.items():
        (data_dir / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Seeded BankGuard demo data in {data_dir}")


if __name__ == "__main__":
    main()
