import asyncio
import argparse
import pyperclip
from snap_ctx_mcp import mcp_server, context_saver
from utils.logger_helper import setup_logger
from utils.mcp_utils import get_prompt_from_mcp, get_tools_from_mcp
from utils.openai_client import OpenAIClient

logger = setup_logger()


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

    llm_output = ""

    async for chunk in client.send_messages_stream_with_tool_call(
        messages_=messages,
        tools=tools,
        call_tool_func=mcp_server.call_tool,
    ):
        if chunk.get("content"):
            llm_output += chunk["content"]
        # yield chunk

    return llm_output


def main():
    # 设置命令行参数解析
    parser = argparse.ArgumentParser(
        description="Snap Context Tool - get related context under the current folder"
    )
    parser.add_argument(
        "query",
        help="describe the query",
    )

    args = parser.parse_args()

    # 执行主逻辑
    asyncio.run(get_context(args.query))
    logger.info("context collected:\n%s", context_saver.context_collected)

    print(context_saver.context_collected)
    pyperclip.copy(context_saver.context_collected)
    logger.info("context copied to clipboard")


if __name__ == "__main__":
    main()
