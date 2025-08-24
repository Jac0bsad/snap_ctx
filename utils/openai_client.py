import os
import json
from typing import AsyncGenerator, Optional, Generator, Callable
from openai import OpenAI
from openai.types import CompletionUsage

from config import LLMConfigManager
from utils import logger_helper


logger = logger_helper.setup_logger("llm-client")


class OpenAIClient:
    def __init__(self):
        """初始化OpenAI客户端，设置token使用统计"""
        self.token_usage_total = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        self.config_manager = LLMConfigManager()

    def _get_llm_config_by_name(self, _: str) -> tuple[str]:
        llm_config = self.config_manager.get_model_config()
        return (llm_config.api_base, llm_config.api_key, llm_config.model_name)

    def update_total_token_usage(self, usage: CompletionUsage) -> None:
        """更新累计的token使用量"""
        self.token_usage_total["prompt_tokens"] += usage.prompt_tokens
        self.token_usage_total["completion_tokens"] += usage.completion_tokens
        self.token_usage_total["total_tokens"] += usage.total_tokens

    def send_messages_stream(
        self,
        messages_: list[dict],
        config_name: Optional[str] = None,
        response_format: Optional[dict] = None,
        stop: Optional[list[str]] = None,
    ) -> Generator[str, None, None]:
        """
        发送消息到大模型，并返回流式响应，处理内容过长导致的截断
        :param messages_: 消息列表
        :param response_format: 响应格式，默认为None
        :return: 流式响应生成器
        """
        api_base, api_key, model_name = self._get_llm_config_by_name(config_name)
        client = OpenAI(api_key=api_key, base_url=api_base)
        full_response = ""
        finish_reason = "length"
        messages = messages_.copy()  # 防止改变原变量
        while finish_reason != "stop" or full_response == "":
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
                response_format=response_format,
                stop=stop,
            )

            for chunk in response:
                if hasattr(chunk, "usage") and chunk.usage:  # 检查是否有 usage 信息
                    logger.debug(chunk.usage)
                    usage = chunk.usage
                    self.update_total_token_usage(usage)
                else:  # 如果没有 usage，则处理 choices 内容
                    if chunk.choices and chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                        full_response += chunk.choices[0].delta.content
                        # print(chunk.choices[0].delta.content, end='')

                    if chunk.choices and chunk.choices[0].finish_reason:
                        finish_reason = chunk.choices[0].finish_reason
                        logger.debug(chunk.choices[0].finish_reason)

            messages.append(
                {"role": "assistant", "content": full_response, "prefix": True}
            )

        logger.info("Total token usage: %s", self.token_usage_total)

    async def send_messages_stream_with_tool_call(
        self,
        messages_: list[dict],
        tools: list[dict],
        call_tool_func: Callable,
        config_name: str = "火山云deepseek",
        stop: list[str] = None,
        tool_argument_to_show: list[str] = (),
    ) -> AsyncGenerator[dict, dict]:
        """
        流式向大模型发送消息，并处理工具调用
        直到没有新的工具调用请求
        Args:
            messages_: 消息列表
            tools: 工具列表
            call_tool_func: 工具调用函数
            config_name: 配置名称，默认为'火山云deepseek'
            reasoning: 是否启用推理，默认为False
            stop: 停止条件，默认为None
            tool_argument_to_show: 会yield指定参数的值，元素为参数名
        """
        api_base, api_key, model_name = self._get_llm_config_by_name(config_name)

        client = OpenAI(api_key=api_key, base_url=api_base)

        content_all = ""
        messages = messages_.copy()  # 防止改变原变量

        while True:
            logger.info(
                "Sending messages to LLM. Current message count: %s", len(messages)
            )
            # 考虑控制messages的大小
            # logger.info(json.dumps(messages, ensure_ascii=False, indent=2))

            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools,
                stream=True,
                stream_options={"include_usage": True},
                tool_choice="required",  # None, auto, required
                stop=stop,
            )

            current_round_content = ""
            # 使用字典来重构工具调用，以其索引为键
            tool_call_deltas_by_index = {}

            for chunk in response:
                # logger.info(chunk)

                if hasattr(chunk, "usage") and chunk.usage:  # 检查是否有 usage 信息
                    logger.info(chunk.usage)
                    usage = chunk.usage
                    self.update_total_token_usage(usage)
                else:  # 如果没有 usage，则处理 choices 内容
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "reasoning_content"):
                        yield {"reasoning_content": delta.reasoning_content}

                    if delta.content:
                        current_round_content += delta.content
                        yield {"content": delta.content}
                        # logger.info(delta.content)

                    if delta.tool_calls:
                        for tool_call_delta in delta.tool_calls:
                            index = tool_call_delta.index

                            if index not in tool_call_deltas_by_index:
                                # 初始化工具调用信息
                                tool_call_deltas_by_index[index] = {
                                    "id": None,
                                    "type": "function",
                                    "function": {"name": None, "arguments": ""},
                                }

                            # 累加流式工具调用内容
                            if tool_call_delta.id:
                                tool_call_deltas_by_index[index][
                                    "id"
                                ] = tool_call_delta.id
                            if tool_call_delta.function:
                                if tool_call_delta.function.name:
                                    yield {
                                        "tool_call": f"\n调用工具{tool_call_delta.function.name}\n\n"
                                    }
                                    tool_call_deltas_by_index[index]["function"][
                                        "name"
                                    ] = tool_call_delta.function.name
                                if tool_call_delta.function.arguments:
                                    yield {
                                        "tool_call": f"{tool_call_delta.function.arguments}"
                                    }
                                    tool_call_deltas_by_index[index]["function"][
                                        "arguments"
                                    ] += tool_call_delta.function.arguments

            # 整理工具调用记录
            assistant_tool_calls_reconstructed = []
            if tool_call_deltas_by_index:
                for _idx in sorted(
                    tool_call_deltas_by_index.keys()
                ):  # 按照工具调用顺序排序
                    assistant_tool_calls_reconstructed.append(
                        tool_call_deltas_by_index[_idx]
                    )

            # 本轮的回答内容
            logger.info("Assistant turn content: %s", current_round_content)
            if assistant_tool_calls_reconstructed:
                logger.info(
                    "Assistant turn tool calls: %s",
                    json.dumps(
                        assistant_tool_calls_reconstructed, indent=2, ensure_ascii=False
                    ),
                )

            # 构建assistant的消息，将回答内和工具调用记录放入消息列表中
            assistant_message = {"role": "assistant"}
            has_content = bool(current_round_content and current_round_content.strip())
            has_tool_calls = bool(assistant_tool_calls_reconstructed)

            if has_content:
                assistant_message["content"] = current_round_content

            if has_tool_calls:
                assistant_message["tool_calls"] = assistant_tool_calls_reconstructed

            if has_content or has_tool_calls:
                messages.append(assistant_message)
            else:
                # 内容和工具调用都为空
                logger.warning(
                    "LLM response was empty for this turn. "
                    "Returning accumulated content if any, or empty string."
                )
                content_all += current_round_content
                # return content_all
                return

            # 没有进一步的工具调用，说明回答结束
            if not has_tool_calls:
                logger.info("LLM processing finished. No more tool calls requested.")
                content_all += current_round_content
                # return content_all
                return

            # 如果有工具调用，执行工具
            logger.info("LLM requested tool calls. Executing now.")
            yield {"tool_call": "\n\n正在执行相关工具\n\n"}
            for tool_call_obj in assistant_tool_calls_reconstructed:
                tool_call_id = tool_call_obj["id"]
                tool_name = tool_call_obj["function"]["name"]
                arguments_str = tool_call_obj["function"]["arguments"]

                # 检查工具参数是否完整，arguments_str可能为空
                if not all([tool_call_id, tool_name]):
                    logger.error(
                        "Malformed tool call object: ID or name missing. "
                        "Skipping. Object: %s",
                        tool_call_obj,
                    )
                    # 把错误信息放入消息列表
                    if not tool_call_id:
                        idx = assistant_tool_calls_reconstructed.index(tool_call_obj)
                        unknown_id_str = f"unknown_id_for_index_{idx}"
                        tool_id = unknown_id_str
                    else:
                        tool_id = tool_call_id
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": (
                                "Error: Tool call information was incomplete "
                                "(ID or name missing). Cannot execute."
                            ),
                        }
                    )
                    yield {"tool_call": "工具调用失败，参数格式不正确"}
                    continue

                logger.info(
                    "Executing tool: %s (ID: %s) with arguments: %s",
                    tool_name,
                    tool_call_id,
                    arguments_str,
                )

                try:
                    parsed_arguments = json.loads(arguments_str)
                    for arg in tool_argument_to_show:
                        yield {arg: f"\n\n{parsed_arguments[arg]}\n\n"}
                    tool_result = await call_tool_func(tool_name, parsed_arguments)
                except json.JSONDecodeError as e:
                    logger.error(
                        "JSON decoding error for tool %s (ID: %s) "
                        "arguments '%s': %s",
                        tool_name,
                        tool_call_id,
                        arguments_str,
                        e,
                    )
                    tool_result = (
                        "Error: Tool %s arguments were not valid JSON. "
                        "Error: %s. Arguments received: %s",
                        tool_name,
                        e,
                        arguments_str,
                    )
                except Exception as e:
                    logger.error(
                        "Error calling tool %s (ID: %s): %s",
                        tool_name,
                        tool_call_id,
                        e,
                    )
                    tool_result = (
                        f"Error: Tool {tool_name} execution failed. Details: {str(e)}\n"
                        "请调整工具的参数，重新执行"
                    )

                yield {"tool_call": f"工具执行结果{str(tool_result)}"}
                yield {"content": "\n\n"}  # 工具执行成功后，插入两个换行符
                messages.append(
                    {
                        "role": "tool",
                        "content": str(tool_result),  # 确保调用结果为字符串
                        "tool_call_id": tool_call_id,
                    }
                )

            # 带着工具结果进入下一轮循环


def main():
    client = OpenAIClient()
    messages = [{"role": "user", "content": "你好"}]
    for chunk in client.send_messages_stream(messages):
        print(chunk, end="")


if __name__ == "__main__":
    main()
