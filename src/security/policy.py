import json
from datetime import datetime
from src.database.database import get_connection


def check_condition(condition_str, agent_role):
    """
    检查条件是否满足。condition_str 是 JSON 字符串或 None。
    支持字段：role, hour_min, hour_max
    """
    if condition_str is None:
        return True

    try:
        condition = json.loads(condition_str)
    except json.JSONDecodeError:
        return False

    # 检查 role
    if "role" in condition:
        if agent_role != condition["role"]:
            return False

    # 检查时间窗
    current_hour = datetime.now().hour

    if "hour_min" in condition:
        if current_hour < condition["hour_min"]:
            return False

    if "hour_max" in condition:
        if current_hour >= condition["hour_max"]:
            return False

    return True


def check_policy(tool_name, arguments, tool, agent_role):
    """
    硬边界判断：资源 + 动作 + 条件。
    返回：{"passed": bool, "error_code": str|None, "reason": str}
    不返回 SecurityDecision。最终决策由 Decision 层做。
    """

    resource_key = tool.get("resource_key")

    if resource_key is None:
        return {
            "passed": True,
            "error_code": None,
            "reason": "无需进行资源策略检查"
        }

    file_name = arguments.get(resource_key)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT resource_policies.action,
               resource_policies.allowed,
               resource_policies.condition
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
        return {
            "passed": False,
            "error_code": "RESOURCE_NOT_FOUND",
            "reason": f"资源 {file_name} 不在允许访问的资源列表中"
        }

    action = tool.get("action")

    for policy_action, allowed, condition in result:

        if policy_action == action:

            if not allowed:
                return {
                    "passed": False,
                    "error_code": "RESOURCE_ACCESS_DENIED",
                    "reason": f"不允许对资源 {file_name} 执行 {action} 操作"
                }

            if not check_condition(condition, agent_role):
                return {
                    "passed": False,
                    "error_code": "CONDITION_NOT_MET",
                    "reason": f"资源 {file_name} 的 {action} 策略条件不满足"
                }

            return {
                "passed": True,
                "error_code": None,
                "reason": "资源策略检查通过"
            }

    return {
        "passed": False,
        "error_code": "POLICY_NOT_FOUND",
        "reason": f"资源 {file_name} 没有定义 {action} 策略"
    }