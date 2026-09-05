
# Agent Security Lab

## Phase 2.5 Report — Security Gateway Refactoring

## 1. Phase 2.5 Overview

Phase 2 完成后，Agent Security Lab 已经具备基于 SQLite 的安全控制能力，包括：

- Authentication
- RBAC Authorization
- Resource Policy
- Schema Validation
- Security Decision
- Real Tool Execution
- Audit Logging

但是在 Phase 2 的实现中，Security Gateway 的核心流程仍然集中在 FastAPI 入口文件 `main.py` 中。

这种设计虽然可以运行，但存在以下问题：

1. 安全逻辑与 API 服务高度耦合；
2. 难以支持不同类型 Agent 接入；
3. 难以进一步扩展为通用 Agent Security Framework。

因此 Phase 2.5 的主要目标是：

> 将 Security Gateway 从业务入口中抽离，形成独立的 Security Engine。


---

# 2. Before Refactoring

Phase 2 原始架构：

```

FastAPI

main.py

|
|
|-- Authentication
|
|-- Authorization
|
|-- Schema Validation
|
|-- Resource Policy
|
|-- Security Decision
|
|-- Audit
|
|-- Tool Execution

```

所有安全流程均由 `main.py` 调用。

存在的问题：

- main.py 职责过多；
- 安全流程无法复用；
- Agent 接入层与安全层没有明确分离。


---

# 3. Phase 2.5 Goal

Phase 2.5 主要完成：

## Security Gateway Modularization


目标架构：

```

Agent / API

```
  |

  ↓
```

main.py

```
  |

  ↓
```

SecurityEngine

```
  |
```

---

Authentication

Authorization

Schema Validation

Resource Policy

Security Decision

Audit

```
  |

  ↓
```

Tool Executor

```
  |

  ↓
```

Real Resource

```


---

# 4. SecurityEngine Design


新增：

```

src/security/engine.py

````


SecurityEngine 负责统一管理安全检查流程。


核心接口：

```python
evaluate(
    tool_name,
    arguments,
    api_key
)
````

输入：

* Tool 名称
* Tool 参数
* Agent API Key

输出：

SecurityDecision：

```python
{
    "allowed": true/false,
    "error_code": "...",
    "reason": "..."
}
```

---

# 5. Security Pipeline

## 5.1 Authentication

作用：

确认 Agent 身份。

流程：

```
API Key

↓

agents table

↓

Agent Identity
```

例如：

```
key_agent_002

↓

agent_002

```

---

## 5.2 Authorization

作用：

确认 Agent 是否拥有 Tool 使用权限。

采用 RBAC：

```
Agent

↓

Role

↓

Permission

↓

Tool Permission
```

例如：

```
agent_002

↓

file_agent

↓

file.read

↓

read_file
```

---

## 5.3 Schema Validation

作用：

验证 Tool 参数是否合法。

例如：

Calculator:

```python
class CalculatorArgs(BaseModel):

    a:int
    b:int

```

非法参数无法进入 Tool。

---

## 5.4 Resource Policy

作用：

进行资源级访问控制。

区别：

Permission:

```
Agent 是否拥有能力
```

Policy:

```
这一次具体资源操作是否允许
```

例如：

```
Agent:

拥有 file.read


但是:

secret.txt

read = false


↓

DENY
```

---

## 5.5 Security Decision

所有安全结果统一返回：

```python
SecurityDecision
```

允许：

```
allowed=True
```

拒绝：

```
allowed=False

error_code=RESOURCE_ACCESS_DENIED
```

---

## 5.6 Audit

记录：

* Agent
* Tool
* Arguments
* Decision
* Reason
* Timestamp

用于后续：

* 安全分析
* 异常检测
* 行为审计

---

# 6. Code Changes

新增：

```
src/security/engine.py
```

修改：

```
src/main.py

src/security/policy.py
```

主要变化：

## main.py

由：

```
负责所有安全流程
```

变为：

```
负责请求处理

↓

调用 SecurityEngine

↓

执行 Tool
```

---

# 7. Testing

Phase 2.5 完成后进行测试：

| Test Case                  | Result |
| -------------------------- | ------ |
| Agent 正常读取 public.txt      | PASS   |
| Agent 读取 secret.txt        | DENY   |
| 无 file.read 权限调用 read_file | DENY   |
| 删除 sensitive.txt           | DENY   |
| Calculator Tool 调用         | PASS   |

测试证明：

SecurityEngine 可以正确接管原有安全流程。

---

# 8. Phase 2.5 Achievement

Phase 2:

> Security Gateway 可以工作。

Phase 2.5:

> Security Gateway 开始成为独立框架组件。

完成后：

```
Agent

↓

SecurityEngine

↓

Tool

↓

Resource
```

为后续 Phase 3：

```
Agent Tool Request Layer
```

以及未来：

* LangChain Agent
* OpenAI Agent
* AutoGen Agent

接入 Security Framework 奠定基础。

---

# 9. Conclusion

Phase 2.5 完成了 Agent Security Lab 的第一次架构升级：

从：

```
Security Demo
```

转变为：

```
Modular Security Framework
```

