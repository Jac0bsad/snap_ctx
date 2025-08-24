import asyncio
from snap_ctx_mcp import mcp_server, context_saver
from utils.mcp_utils import get_prompt_from_mcp, get_tools_from_mcp
from utils.openai_client import OpenAIClient


async def get_context(user_input: str) -> str:
    client = OpenAIClient()
    tools = await get_tools_from_mcp(mcp_server)
    system_prompt = await get_prompt_from_mcp(
        mcp_server,
        "summarize_ctx",
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    cxt = ""

    async for chunk in client.send_messages_stream_with_tool_call(
        messages_=messages,
        tools=tools,
        call_tool_func=mcp_server.call_tool,
    ):
        if chunk.get("content"):
            cxt += chunk["content"]
        # yield chunk

    return cxt


def main():
    asyncio.run(get_context("这个项目的目的是什么？是如何实现的？"))
    print(f"context collected:\n{context_saver.context_collected}")


if __name__ == "__main__":
    main()
