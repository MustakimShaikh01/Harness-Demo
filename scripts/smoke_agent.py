import asyncio
import os

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from banking_agent.agent import root_agent


async def main() -> None:
    if not os.getenv("GOOGLE_API_KEY"):
        raise SystemExit("Set GOOGLE_API_KEY in .env before running this live, billable smoke test.")

    app_name = "banking_agent"
    user_id = "bankguard-smoke-test"
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name=app_name, user_id=user_id)
    runner = Runner(agent=root_agent, app_name=app_name, session_service=session_service)
    message = types.Content(
        role="user",
        parts=[types.Part(text="Show the balance for acct_demo_001. Use the account tool.")],
    )

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=message,
    ):
        content = getattr(event, "content", None)
        if not content:
            continue
        for part in content.parts or []:
            if getattr(part, "function_call", None):
                print(f"Tool call: {part.function_call.name}")
            if getattr(part, "text", None):
                print(part.text)


if __name__ == "__main__":
    asyncio.run(main())
