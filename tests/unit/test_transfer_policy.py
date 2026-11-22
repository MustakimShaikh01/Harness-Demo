from decimal import Decimal
from pathlib import Path
from banking_agent.harness.policy_engine import PolicyEngine

def test_transfer_limits():
    policy=PolicyEngine(Path('banking_agent/config/policies.yaml'))
    assert policy.evaluate_transfer(Decimal('25001'),Decimal('0'),True,True)['decision']=='deny'
    assert policy.evaluate_transfer(Decimal('100'),Decimal('49901'),True,True)['decision']=='deny'
    assert policy.evaluate_transfer(Decimal('100'),Decimal('0'),True,True)['decision']=='allow'
