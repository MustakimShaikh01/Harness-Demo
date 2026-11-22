from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types
from .config.settings import MAX_OUTPUT_TOKENS, MODEL
from .prompts.banking_instructions import BANKING_INSTRUCTIONS
from .tools.account_tools import get_account, get_account_summary, get_balance
from .tools.transaction_tools import get_transaction_history, search_transaction
from .tools.beneficiary_tools import add_beneficiary, list_beneficiaries
from .tools.transfer_tools import request_transfer, execute_confirmed_transfer
from .tools.bill_tools import get_bill_details, list_pending_bills, request_bill_payment, execute_confirmed_bill_payment
from .tools.fraud_tools import assess_transfer_risk
from .harness.callbacks import before_tool_callback, after_tool_callback

confirmed_transfer_tool = FunctionTool(
    func=execute_confirmed_transfer,
    require_confirmation=True,
)
confirmed_bill_payment_tool = FunctionTool(
    func=execute_confirmed_bill_payment,
    require_confirmation=True,
)
confirmed_add_beneficiary_tool = FunctionTool(
    func=add_beneficiary,
    require_confirmation=True,
)

root_agent = LlmAgent(
    name="bankguard_banking_agent",
    model=MODEL,
    description="A controlled simulated-banking assistant for the active demo customer.",
    instruction=BANKING_INSTRUCTIONS,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    ),
    tools=[
        get_account, get_account_summary, get_balance, get_transaction_history,
        search_transaction, list_beneficiaries, confirmed_add_beneficiary_tool, request_transfer,
        confirmed_transfer_tool, list_pending_bills, get_bill_details,
        request_bill_payment, confirmed_bill_payment_tool, assess_transfer_risk,
    ],
    before_tool_callback=before_tool_callback,
    after_tool_callback=after_tool_callback,
)
