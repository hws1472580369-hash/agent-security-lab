from src.database.database import get_connection
from src.security.decision import SecurityDecision


def get_agent_role(agent_id):

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

    if result is None:
        return None

    return result[0]


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


def check_agent_permission(tool_name, agent_id, tool):

    # 1. 获取 Agent 的 Role
    role = get_agent_role(agent_id)

    # 2. Agent 不存在
    if role is None:
        return SecurityDecision(
            decision="DENY",
            allowed=False,
            status="DENIED",
            error_code="AGENT_NOT_FOUND",
            reason="Agent 不存在或未激活"
        )

    permissions = get_role_permissions(role)

    # 3. Tool 不存在（理论上 engine 已经查过，但保留）
    if tool is None:
        return SecurityDecision(
            decision="DENY",
            allowed=False,
            status="DENIED",
            error_code="TOOL_NOT_FOUND",
            reason=f"Tool {tool_name} 不存在"
        )

    # 4. Tool 要求的权限
    required_permission = tool.get("permission")

    # 5. 检查权限
    if required_permission not in permissions:
        return SecurityDecision(
            decision="DENY",
            allowed=False,
            status="DENIED",
            error_code="AUTHORIZATION_DENIED",
            reason=(
                f"{agent_id} 没有使用 {tool_name} "
                f"所需的 {required_permission} 权限"
            )
        )

    # 6. 权限通过
    return SecurityDecision(
        decision="ALLOW",
        allowed=True,
        status="ALLOWED",
        reason="权限检查通过"
    )