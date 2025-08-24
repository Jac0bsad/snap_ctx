from typing import Optional
from mcp.server import FastMCP


async def get_prompt_from_mcp(
    mcp: FastMCP, name: str, arguments: Optional[dict] = None
) -> str:
    """
    从mcp获取提示词
    Args:
        name: 提示词的名称，应该为定义时候的函数名
        arguments: 提示词的参数
    Returns:
        str: 提示词
    """
    mcp_prompt = await mcp.get_prompt(name=name, arguments=arguments)
    prompt = mcp_prompt.messages[0]
    return prompt.content.text


async def get_tools_from_mcp(mcp: FastMCP) -> list[dict]:
    """
    把mcp的工具列表转换为openai的工具列表格式
        {
            "type": tool["type"],
            "function": {
                "name": unique_name,
                "description": tool["function"]["description"],
                "parameters": tool["function"]["parameters"],
            },
        }
    """
    mcp_tools = await mcp.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }
        for tool in mcp_tools
    ]
