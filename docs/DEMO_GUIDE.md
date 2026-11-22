# 10-minute demo

1. Introduce the ADK-to-harness architecture and Mermaid data-flow diagram.
2. Ask for the balance and summary of `acct_demo_001`.
3. Search for seed transaction `tx_seed_001`.
4. List beneficiary `ben_demo_001`; add `acct_demo_004` using `add_beneficiary`, then retry to demonstrate duplicate prevention.
5. Request ₹500 transfer to `ben_demo_001`; point out that requesting does not move funds.
6. Confirm the sensitive execution in the ADK UI; inspect verified output and paired transactions.
7. Attempt ₹30,000 and demonstrate deterministic policy denial.
8. Attempt to use `acct_demo_003` as a source account and demonstrate cross-customer denial.
9. Request bill payment and demonstrate ADK confirmation and bill-specific owned-account selection.
10. Inspect `banking_agent/data/audit_logs.json`, run pytest/evaluation, and explain how `python scripts/recover_demo_data.py` replays a prepared journal after an interrupted demo write.

Launch using `adk web --no_use_local_storage .` so conversation context does not create ADK's default local SQLite session file.
