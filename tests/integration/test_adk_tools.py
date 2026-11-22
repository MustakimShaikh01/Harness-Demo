import asyncio
from types import SimpleNamespace

from google.adk.tools import FunctionTool
from google.adk.tools.tool_confirmation import ToolConfirmation

from banking_agent.agent import root_agent


def test_sensitive_execution_tools_require_adk_confirmation():
    tools = {
        tool.name if isinstance(tool, FunctionTool) else tool.__name__: tool
        for tool in root_agent.tools
    }
    for name in ("execute_confirmed_transfer", "execute_confirmed_bill_payment", "add_beneficiary"):
        tool = tools[name]
        assert isinstance(tool, FunctionTool)
        assert tool._require_confirmation is True


def test_agent_limits_output_for_cost_control():
    assert root_agent.generate_content_config.max_output_tokens == 384
    assert root_agent.generate_content_config.temperature == 0.1


def test_adk_rejected_confirmation_does_not_invoke_sensitive_tool():
    tool = next(
        tool for tool in root_agent.tools
        if isinstance(tool, FunctionTool) and tool.name == "execute_confirmed_transfer"
    )
    context = SimpleNamespace(tool_confirmation=ToolConfirmation(confirmed=False))

    result = asyncio.run(tool.run_async(
        args={
            "approval_id": "unused",
            "source_account_id": "acct_demo_001",
            "beneficiary_id": "ben_demo_001",
            "amount": "10.00",
            "request_id": "rejected-demo",
        },
        tool_context=context,
    ))

    assert result == {"error": "This tool call is rejected."}
