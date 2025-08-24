import asyncio
from mcp.server import FastMCP

from utils.file_helper import get_file_content, get_tree_pathlib

mcp_server = FastMCP("snap_ctx")


class ContextSaver:
    def __init__(self):
        self.context_collected = ""

    def save_ctx(self, ctx: str):
        self.context_collected += ctx


context_saver = ContextSaver()


@mcp_server.prompt(title="summarize_ctx")
async def summarize_ctx():
    system_prompt = """
# 上下文摘要专家

## 角色定位
您是一个专业的上下文摘要专家，专注于从当前目录结构中提取和总结项目信息。

## 主要职责
1. 分析用户请求，确定需要总结的信息类型和范围
2. 使用get_tree_structure工具获取当前目录的文件树结构
3. 基于文件树结构和用户需求，选择相关的文件
4. 使用get_file_content_tool获取选定文件的内容
5. 提炼关键信息，生成结构化摘要

## 执行流程
1. 接收用户请求后，首先分析总结需求的具体用途和范围
2. 获取完整的目录结构作为基础参考
3. 根据用户需求筛选相关文件（如代码文件、文档、配置文件等）
4. 按优先级顺序获取文件内容
5. 生成包含以下内容的摘要，调用save_ctx工具保存相关关键上下文：
   - 项目结构概述
   - 关键文件及其功能说明
   - 主要代码逻辑或配置要点
   - 项目依赖和技术栈信息
   - 结构化的Markdown格式摘要，包含清晰的章节划分和重点突出

## 注意事项
- 仅处理当前目录及其子目录下的文件
- 如果用户请求过于宽泛，需要询问具体关注点
- 遇到无法访问的文件时跳过并记录
- 摘要长度控制在合理范围内，突出核心信息
- 不回答项目功能性问题，只提供客观信息摘要
- 你不需要直接回答用户的问题，也不需要直接输出收集到的上下文，当前的任务只是收集上下文信息，并使用save_ctx工具进行保存，用于后续的回答

## 输出格式
上下文收集完成后，输出`DONE`即可
"""
    return system_prompt


@mcp_server.tool(name="get_tree_structure")
async def get_tree_structure() -> str:
    """获取当前目录下的文件树结构"""
    return get_tree_pathlib()


@mcp_server.tool(name="get_file_content_tool")
async def get_file_content_tool(file_path: str) -> str:
    """
    获取指定文件的内容
    Args:
        file_path: 文件路径
    Returns:
        文件内容
    """
    return get_file_content(file_path)


@mcp_server.tool(name="save_ctx")
async def save_ctx(ctx: str):
    """
    增量保存上下文信息，每次输入的字符串会追加到最后
    """
    context_saver.save_ctx(ctx)


async def main():
    res = await mcp_server.list_prompts()
    print(res)
    print(type(res))
    print(res[0].name)
    prompt = await mcp_server.get_prompt(name=res[0].name)
    print(prompt.messages[0])


if __name__ == "__main__":
    asyncio.run(main())
    # sql_mcp.run(transport="streamable-http")
