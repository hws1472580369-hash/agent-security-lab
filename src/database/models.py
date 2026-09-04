from src.database.database import get_connection


# =========================
# 创建基础表
# =========================

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


# =========================
# Agent 表
# =========================

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

    # 兼容旧数据库
    cursor.execute("PRAGMA table_info(agents)")

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

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


# =========================
# Role / Permission 表
# =========================

def create_role_tables():

    print("开始创建角色和权限表")

    conn = get_connection()
    cursor = conn.cursor()


    # 角色表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS roles(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
    )


    # 权限表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS permissions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
        """
    )


    # 角色-权限关系表
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS role_permissions(
            role_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,

            PRIMARY KEY(role_id, permission_id),

            FOREIGN KEY(role_id)
            REFERENCES roles(id),

            FOREIGN KEY(permission_id)
            REFERENCES permissions(id)
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

            FOREIGN KEY(resource_id)
            REFERENCES resources(id)
        )
        """
    )

    conn.commit()
    conn.close()

    print("资源策略表创建完成")


# =========================
# 清理资源重复
# =========================

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



# =========================
# Resource 唯一约束
# =========================

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



# =========================
# 初始化 Resource
# =========================

def insert_resources():

    print("检查资源数据")


    conn = get_connection()
    cursor = conn.cursor()


    resources = [

        (
            "public.txt",
            "file",
            "PUBLIC"
        ),

        (
            "sensitive.txt",
            "file",
            "SENSITIVE"
        ),

        (
            "secret.txt",
            "file",
            "SECRET"
        )
    ]


    cursor.executemany(
        """
        INSERT OR IGNORE INTO resources
        (name,type,level)

        VALUES(?,?,?)
        """,

        resources
    )


    conn.commit()
    conn.close()


    print("资源数据检查完成")



# =========================
# 初始化 Agent
# =========================

def insert_agents():

    print("开始写入 Agent")


    conn = get_connection()
    cursor = conn.cursor()


    agents = [

        (
            "agent_001",
            "key_agent_001",
            "normal_agent",
            "active"
        ),

        (
            "agent_002",
            "key_agent_002",
            "file_agent",
            "active"
        ),

        (
            "admin_001",
            "key_admin_001",
            "admin",
            "active"
        )

    ]


    cursor.executemany(
        """
        INSERT OR IGNORE INTO agents
        (agent_name,api_key,role,status)

        VALUES(?,?,?,?)
        """,

        agents
    )


    conn.commit()
    conn.close()


    print("Agent 写入完成")



# =========================
# 初始化 Role 和 Permission
# =========================

def insert_roles_and_permissions():

    print("开始初始化角色和权限")


    conn = get_connection()
    cursor = conn.cursor()


    roles = [

        ("normal_agent",),
        ("file_agent",),
        ("admin",)

    ]


    cursor.executemany(
        """
        INSERT OR IGNORE INTO roles(name)
        VALUES(?)
        """,

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
        """
        INSERT OR IGNORE INTO permissions(name)
        VALUES(?)
        """,

        permissions
    )


    conn.commit()
    conn.close()


    print("角色和权限初始化完成")



# =========================
# 初始化 Role-Permission 关系
# =========================

def insert_role_permissions():

    print("开始初始化角色权限关系")


    conn = get_connection()
    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT id,name FROM roles
        """
    )

    roles = {
        row[1]: row[0]
        for row in cursor.fetchall()
    }


    cursor.execute(
        """
        SELECT id,name FROM permissions
        """
    )

    permissions = {
        row[1]: row[0]
        for row in cursor.fetchall()
    }


    relations = [

        ("normal_agent","search.use"),
        ("normal_agent","calculator.use"),


        ("file_agent","search.use"),
        ("file_agent","calculator.use"),
        ("file_agent","file.read"),
        ("file_agent","file.delete"),


        ("admin","search.use"),
        ("admin","calculator.use"),
        ("admin","file.read"),
        ("admin","file.write"),
        ("admin","file.delete")

    ]


    for role,permission in relations:

        cursor.execute(
            """
            INSERT OR IGNORE INTO role_permissions
            (role_id,permission_id)

            VALUES(?,?)
            """,

            (
                roles[role],
                permissions[permission]
            )
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

        ("sensitive.txt", "read", 1),
        ("sensitive.txt", "delete", 0),

        ("secret.txt", "read", 0),
        ("secret.txt", "delete", 0)
    ]

    for resource_name, action, allowed in policies:

        cursor.execute(
            """
            SELECT id
            FROM resources
            WHERE name = ?
            """,
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


# =========================
# 主程序
# =========================

if __name__ == "__main__":


   create_tables()

create_agent_table()

create_role_tables()

create_resource_policy_table()

clean_resources()

create_resource_unique_index()

insert_resources()

insert_agents()

insert_roles_and_permissions()

insert_role_permissions()

insert_resource_policies()

print("数据库初始化完成")