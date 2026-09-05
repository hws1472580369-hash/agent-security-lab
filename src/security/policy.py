from src.database.database import get_connection
from src.security.decision import SecurityDecision


def check_policy(tool_name, arguments):

    if tool_name not in ["read_file", "delete_file"]:
        return SecurityDecision(
            allowed=True,
            reason="无需进行资源策略检查"
        )

    file_name = arguments["file_name"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT resource_policies.action,
               resource_policies.allowed
        FROM resources
        JOIN resource_policies
        ON resources.id = resource_policies.resource_id
        WHERE resources.name = ?
        """,
        (file_name,)
    )

    result = cursor.fetchall()

    conn.close()

    if not result:
        return SecurityDecision(
            allowed=False,
            error_code="RESOURCE_NOT_FOUND",
            reason=f"资源 {file_name} 不在允许访问的资源列表中"
        )

    action = "read" if tool_name == "read_file" else "delete"

    for policy_action, allowed in result:

        if policy_action == action:

            if not allowed:
                return SecurityDecision(
                    allowed=False,
                    error_code="RESOURCE_ACCESS_DENIED",
                    reason=f"不允许对资源 {file_name} 执行 {action} 操作"
                )

            return SecurityDecision(
                allowed=True,
                reason="资源策略检查通过"
            )

    return SecurityDecision(
        allowed=False,
        error_code="POLICY_NOT_FOUND",
        reason=f"资源 {file_name} 没有定义 {action} 策略"
    )