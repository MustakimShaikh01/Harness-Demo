# 10-minute demo

1. Introduce the ADK-to-harness architecture and Mermaid data-flow diagram.
2. Ask for the balance and summary of `acct_demo_001`.
3. Search for seed transaction `tx_seed_001`.
4. List beneficiary `ben_demo_001` and pending bill `bill_demo_001`.
5. Request ₹500 transfer to `ben_demo_001`; point out that requesting does not move funds.
6. Confirm the sensitive execution in the ADK UI; inspect verified output and paired transactions.
7. Attempt ₹30,000 and demonstrate deterministic policy denial.
8. Attempt `acct_demo_003` and demonstrate cross-customer denial.
9. Request bill payment and demonstrate ADK confirmation and bill-specific owned-account selection.
10. Inspect `banking_agent/data/audit_logs.json`, then run pytest and the local evaluation runner.

Launch using `adk web --no_use_local_storage .` so conversation context does not create ADK's default local SQLite session file.
