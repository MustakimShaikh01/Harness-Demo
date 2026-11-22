import json
from pathlib import Path

def test_evaluation_catalog_exists():
    cases=json.loads(Path('banking_agent/evaluation/test_cases.json').read_text())
    assert len(cases)>=20
