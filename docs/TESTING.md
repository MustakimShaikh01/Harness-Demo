# Testing

```bash
pytest -q
python banking_agent/evaluation/evaluation_runner.py
```

The local suite covers policy boundaries, transfer and bill-payment integration, ADK sensitive-tool confirmation configuration, cross-customer authorization, approval modification/expiry/replay, malformed JSON and money validation. Tests use temporary directories and do not call Gemini.

The evaluation runner executes the deterministic unit, integration and security tests and reports their actual pass/fail counts. `banking_agent/evaluation/test_cases.json` is a scenario catalog for planned coverage; it is not falsely reported as fully executed. Live Gemini testing is separate and optional:

```bash
python scripts/smoke_agent.py
```

That script sends one short model request and can incur API usage.
