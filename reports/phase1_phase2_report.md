# Agent Security Lab

## Phase 1 & Phase 2 阶段总结报告

**项目名称：** Agent Security Lab
**项目方向：** AI Agent Tool Calling Security / Agent Security Framework
**当前阶段：** Phase 2 — Real Tool + SQLite

---

# 一、项目总体目标

Agent Security Lab 的目标，是设计并实现一个面向 AI Agent Tool Calling 场景的安全框架。

当 Agent 可以调用搜索、计算、文件读写等 Tool 时，Agent 的行为已经不再局限于生成文本，而可能进一步访问真实资源、修改数据甚至执行具有实际影响的操作。

因此，本项目不直接信任 Agent 的 Tool Calling 请求，而是在 Agent 与 Tool 之间增加一个 Security Gateway：

```text
Agent
  ↓
Authentication
  ↓
Authorization
  ↓
Tool Registry
  ↓
Schema Validation
  ↓
Resource Policy
  ↓
Security Decision
  ↓
Tool Executor
  ↓
Real Resource
  ↓
Audit
```

项目采用逐阶段演进的方式：

```text
Phase 1
基础安全网关
    ↓
Phase 2
SQLite + RBAC + Resource Policy + Real Tool
    ↓
Phase 3
进一步扩展为可复用的 Agent Security Framework
```

---

# 二、Phase 1：基础 Agent Security Gateway

## 2.1 Phase 1 目标

Phase 1 的主要目标不是建立完整框架，而是验证一个核心思想：

> Agent 请求 Tool 时，不能直接执行，而应该先经过安全检查。

因此首先建立最小安全流水线。

```text
Agent
 ↓
Authentication
 ↓
Authorization
 ↓
Schema
 ↓
Policy
 ↓
Decision
 ↓
Tool
 ↓
Audit
```

---

## 2.2 Tool Calling 基本模型

在项目中，一个 Tool 可以理解为 Agent 可以使用的一种能力。

例如：

```text
calculator
search
read_file
delete_file
```

Agent 发出的请求可以抽象成：

```text
Agent
Intent
Arguments
Resource
```

例如：

```text
Agent:
agent_002

Intent:
read_file

Resource:
public.txt

Arguments:
{
    "file_name": "public.txt"
}
```

Security Gateway 根据这些信息决定：

```text
ALLOW
```

或者：

```text
DENY
```

---

# 三、Phase 1 的主要安全机制

## 3.1 Authentication

Authentication 解决的问题是：

> “你是谁？”

系统通过 API Key 识别 Agent。

例如：

```text
key_agent_002
        ↓
agent_002
```

---

## 3.2 Authorization

Authorization 解决的问题是：

> “你有没有使用这个 Tool 的权限？”

例如：

```text
agent_001
   ↓
normal_agent
   ↓
没有 file.read
   ↓
拒绝 read_file
```

---

## 3.3 Schema Validation

Schema 解决的问题是：

> “Agent 给 Tool 的参数是否合法？”

例如 Calculator：

```python
class CalculatorSchema(BaseModel):
    a: int
    b: int
```

Agent 如果提供：

```text
a = 10
b = 20
```

则参数符合要求。

如果参数类型或者结构不正确，则请求不能继续执行。

---

## 3.4 Policy

Policy 解决：

> “这个具体操作是否允许？”

它与 Authorization 不完全相同。

Authorization 判断：

```text
Agent 能不能使用 Tool？
```

Policy 判断：

```text
这一次具体操作是否允许？
```

---

# 四、Phase 1 的局限

Phase 1 成功证明了安全流水线可以工作，但存在明显问题：

### 1. 安全配置大量写在 Python 中

例如：

```python
AGENTS = {...}
```

以及资源策略：

```python
RESOURCE_POLICIES = {
    "public.txt": {"read": True, "delete": True},
    "sensitive.txt": {"read": True, "delete": False},
    "secret.txt": {"read": False, "delete": False}
}
```

这意味着：

> 修改 Agent、权限或者资源策略，需要修改程序代码。

---

### 2. Tool 还没有真正连接真实资源

Phase 1 更偏向于验证安全流程本身。

因此需要进一步验证：

> 安全系统是否真的能够阻止 Agent 对真实资源进行危险操作？

---

### 3. 缺少结构化安全配置

Agent、Role、Permission、Resource、Policy 之间的关系没有被数据库结构化表达。

因此 Phase 2 的目标开始明确。

---

# 五、Phase 2：Real Tool + SQLite

## 5.1 Phase 2 目标

Phase 2 的核心目标：

> **把安全配置从 Python 硬编码逐渐迁移到 SQLite，并让 Tool 真正操作真实文件资源。**

最终形成：

```text
SQLite
 ↓
Agent / Role / Permission
 ↓
Resource / Resource Policy

Python
 ↓
Tool Registry / Tool Executor
 ↓
Real Tool
```

---

# 六、Phase 2 数据库设计

当前数据库：

```text
data/security.db
```

主要包含六张表：

```text
agents
roles
permissions
role_permissions
resources
resource_policies
```

---

# 七、Agent 与 RBAC 结构

Phase 2 使用 RBAC：

> Role-Based Access Control
> 基于角色的访问控制

关系：

```text
Agent
  ↓
Role
  ↓
Role_Permissions
  ↓
Permission
```

具体结构：

```text
agent_001
    ↓
normal_agent
    ↓
search.use
calculator.use
```

```text
agent_002
    ↓
file_agent
    ↓
search.use
calculator.use
file.read
file.delete
```

```text
admin_001
    ↓
admin
    ↓
search.use
calculator.use
file.read
file.write
file.delete
```

---

# 八、为什么需要 Role

如果直接给每一个 Agent 配置大量 Permission：

```text
agent_001 → permission A
agent_002 → permission A
agent_003 → permission A
...
```

会导致管理困难。

因此引入 Role：

```text
Agent
 ↓
Role
 ↓
Permissions
```

多个 Agent 可以共享同一个 Role。

例如：

```text
file_agent
 ├── search.use
 ├── calculator.use
 ├── file.read
 └── file.delete
```

这样权限配置更加清晰。

---

# 九、Resource 设计

Phase 2 增加：

```text
resources
```

它主要负责描述系统中的资源。

例如：

```text
public.txt
sensitive.txt
secret.txt
```

数据库中可以描述：

```text
name
type
classification
```

例如：

```text
public.txt
file
PUBLIC
```

```text
sensitive.txt
file
SENSITIVE
```

```text
secret.txt
file
SECRET
```

这里需要区分：

> `resources` 负责描述/注册资源。

它并不是最终的访问控制规则。

---

# 十、Resource Policy

真正控制资源操作的是：

```text
resource_policies
```

结构：

```text
resource_id
action
allowed
```

例如：

```text
public.txt
    read    → 1
    delete  → 1
```

```text
sensitive.txt
    read    → 1
    delete  → 0
```

```text
secret.txt
    read    → 0
    delete  → 0
```

因此可以形成：

```text
resources
    ↓
resource_policies
```

其中：

```text
resources
=
“这是什么资源？”

resource_policies
=
“这个资源允许做什么？”
```

---

# 十一、为什么 Tool Registry 没有放进数据库

当前 Tool Registry 仍然位于 Python：

```text
src/tools/registry.py
```

原因是：

> Tool 的安全配置可以数据库化，但 Tool 的实际可执行代码仍然应该由受信任的 Python 程序控制。

也就是说：

```text
数据库
→ Agent
→ Role
→ Permission
→ Resource
→ Policy
→ Security Configuration
```

而：

```text
Python
→ Tool Implementation
→ Executor
```

两者职责不同。

不能简单地把任意 Python 代码放进数据库，然后动态执行。

---

# 十二、Phase 2 完整安全流程

现在一个真实文件请求的流程为：

```text
Agent
 ↓
API Key
 ↓
Authentication
 ↓
agent_002
 ↓
查询 agents
 ↓
Role
 ↓
file_agent
 ↓
Permissions
 ↓
file.read
 ↓
Tool Registry
 ↓
read_file
 ↓
Schema Validation
 ↓
file_name
 ↓
Resource Policy
 ↓
查询 resources
 ↓
查询 resource_policies
 ↓
Security Decision
 ↓
ALLOW / DENY
```

如果允许：

```text
ALLOW
 ↓
Executor
 ↓
真实读取 public.txt
 ↓
返回文件内容
 ↓
Audit
```

如果拒绝：

```text
DENY
 ↓
不执行 Tool
 ↓
返回 error_code
 ↓
Audit
```

---

# 十三、Phase 2 两种核心拒绝

Phase 2 最重要的设计成果之一，是明确区分两种安全拒绝。

## 13.1 AUTHORIZATION_DENIED

表示：

> Agent 根本没有使用这个 Tool 的权限。

例如：

```text
agent_001
 ↓
normal_agent
 ↓
没有 file.read
 ↓
read_file
 ↓
AUTHORIZATION_DENIED
```

即使资源是：

```text
public.txt
```

也不能访问。

---

## 13.2 RESOURCE_ACCESS_DENIED

表示：

> Agent 有使用 Tool 的权限，但具体资源操作不允许。

例如：

```text
agent_002
 ↓
file_agent
 ↓
拥有 file.read
 ↓
read_file
 ↓
secret.txt
 ↓
resource_policy
 ↓
read = 0
 ↓
RESOURCE_ACCESS_DENIED
```

这两个错误代表不同的安全层。

---

# 十四、真实实验结果

## 实验 1：正常读取公开文件

请求：

```text
Agent:
agent_002

Tool:
read_file

Resource:
public.txt
```

结果：

```text
ALLOW
```

并成功返回真实文件内容。

**实验结论：通过。**

---

## 实验 2：读取禁止资源

请求：

```text
agent_002
→ read_file
→ secret.txt
```

结果：

```json
{
    "error_code": "RESOURCE_ACCESS_DENIED"
}
```

说明：

```text
Agent 有 file.read
        ↓
但 secret.txt 禁止 read
        ↓
拒绝
```

**实验结论：通过。**

---

## 实验 3：没有 Tool 权限

请求：

```text
agent_001
→ read_file
→ public.txt
```

结果：

```json
{
    "error_code": "AUTHORIZATION_DENIED"
}
```

说明：

```text
agent_001
 ↓
normal_agent
 ↓
没有 file.read
 ↓
直接拒绝
```

**实验结论：通过。**

---

## 实验 4：删除敏感资源

请求：

```text
agent_002
→ delete_file
→ sensitive.txt
```

结果：

```json
{
    "error_code": "RESOURCE_ACCESS_DENIED"
}
```

说明：

```text
agent_002
拥有 file.delete
        ↓
sensitive.txt
        ↓
delete = 0
        ↓
拒绝
```

**实验结论：通过。**

---

# 十五、Audit Log 实验

系统同时记录安全事件：

```text
agent
tool
arguments
allowed
reason
timestamp
```

例如：

```text
agent=agent_002
tool=read_file
arguments={'file_name': 'secret.txt'}
allowed=False
```

以及：

```text
agent=agent_001
tool=read_file
allowed=False
```

因此系统不仅能够：

```text
ALLOW / DENY
```

还能够回答：

> “系统之前发生了什么安全事件？”

这为后续的安全分析、异常行为检测和审计功能提供基础。

---

# 十六、数据库幂等性

Phase 2 开发过程中发现：

```text
INSERT OR IGNORE
```

本身并不能阻止重复数据。

如果数据库没有：

```text
UNIQUE(resource_id, action)
```

那么相同 Policy 仍然可能被重复插入。

因此最终增加唯一约束/唯一索引：

```text
(resource_id, action)
```

保证：

```text
一个资源 + 一个操作
=
唯一一条 Policy
```

最终数据库初始化可以重复执行，而不会不断产生重复资源策略。

这提高了数据库初始化过程的幂等性。

---

# 十七、Phase 1 → Phase 2 架构变化

| 项目                | Phase 1    | Phase 2   |
| ----------------- | ---------- | --------- |
| Agent 配置          | Python 硬编码 | SQLite    |
| Role              | 基础/硬编码     | SQLite    |
| Permission        | 基础/硬编码     | SQLite    |
| Resource          | Python 配置  | SQLite    |
| Resource Policy   | Python 字典  | SQLite    |
| Tool              | 基础 Tool    | Real Tool |
| 文件访问              | 模拟/基础      | 真实文件      |
| RBAC              | 基础         | 完整数据库关系   |
| Schema            | ✅          | ✅         |
| Security Decision | ✅          | ✅         |
| Audit             | ✅          | ✅         |
| 数据库               | ❌          | SQLite    |
| 幂等初始化             | —          | ✅         |

因此 Phase 2 并不是简单地“增加 SQLite”。

真正的变化是：

> **安全系统开始从一个写死在程序里的 Demo，逐渐变成一个由结构化安全配置驱动的系统。**

---

# 十八、当前项目结构

```text
agent-security-lab/
│
├── data/
│   ├── audit.log
│   ├── public.txt
│   ├── sensitive.txt
│   ├── secret.txt
│   ├── test_data.txt
│   └── security.db
│
├── src/
│   ├── database/
│   │   ├── database.py
│   │   └── models.py
│   │
│   ├── security/
│   │   ├── authentication.py
│   │   ├── authorization.py
│   │   ├── decision.py
│   │   └── policy.py
│   │
│   ├── tools/
│   │   ├── registry.py
│   │   └── executor.py
│   │
│   ├── audit/
│   │   └── logger.py
│   │
│   └── main.py
│
├── tests/
├── reports/
├── README.md
└── requirements.txt
```

---

# 十九、Phase 2 的核心成果

经过 Phase 2，目前系统已经具备：

```text
Authentication        ✅
Authorization / RBAC  ✅
Tool Registry         ✅
Schema Validation     ✅
Resource Policy       ✅
Security Decision     ✅
Real File Tool        ✅
Audit Log             ✅
SQLite                ✅
Idempotent Init       ✅
```

因此，Phase 2 已经达到了预定目标。

---

# 二十、Phase 3 的发展方向

Phase 3 不应该简单地继续增加几个 Tool，而应该开始向：

> **可复用 Agent Security Framework**

发展。

可能的方向包括：

### 1. 标准化 Tool Request

把 Agent 请求统一成：

```json
{
    "agent": "...",
    "tool": "...",
    "arguments": {...},
    "resource": "..."
}
```

让 Security Gateway 与具体 Agent 解耦。

---

### 2. 更细粒度的 Policy

从：

```text
Agent → Resource → Action
```

进一步发展为：

```text
Agent
+
Tool
+
Action
+
Resource
+
Context
```

综合判断风险。

---

### 3. Risk-based Authorization

不再只有：

```text
ALLOW / DENY
```

而可以进一步引入：

```text
LOW RISK
MEDIUM RISK
HIGH RISK
```

根据风险决定：

```text
ALLOW
REQUIRE APPROVAL
DENY
```

---

### 4. Prompt Injection / Tool Abuse

进一步研究：

```text
Prompt Injection
      ↓
Agent 行为改变
      ↓
恶意 Tool Calling
      ↓
Security Gateway
      ↓
阻止危险操作
```

这样项目就从简单的 RBAC/访问控制逐渐进入真正的 **Agent Security** 问题。

---

# 二十一、阶段总结

Phase 1 证明了：

> **Agent Tool Calling 可以通过 Security Gateway 进行安全控制。**

Phase 2 进一步证明：

> **安全配置可以从 Python 硬编码迁移到 SQLite，并通过 RBAC、Resource Policy 和真实 Tool 对实际资源进行访问控制。**

最终形成：

```text
             Agent
               │
               ▼
        Authentication
               │
               ▼
        Authorization
               │
               ▼
         Tool Registry
               │
               ▼
       Schema Validation
               │
               ▼
       Resource Policy
               │
               ▼
        Security Decision
          │           │
        DENY         ALLOW
          │           │
          │           ▼
          │      Tool Executor
          │           │
          │           ▼
          │      Real Resource
          │           │
          └─────┬─────┘
                ▼
              Audit
```

**Phase 2 的核心意义不是“用了 SQLite”，而是完成了从“安全 Demo”到“可配置安全系统”的第一次架构升级。**

后续 Phase 3 将在此基础上继续解决：

> **如何让不同 Agent、不同 Tool、不同资源和不同风险场景，都能够接入同一个安全框架。**
