import json
from pathlib import Path

def test_evaluation_catalog_exists():
    cases=json.loads(Path('banking_agent/evaluation/test_cases.json').read_text())
    assert len(cases)>=20
    assert all(case.get("test_nodeid", "").startswith("tests/") for case in cases)
    assert len({case["id"] for case in cases}) == len(cases)
