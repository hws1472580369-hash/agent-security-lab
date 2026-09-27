import json
from src.database.database import get_connection


def get_tool(name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, permission, action, resource_key, schema_json, enabled
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
        "schema": json.loads(row[4]) if row[4] else None,
        "enabled": bool(row[5])
    }


def list_enabled_tools():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, description, permission, action, resource_key, schema_json, enabled
        FROM tools
        WHERE enabled = 1
        """
    )
    rows = cursor.fetchall()
    conn.close()

    tools = []
    for row in rows:
        tools.append({
            "name": row[0],
            "description": row[1],
            "permission": row[2],
            "action": row[3],
            "resource_key": row[4],
            "schema": json.loads(row[5]) if row[5] else None,
            "enabled": bool(row[6]),
        })
    return tools
