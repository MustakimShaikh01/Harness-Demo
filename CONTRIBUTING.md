# Contributing

Thank you for helping improve this educational project.

## Local checks

```bash
python -m pip install -r requirements.txt
pytest -q
python banking_agent/evaluation/evaluation_runner.py
```

The deterministic suite must not require a Google API key or modify the seeded demo dataset. `python scripts/smoke_agent.py` is an optional live model check and may incur API usage.

## Engineering boundaries

- Keep all data fictional; never add credentials or customer information.
- Do not let the model decide authorization, limits, balances or approval status.
- Add tests for ownership, policy and persistence behavior when changing a sensitive workflow.
- Preserve `Decimal` for monetary arithmetic and decimal strings in JSON.
- Document behavior and limitations honestly; a passing simulation is not production certification.
