import json
from datetime import datetime
from src.database.database import get_connection


def create_approval_request(agent_id: str, tool_name: str, arguments: dict) -> int:
    """
    创建一条 PENDING 审批请求，返回 approval_id
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO approval_requests
        (agent_id, tool_name, arguments, status, created_at)
        VALUES (?, ?, ?, 'PENDING', ?)
        """,
        (
            agent_id,
            tool_name,
            json.dumps(arguments, ensure_ascii=False),
            datetime.now().isoformat()
        )
    )
    approval_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return approval_id


def get_approval_request(approval_id: int):
    """
    根据 id 查询审批请求，返回字典或 None
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, agent_id, tool_name, arguments, status,
               created_at, reviewer, reviewed_at, reject_reason,result
        FROM approval_requests
        WHERE id = ?
        """,
        (approval_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "agent_id": row[1],
        "tool_name": row[2],
        "arguments": json.loads(row[3]),
        "status": row[4],
        "created_at": row[5],
        "reviewer": row[6],
        "reviewed_at": row[7],
        "reject_reason": row[8],
        "result": row[9]
    }


def update_approval_status(approval_id: int, status: str, reviewer: str, reject_reason: str = None):
    """
    更新审批状态：APPROVED 或 REJECTED
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE approval_requests
        SET status = ?,
            reviewer = ?,
            reviewed_at = ?,
            reject_reason = ?
        WHERE id = ?
        """,
        (
            status,
            reviewer,
            datetime.now().isoformat(),
            reject_reason,
            approval_id
        )
    )
    conn.commit()
    conn.close()


def list_pending_approvals():
    """
    列出所有 PENDING 状态的审批请求
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, agent_id, tool_name, arguments, created_at
        FROM approval_requests
        WHERE status = 'PENDING'
        ORDER BY created_at ASC
        """
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": r[0],
            "agent_id": r[1],
            "tool_name": r[2],
            "arguments": json.loads(r[3]),
            "created_at": r[4]
        }
        for r in rows
    ]

def save_approval_result(approval_id: int, result: str):
    """
    把工具执行结果存进 approval_requests 表
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE approval_requests
        SET result = ?
        WHERE id = ?
        """,
        (result, approval_id)
    )
    conn.commit()
    conn.close()