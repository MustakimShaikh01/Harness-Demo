from google.adk.tools import FunctionTool

from banking_agent.agent import root_agent


def test_sensitive_execution_tools_require_adk_confirmation():
    tools = {
        tool.name if isinstance(tool, FunctionTool) else tool.__name__: tool
        for tool in root_agent.tools
    }
    for name in ("execute_confirmed_transfer", "execute_confirmed_bill_payment"):
        tool = tools[name]
        assert isinstance(tool, FunctionTool)
        assert tool._require_confirmation is True


def test_agent_limits_output_for_cost_control():
    assert root_agent.generate_content_config.max_output_tokens == 384
    assert root_agent.generate_content_config.temperature == 0.1
