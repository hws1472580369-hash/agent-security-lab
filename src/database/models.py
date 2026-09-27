from src.database.database import get_connection


def create_tables():
    print("开始创建数据库")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS resources(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            level TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()
    print("数据库创建完成")


def create_agent_table():
    print("开始创建 agents 表")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS agents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL,
            api_key TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL DEFAULT 'normal_agent',
            status TEXT NOT NULL
        )
        """
    )
    cursor.execute("PRAGMA table_info(agents)")
    columns = [row[1] for row in cursor.fetchall()]
    if "role" not in columns:
        cursor.execute(
            """
            ALTER TABLE agents
            ADD COLUMN role TEXT NOT NULL DEFAULT 'normal_agent'
            """
        )
    conn.commit()
    conn.close()
    print("agents 表创建/检查完成")


def create_role_tables():
    print("开始创建角色和权限表")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS roles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS permissions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS role_permissions(
            role_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            PRIMARY KEY(role_id, permission_id),
            FOREIGN KEY(role_id) REFERENCES roles(id),
            FOREIGN KEY(permission_id) REFERENCES permissions(id)
        )
        """
    )
    conn.commit()
    conn.close()
    print("角色和权限表创建完成")


def create_resource_policy_table():
    print("开始创建资源策略表")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS resource_policies(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            allowed INTEGER NOT NULL,
            UNIQUE(resource_id, action),
            FOREIGN KEY(resource_id) REFERENCES resources(id)
        )
        """
    )
    conn.commit()
    conn.close()
    print("资源策略表创建完成")


def create_tools_table():
    print("开始创建 tools 表")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tools(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            permission TEXT NOT NULL,
            action TEXT NOT NULL,
            resource_key TEXT,
            schema_json TEXT,
            enabled INTEGER DEFAULT 1
        )
        """
    )
    conn.commit()
    conn.close()
    print("tools 表创建完成")

def create_audit_logs_table():
    print("开始创建 audit_logs 表")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            agent_id TEXT,
            tool_name TEXT,
            arguments TEXT,
            allowed INTEGER NOT NULL,
            reason TEXT,
            error_code TEXT,
            risk_score INTEGER,
            trigger_message TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    print("audit_logs 表创建完成")

def create_approval_requests_table():
    print("开始创建 approval_requests 表")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_requests(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            created_at TEXT NOT NULL,
            reviewer TEXT,
            reviewed_at TEXT,
            reject_reason TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    print("approval_requests 表创建完成")

def create_risk_factors_table():
    print("开始创建 risk_factors 表")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS risk_factors(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            factor_type TEXT NOT NULL,
            factor_value TEXT NOT NULL,
            score INTEGER NOT NULL,
            UNIQUE(factor_type, factor_value)
        )
        """
    )
    conn.commit()
    conn.close()
    print("risk_factors 表创建完成") 

def add_condition_column_to_resource_policies():
    print("检查 resource_policies 表的 condition 字段")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(resource_policies)")
    columns = [row[1] for row in cursor.fetchall()]

    if "condition" not in columns:
        cursor.execute(
            """
            ALTER TABLE resource_policies
            ADD COLUMN condition TEXT
            """
        )
        print("已添加 condition 字段")
    else:
        print("condition 字段已存在")

    conn.commit()
    conn.close()       

def add_status_column_to_audit_logs():
    print("检查 audit_logs 表的 status 字段")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(audit_logs)")
    columns = [row[1] for row in cursor.fetchall()]

    if "status" not in columns:
        cursor.execute(
            """
            ALTER TABLE audit_logs
            ADD COLUMN status TEXT
            """
        )
        print("已添加 status 字段")
    else:
        print("status 字段已存在")

    conn.commit()
    conn.close()		

def add_audit_logs_new_columns():
    print("检查 audit_logs 的新字段")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(audit_logs)")
    columns = [row[1] for row in cursor.fetchall()]

    if "risk_score" not in columns:
        cursor.execute(
            """
            ALTER TABLE audit_logs
            ADD COLUMN risk_score INTEGER
            """
        )
        print("已添加 risk_score 字段")
    else:
        print("risk_score 字段已存在")

    if "trigger_message" not in columns:
        cursor.execute(
            """
            ALTER TABLE audit_logs
            ADD COLUMN trigger_message TEXT
            """
        )
        print("已添加 trigger_message 字段")
    else:
        print("trigger_message 字段已存在")

    conn.commit()
    conn.close()
    				
def clean_resources():
    print("清理重复资源")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM resources
        WHERE id NOT IN(
            SELECT MIN(id)
            FROM resources
            GROUP BY name
        )
        """
    )
    conn.commit()
    conn.close()
    print("重复资源清理完成")


def create_resource_unique_index():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS
        idx_resources_name
        ON resources(name)
        """
    )
    conn.commit()
    conn.close()


def insert_resources():
    print("检查资源数据")
    conn = get_connection()
    cursor = conn.cursor()
    resources = [
        ("public.txt", "file", "PUBLIC"),
        ("customer_records.txt", "file", "SENSITIVE"),
        ("internal_notes.txt", "file", "SECRET"),
        ("test_risk.txt", "file", "SENSITIVE"),
        ("test_timewindow.txt", "file", "SENSITIVE")
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO resources
        (name, type, level)
        VALUES (?, ?, ?)
        """,
        resources
    )
    conn.commit()
    conn.close()
    print("资源数据检查完成")


def insert_agents():
    print("开始写入 Agent")
    conn = get_connection()
    cursor = conn.cursor()
    agents = [
        ("agent_001", "key_agent_001", "normal_agent", "active"),
        ("agent_002", "key_agent_002", "file_agent", "active"),
        ("admin_001", "key_admin_001", "admin", "active")
    ]
    cursor.executemany(
        """
        INSERT OR IGNORE INTO agents
        (agent_name, api_key, role, status)
        VALUES (?, ?, ?, ?)
        """,
        agents
    )
    conn.commit()
    conn.close()
    print("Agent 写入完成")


def insert_roles_and_permissions():
    print("开始初始化角色和权限")
    conn = get_connection()
    cursor = conn.cursor()
    roles = [("normal_agent",), ("file_agent",), ("admin",)]
    cursor.executemany(
        "INSERT OR IGNORE INTO roles(name) VALUES(?)",
        roles
    )
    permissions = [
        ("search.use",),
        ("calculator.use",),
        ("file.read",),
        ("file.write",),
        ("file.delete",)
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO permissions(name) VALUES(?)",
        permissions
    )
    conn.commit()
    conn.close()
    print("角色和权限初始化完成")


def insert_role_permissions():
    print("开始初始化角色权限关系")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM roles")
    roles = {row[1]: row[0] for row in cursor.fetchall()}
    cursor.execute("SELECT id, name FROM permissions")
    permissions = {row[1]: row[0] for row in cursor.fetchall()}
    relations = [
        ("normal_agent", "search.use"),
        ("normal_agent", "calculator.use"),
        ("file_agent", "search.use"),
        ("file_agent", "calculator.use"),
        ("file_agent", "file.read"),
        ("file_agent", "file.delete"),
        ("admin", "search.use"),
        ("admin", "calculator.use"),
        ("admin", "file.read"),
        ("admin", "file.write"),
        ("admin", "file.delete")
    ]
    for role, permission in relations:
        cursor.execute(
            """
            INSERT OR IGNORE INTO role_permissions
            (role_id, permission_id)
            VALUES (?, ?)
            """,
            (roles[role], permissions[permission])
        )
    conn.commit()
    conn.close()
    print("角色权限关系初始化完成")


def insert_resource_policies():
    conn = get_connection()
    cursor = conn.cursor()
    policies = [
        ("public.txt", "read", 1),
        ("public.txt", "delete", 1),
        ("customer_records.txt", "read", 1),
        ("customer_records.txt", "delete", 0),
        ("internal_notes.txt", "read", 0),
        ("internal_notes.txt", "delete", 0),
        ("test_risk.txt", "read", 1),
        ("test_risk.txt", "delete", 1),
        ("test_timewindow.txt", "read", 1),
        ("test_timewindow.txt", "delete", 1)
    ]
    for resource_name, action, allowed in policies:
        cursor.execute(
            "SELECT id FROM resources WHERE name = ?",
            (resource_name,)
        )
        result = cursor.fetchone()
        if result is None:
            continue
        resource_id = result[0]
        cursor.execute(
            """
            INSERT OR IGNORE INTO resource_policies
            (resource_id, action, allowed)
            VALUES (?, ?, ?)
            """,
            (resource_id, action, allowed)
        )
    conn.commit()
    conn.close()


def insert_tools():
    print("开始初始化工具数据")
    import json
    conn = get_connection()
    cursor = conn.cursor()
    
    tools_data = [
        (
            "search", 
            "搜索工具", 
            "search.use", 
            "search", 
            None, 
            json.dumps({
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            })
        ),
        (
            "calculator", 
            "计算器", 
            "calculator.use", 
            "execute", 
            None, 
            json.dumps({
                "type": "object",
                "properties": {
                    "a": {"type": "integer"},
                    "b": {"type": "integer"}
                },
                "required": ["a", "b"]
            })
        ),
        (
            "read_file", 
            "读取文件", 
            "file.read", 
            "read", 
            "file_name", 
            json.dumps({
                "type": "object",
                "properties": {"file_name": {"type": "string"}},
                "required": ["file_name"]
            })
        ),
        (
            "delete_file", 
            "删除文件", 
            "file.delete", 
            "delete", 
            "file_name", 
            json.dumps({
                "type": "object",
                "properties": {"file_name": {"type": "string"}},
                "required": ["file_name"]
            })
        )
    ]

    cursor.executemany(
        """
        INSERT OR IGNORE INTO tools
        (name, description, permission, action, resource_key, schema_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        tools_data
    )
    conn.commit()
    conn.close()
    print("工具数据初始化完成")

def add_result_column_to_approval_requests():
    print("检查 approval_requests 表的 result 字段")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(approval_requests)")
    columns = [row[1] for row in cursor.fetchall()]

    if "result" not in columns:
        cursor.execute(
            """
            ALTER TABLE approval_requests
            ADD COLUMN result TEXT
            """
        )
        print("已添加 result 字段")
    else:
        print("result 字段已存在")

    conn.commit()
    conn.close()    

def insert_risk_factors():
    print("开始初始化风险因素分数")
    conn = get_connection()
    cursor = conn.cursor()

    factors = [
        # action 维度
        ("action", "read",      10),
        ("action", "delete",    30),
        ("action", "execute",   20),
        ("action", "search",     5),

        # resource_level 维度
        ("resource_level", "PUBLIC",      0),
        ("resource_level", "SENSITIVE",  20),
        ("resource_level", "SECRET",     60),
        ("resource_level", "NONE",        0),

        # role 维度
        ("role", "normal_agent",   0),
        ("role", "file_agent",     0),
        ("role", "admin",        -10),
    ]

    cursor.executemany(
        """
        INSERT OR IGNORE INTO risk_factors
        (factor_type, factor_value, score)
        VALUES (?, ?, ?)
        """,
        factors
    )
    conn.commit()
    conn.close()
    print("风险因素分数初始化完成") 

def update_resource_policy_conditions():
    print("开始更新资源策略的条件")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE resource_policies
        SET condition = ?
        WHERE resource_id = (SELECT id FROM resources WHERE name = ?)
          AND action = ?
        """,
        ('{"role": "file_agent"}', 'customer_records.txt', 'read')
    )

    conn.commit()
    conn.close()
    print("资源策略条件更新完成")

def update_timewindow_condition():
    print("设置 test_timewindow.txt 的时间窗条件")
    conn = get_connection()
    cursor = conn.cursor()

    condition = '{"hour_min": 0, "hour_max": 23}'

    for action in ["read", "delete"]:
        cursor.execute(
            """
            UPDATE resource_policies
            SET condition = ?
            WHERE resource_id = (SELECT id FROM resources WHERE name = ?)
              AND action = ?
            """,
            (condition, 'test_timewindow.txt', action)
        )

    conn.commit()
    conn.close()
    print("时间窗条件设置完成")    
    		  

def init_db():
    """初始化数据库：建表 + 灌初始数据。可重复调用。"""
    create_tables()
    create_agent_table()
    create_role_tables()
    create_tools_table()
    create_resource_policy_table()
    create_audit_logs_table()
    create_approval_requests_table()
    create_risk_factors_table()
    add_result_column_to_approval_requests()
    add_condition_column_to_resource_policies()
    add_status_column_to_audit_logs()
    add_audit_logs_new_columns()   # ← 新增

    clean_resources()
    create_resource_unique_index()

    insert_resources()
    insert_agents()
    insert_roles_and_permissions()
    insert_role_permissions()
    insert_resource_policies()
    insert_tools()
    insert_risk_factors()
    update_resource_policy_conditions()
    update_timewindow_condition()

    print("数据库初始化完成")


if __name__ == "__main__":
    init_db()
