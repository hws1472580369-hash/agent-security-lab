"""最小 MCP 客户端：观察一次工具调用的数据流。"""

from __future__ import annotations

import argparse
import asyncio
import json

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="测试 MCP HTTP 工具调用")
    parser.add_argument("--url", default="http://127.0.0.1:8001/mcp")
    parser.add_argument("--token", default="key_agent_002")
    parser.add_argument("--tool", default="read_file")
    parser.add_argument(
        "--args",
        default='{"file_name": "public.txt"}',
        help="工具参数的 JSON 字符串",
    )
    return parser


async def run() -> None:
    options = build_parser().parse_args()
    arguments = json.loads(options.args)

    print("=" * 60)
    print("[1] MCP 客户端准备发送请求")
    print(f"    URL: {options.url}")
    print("    请求头: Authorization: Bearer ***")
    print(f"    工具: {options.tool}")
    print(f"    参数: {arguments}")

    headers = {"Authorization": f"Bearer {options.token}"}
    async with httpx2.AsyncClient(headers=headers, timeout=30.0) as http_client:
        async with streamable_http_client(options.url, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                print("[2] 初始化 MCP 会话...")
                await session.initialize()

                print("[3] 调用工具...")
                result = await session.call_tool(options.tool, arguments)

                text = "\n".join(
                    getattr(block, "text", "")
                    for block in result.content
                )
                print("[4] 网关返回结果")
                print("-" * 60)
                print(text)
                print("-" * 60)
                print(f"is_error: {result.is_error}")


if __name__ == "__main__":
    asyncio.run(run())

