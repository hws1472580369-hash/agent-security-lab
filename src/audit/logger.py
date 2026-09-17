import json
from datetime import datetime
from src.database.database import get_connection


def log_event(agent_id, tool_name, arguments, allowed, reason, error_code=None, status="ALLOWED"):
    timestamp = datetime.now().isoformat()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO audit_logs
        (timestamp, agent_id, tool_name, arguments, allowed, reason, error_code, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            timestamp,
            agent_id,
            tool_name,
            json.dumps(arguments, ensure_ascii=False),
            int(allowed),
            reason,
            error_code,
            status,
        )
    )

    conn.commit()
    conn.close()

    print(f"[{timestamp}] agent={agent_id} tool={tool_name} allowed={allowed} status={status} reason={reason}")