from src.database.database import get_connection
from src.security.decision import SecurityDecision

def get_role_permissions(role):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT permissions.name

        FROM roles

        JOIN role_permissions
        ON roles.id = role_permissions.role_id

        JOIN permissions
        ON permissions.id = role_permissions.permission_id

        WHERE roles.name = ?
        """,
        (role,)
    )

    permissions = [
        row[0]
        for row in cursor.fetchall()
    ]

    conn.close()

    return permissions

def check_agent_permission(tool_name, agent_id, TOOLS):

    # 1. 从数据库查 Agent
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role
        FROM agents
        WHERE agent_name = ?
        AND status = 'active'
        """,
        (agent_id,)
    )

    result = cursor.fetchone()

    conn.close()

    # 2. Agent 不存在
    if result is None:
        return SecurityDecision(
            allowed=False,
            error_code="AGENT_NOT_FOUND",
            reason="Agent 不存在或未激活"
        )

    # 3. 获取 Role
    role = result[0]

    permissions = get_role_permissions(role)

    # 5. 找 Tool
    tool = TOOLS.get(tool_name)

    if tool is None:
        return SecurityDecision(
            allowed=False,
            error_code="TOOL_NOT_FOUND",
            reason=f"Tool {tool_name} 不存在"
        )

    # 6. Tool 要求的权限
    required_permission = tool.get("permission")

    # 7. 检查权限
    if required_permission not in permissions:
        return SecurityDecision(
            allowed=False,
            error_code="AUTHORIZATION_DENIED",
            reason=(
                f"{agent_id} 没有使用 {tool_name} "
                f"所需的 {required_permission} 权限"
            )
        )

    # 8. 权限通过
    return SecurityDecision(
        allowed=True,
        reason="权限检查通过"
    )

