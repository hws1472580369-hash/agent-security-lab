from src.database.database import get_connection




def authenticate(api_key):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT agent_name
        FROM agents
        WHERE api_key = ?
        AND status = 'active'
        """,
        (api_key,)
    )

    result = cursor.fetchone()

    conn.close()

    if result is None:
        return None

    return result[0]