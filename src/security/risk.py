from pydantic import BaseModel
from src.database.database import get_connection


def get_action(tool):
    # 直接从 tool 对象拿，不再猜字符串
    return tool.get("action")


def get_resource(tool, arguments):
    resource_key = tool.get("resource_key")
    if resource_key:
        return arguments.get(resource_key)
    return None


class RiskContext(BaseModel):
    agent_id: str
    role: str
    tool: str
    action: str
    resource: str | None = None
    resource_level: str | None = None
    arguments: dict


def get_resource_level(resource):
    if resource is None:
        return "NONE"
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT level
        FROM resources
        WHERE name = ?
        """,
        (resource,)
    )

    result = cursor.fetchone()
    conn.close()

    if result is None:
        return None

    return result[0]

def get_history_penalty(agent_id: str) -> int:
    """
    根据历史行为计算惩罚分数。
    最近 5 分钟内被拒绝 3 次及以上 → +30 分。
    """
    from datetime import datetime, timedelta

    cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM audit_logs
        WHERE agent_id = ?
          AND status = 'DENIED'
          AND timestamp >= ?
        """,
        (agent_id, cutoff)
    )
    count = cursor.fetchone()[0]
    conn.close()

    if count >= 3:
        return 30
    return 0

def get_risk_score(context):
    """
    计算风险分数，返回原始分数（int）。
    不做等级映射，由 Decision 层决定怎么处理。
    """
    score = 0

    # ① 动作本身的分数
    score += get_factor_score("action", context.action)

    # ② 资源敏感度的分数
    if context.resource_level is not None:
        score += get_factor_score("resource_level", context.resource_level)

    # ③ 角色的分数
    if context.role is not None:
        score += get_factor_score("role", context.role)

    # ④ 历史行为的惩罚
    score += get_history_penalty(context.agent_id)

    return score

def get_factor_score(factor_type: str, factor_value: str) -> int:
    """
    查 risk_factors 表，拿某个维度某个值的分数。找不到返回 0。
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT score FROM risk_factors
        WHERE factor_type = ? AND factor_value = ?
        """,
        (factor_type, factor_value)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return 0

    return row[0]


def score_to_risk_level(score: int) -> str:
    """
    把总分映射为风险等级。
    """
    if score < 30:
        return "LOW"
    elif score < 50:
        return "MEDIUM"
    else:
        return "HIGH"