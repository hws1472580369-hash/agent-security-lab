from datetime import datetime, timedelta
from src.database.database import get_connection


RATE_WINDOW_MINUTES = 1
RATE_MAX_REQUESTS = 50

def check_rate_limit(agent_id: str) -> bool:
    """
    检查该 Agent 最近 1 分钟内的请求是否超过阈值。
    返回 True 表示允许（未超限），False 表示拒绝（超限）。
    """
    cutoff = (datetime.now() - timedelta(minutes=RATE_WINDOW_MINUTES)).isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM audit_logs
        WHERE agent_id = ?
          AND timestamp >= ?
        """,
        (agent_id, cutoff)
    )
    count = cursor.fetchone()[0]
    conn.close()

    return count < RATE_MAX_REQUESTS
