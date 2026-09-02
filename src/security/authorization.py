from src.security.authentication import AGENTS
from src.security.decision import SecurityDecision


def check_agent_permission(tool_name, agent_id, TOOLS):

    # 1. 找 Agent
    agent = AGENTS.get(agent_id)

    if agent is None:
        return SecurityDecision(
            allowed=False,
            error_code="AGENT_NOT_FOUND",
            reason="Agent 不存在"
        )

    # 2. 找 Role
    role = agent["role"]

    # 3. 找 Role 的权限
    permissions = {
        "normal_agent": [
            "search.use",
            "calculator.use"
        ],

        "file_agent": [
            "search.use",
            "calculator.use",
            "file.read",
            "file.delete"
        ],

        "admin": [
            "search.use",
            "calculator.use",
            "file.read",
            "file.write",
            "file.delete"
        ]
    }.get(role, [])

    # 4. 找 Tool
    tool = TOOLS.get(tool_name)

    if tool is None:
        return SecurityDecision(
            allowed=False,
            error_code="TOOL_NOT_FOUND",
            reason=f"Tool {tool_name} 不存在"
        )

    # 5. Tool 要求的权限
    required_permission = tool.get("permission")

    # 6. 检查权限
    if required_permission not in permissions:
        return SecurityDecision(
            allowed=False,
            error_code="AUTHORIZATION_DENIED",
            reason=(
                f"{agent_id} 没有使用 {tool_name} "
                f"所需的 {required_permission} 权限"
            )
        )

    # 7. 权限通过
    return SecurityDecision(
        allowed=True,
        reason="权限检查通过"
    )