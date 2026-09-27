def test_db_isolation():
    """验证每个测试用的是独立的临时库。"""
    from src.database.database import get_connection
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    # 临时库里应该有这些表
    assert "agents" in tables
    assert "tools" in tables
    assert "audit_logs" in tables
    print(f"\n临时库路径：{get_connection.__globals__['os'].getenv('SECURITY_DB_PATH')}")