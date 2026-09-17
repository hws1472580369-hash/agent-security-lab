import json
from src.database.database import get_connection


def get_tool(name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, permission, action, resource_key, risk_level, schema_json, enabled
        FROM tools
        WHERE name = ?
        """,
        (name,)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "name": row[0],
        "permission": row[1],
        "action": row[2],
        "resource_key": row[3],
        "risk_level": row[4],
        "schema": json.loads(row[5]) if row[5] else None,
        "enabled": bool(row[6])
    }