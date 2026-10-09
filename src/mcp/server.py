import json
import os
import sys
from pathlib import Path

from pydantic import AnyHttpUrl

from mcp.server.mcpserver import MCPServer, Context
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings

# 让 mcp dev 直接跑这个文件时，也能 import 到项目里的 src 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.models.request import SecurityRequest
from src.security.authentication import authenticate
from src.security.engine import SecurityEngine
from src.tools.executor import execute_tool

# 初始化你的安全引擎
security_engine = SecurityEngine()

# 监听地址 / 端口可以通过环境变量覆盖：
# - 本机直接跑（默认）：127.0.0.1:8001，只有本机进程能访问
# - 放进 Docker 里跑：容器内要绑 0.0.0.0，再由 Docker 把端口映射出来
MCP_HOST = os.getenv("MCP_HOST", "127.0.0.1")
MCP_PORT = int(os.getenv("MCP_PORT", "8001"))
MCP_RESOURCE_URL = os.getenv(
    "MCP_RESOURCE_URL",
    f"http://127.0.0.1:{MCP_PORT}/mcp",
)


class MyTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        agent_name = authenticate(token)
        if agent_name is None:
            return None
        return AccessToken(
            token=token,
            client_id=agent_name,
            scopes=[],
        )


# 创建一个 MCP Server，名字叫 AgentSecurityGateway
mcp = MCPServer(
    "AgentSecurityGateway",
    token_verifier=MyTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl("https://auth.example.com"),
        resource_server_url=AnyHttpUrl(MCP_RESOURCE_URL),
        validate_token_resource=False,
    ),
)

async def call_gateway(tool_name: str, arguments: dict) -> str:
    token = get_access_token()
    if token is None:
        return json.dumps({
            "status": "DENIED",
            "error_code": "AUTHENTICATION_FAILED",
            "reason": "缺少或无效的访问令牌"
        }, ensure_ascii=False)

    # 1. 组装你熟悉的 SecurityRequest
    request = SecurityRequest(
        api_key="",
        agent_id=token.client_id,
        tool=tool_name,
        arguments=arguments,
        trigger_message="MCP Call",
    )

    # 2. 直接调用你的九步流水线（注意：evaluate 是同步方法，不要加 await）
    decision = security_engine.evaluate(request)

    # 3. 被拒绝
    if decision.status == "DENIED":
        return json.dumps({
            "status": "DENIED",
            "error_code": decision.error_code,
            "reason": decision.reason
        }, ensure_ascii=False)

    # 4. 需要审批（PENDING）
    if decision.status == "PENDING":
        return json.dumps({
            "status": "PENDING",
            "error_code": decision.error_code,
            "reason": decision.reason,
            "approval_id": decision.approval_id
        }, ensure_ascii=False)

    # 5. 放行（ALLOWED），真正执行工具
    result = execute_tool(tool_name, decision.arguments)
    return f"<文件内容>\n{result}\n</文件内容>"

@mcp.tool()
async def read_file(file_name: str, ctx: Context) -> str:
    """读取指定文件内容。经过安全网关鉴权。"""
    return await call_gateway("read_file", {"file_name": file_name})

@mcp.tool()
async def delete_file(file_name: str, ctx: Context) -> str:
    """删除指定文件。高风险操作，受资源策略严格控制。"""
    return await call_gateway("delete_file", {"file_name": file_name})

@mcp.tool()
async def calculator(a: int, b: int, ctx: Context) -> str:
    """执行数学计算。经过安全网关鉴权。"""
    return await call_gateway("calculator", {"a": a, "b": b})

@mcp.tool()
async def search(query: str, ctx: Context) -> str:
    """搜索工具。经过安全网关鉴权。"""
    return await call_gateway("search", {"query": query})

# 最后，启动它
if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=MCP_HOST,
        port=MCP_PORT,
    )
