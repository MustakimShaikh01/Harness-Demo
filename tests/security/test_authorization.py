from pathlib import Path
from banking_agent.storage.json_store import JsonStore
from banking_agent.harness.authorization import AuthorizationEngine

def test_cross_customer_denied(tmp_path):
    store=JsonStore(tmp_path); store.write('accounts.json',[{'account_id':'acct_foreign','customer_id':'cust_other','balance':'1'}]); auth=AuthorizationEngine('cust_demo_001')
    account=store.read('accounts.json')[0]
    try:
        auth.own_account(account); assert False
    except PermissionError:
        assert True
