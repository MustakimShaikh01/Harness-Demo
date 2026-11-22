import pytest

from banking_agent.harness.authorization import AuthorizationEngine
from banking_agent.harness.validation import ToolValidationError
from banking_agent.services.beneficiary_service import BeneficiaryService
from banking_agent.storage.json_store import JsonStore


def build_service(tmp_path):
    store = JsonStore(tmp_path)
    store.write("accounts.json", [
        {"account_id": "acct_owner", "customer_id": "cust_demo_001", "status": "active"},
        {"account_id": "acct_recipient", "customer_id": "cust_demo_002", "status": "active"},
        {"account_id": "acct_new_recipient", "customer_id": "cust_demo_002", "status": "active"},
        {"account_id": "acct_inactive", "customer_id": "cust_demo_002", "status": "inactive"},
    ])
    store.write("beneficiaries.json", [
        {"beneficiary_id": "ben_existing", "customer_id": "cust_demo_001",
         "account_id": "acct_recipient", "name": "Recipient"},
    ])
    return store, BeneficiaryService(store, AuthorizationEngine("cust_demo_001"))


def test_add_beneficiary_for_active_account(tmp_path):
    store, service = build_service(tmp_path)

    beneficiary = service.add("Family Recipient", "acct_new_recipient")

    assert beneficiary["beneficiary_id"].startswith("ben_")
    assert beneficiary["customer_id"] == "cust_demo_001"
    assert service.get(beneficiary["beneficiary_id"]) == beneficiary


def test_duplicate_beneficiary_account_is_rejected(tmp_path):
    _, service = build_service(tmp_path)

    with pytest.raises(ToolValidationError) as error:
        service.add("Another name", "acct_recipient")

    assert error.value.code == "DUPLICATE_BENEFICIARY"


def test_nonexistent_and_inactive_destination_are_rejected(tmp_path):
    _, service = build_service(tmp_path)

    with pytest.raises(ToolValidationError) as missing:
        service.add("Missing", "acct_unknown")
    with pytest.raises(ToolValidationError) as inactive:
        service.add("Inactive", "acct_inactive")

    assert missing.value.code == "ACCOUNT_NOT_FOUND"
    assert inactive.value.code == "ACCOUNT_INACTIVE"


def test_beneficiary_input_is_validated_and_duplicate_safe(tmp_path):
    _, service = build_service(tmp_path)

    with pytest.raises(ToolValidationError) as invalid_name:
        service.add("  ", "acct_owner")
    with pytest.raises(ToolValidationError) as self_beneficiary:
        service.add("Self", "acct_owner")

    assert invalid_name.value.code == "INVALID_BENEFICIARY_NAME"
    assert self_beneficiary.value.code == "SELF_BENEFICIARY"
