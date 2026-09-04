# 资源级安全策略实验

## 1. 实验目的

验证 Agent 在拥有 Tool 使用权限的情况下，是否仍然受到资源级安全策略的限制。

本实验重点验证：

> **Tool Permission 不等于 Resource Permission。**

也就是说：

* Agent 拥有 `file.read` 权限，只代表 Agent **有能力使用文件读取 Tool**；
* 并不代表 Agent 可以读取系统中的任意文件；
* 对具体资源执行具体操作时，还需要经过资源级安全策略检查。

本实验用于验证 Phase 2 中新增的 **Resource Policy** 是否能够进一步限制 Agent 的实际资源访问行为。

---

## 2. 实验场景

### 2.1 Agent 信息

* Agent ID：`agent_002`
* Role：`file_agent`
* 状态：`active`

### 2.2 Agent 权限

`file_agent` 角色拥有：

```text
search.use
calculator.use
file.read
file.delete
```

因此：

```text
agent_002
    ↓
file_agent
    ↓
file.read
```

说明 `agent_002` **具备使用 `read_file` Tool 的权限**。

---

## 3. 测试请求

Agent 发起请求：

```text
读取 secret.txt
```

系统解析请求后得到：

```text
Agent = agent_002
Intent = read_file
Resource = secret.txt
Action = read
```

因此，本次请求可以抽象为：

```text
Agent
  ↓
agent_002
  ↓
read_file
  ↓
secret.txt
  ↓
read
```

---

## 4. 资源级安全策略

当前数据库中的 `resource_policies` 配置如下：

| 文件              |  read | delete |
| --------------- | ----: | -----: |
| `public.txt`    | ALLOW |  ALLOW |
| `sensitive.txt` | ALLOW |   DENY |
| `secret.txt`    |  DENY |   DENY |

因此：

```text
secret.txt
    ↓
read = DENY
delete = DENY
```

虽然 `agent_002` 拥有：

```text
file.read
```

但资源策略明确规定：

```text
secret.txt + read = DENY
```

---

## 5. 安全检查过程

本次请求进入安全网关后，依次经过以下检查。

### 第一步：Authentication

系统首先根据 API Key 查找 Agent：

```text
api_key
    ↓
agents
    ↓
agent_002
```

认证成功。

---

### 第二步：Authorization

系统查询 `agent_002` 对应的 Role：

```text
agent_002
    ↓
file_agent
```

然后查询该 Role 所拥有的 Permission：

```text
file_agent
    ↓
file.read
```

当前 Tool：

```text
read_file
```

所要求的 Permission：

```text
file.read
```

因此：

```text
file.read ∈ agent_002 permissions
```

Authorization 检查通过。

---

### 第三步：Schema Validation

系统检查请求参数：

```python
{
    "file_name": "secret.txt"
}
```

参数符合 `read_file` Tool 的 Schema，因此 Schema Validation 通过。

---

### 第四步：Resource Policy Check

此时系统进一步检查：

```text
resource = secret.txt
action   = read
```

系统通过数据库查询：

```text
resources
    ↓
secret.txt
    ↓
resource_policies
    ↓
read = DENY
```

因此资源级策略检查失败。

系统生成：

```text
allowed = False
error_code = RESOURCE_ACCESS_DENIED
```

---

## 6. 最终安全决策

最终安全决策为：

```text
DENY
```

原因：

```text
agent_002
拥有 file.read
        ↓
可以使用 read_file Tool
        ↓
但是
        ↓
secret.txt 的 read 策略 = DENY
        ↓
最终拒绝访问
```

---

## 7. 实际执行结果

API 返回：

```json
{
    "reply": "不允许对资源 secret.txt 执行 read 操作",
    "error_code": "RESOURCE_ACCESS_DENIED"
}
```

可以看到：

* Agent 身份合法；
* Agent 拥有 `file.read` 权限；
* Tool 存在；
* 参数合法；
* 但是资源策略拒绝了本次操作。

因此，**Tool Executor 没有继续执行实际的文件读取操作**。

也就是说：

```text
Security Check
      ↓
    DENY
      ↓
   Executor
      ↓
  不执行 Tool
```

---

## 8. 审计日志

本次拒绝请求同时被记录到 Audit Log。

日志记录包含：

```text
agent = agent_002
tool = read_file
arguments = {'file_name': 'secret.txt'}
allowed = False
reason = 不允许对资源 secret.txt 执行 read 操作
```

因此系统不仅能够阻止非法资源访问，还能够记录：

> **谁、什么时候、调用了什么 Tool、访问了什么资源，以及为什么被拒绝。**

---

## 9. 实验结果

| 检查项目                  | 结果           |
| --------------------- | ------------ |
| Agent Authentication  | PASS         |
| Agent Authorization   | PASS         |
| Tool Registry Check   | PASS         |
| Schema Validation     | PASS         |
| Resource Policy Check | **DENY**     |
| Tool Execution        | NOT EXECUTED |
| Audit Logging         | PASS         |
| 最终结果                  | **DENY**     |

---

## 10. 实验结论

实验结果表明，Agent 即使拥有 `file.read` Tool Permission，也不能因此获得对所有文件资源的无限制访问能力。

本实验成功验证了：

$$
Tool\ Permission \neq Resource\ Permission
$$

更准确地说：

$$
最终允许
=
Tool\ Permission
\land
Resource\ Policy
$$

只有同时满足：

```text
Agent 有权限使用 Tool
        AND
当前资源允许执行该操作
```

系统才允许 Tool Executor 执行真实操作。

本实验说明，单纯依靠 RBAC Permission 无法解决 Agent 对具体资源的细粒度访问控制问题。

因此，在 Phase 2 中引入：

```text
Resource
    +
Resource Policy
```

可以进一步实现：

> **从“Agent 能不能使用 Tool”扩展到“Agent 能不能对某个具体资源执行某个具体操作”。**

这也是 Agent Security Framework 从基础 Tool Permission 控制向 **资源级安全控制** 演进的重要一步。

---

## 11. Phase 2 的安全意义

Phase 1 中，系统主要回答：

> **“这个 Agent 能不能使用这个 Tool？”**

Phase 2 进一步回答：

> **“即使 Agent 能使用这个 Tool，它现在能不能对这个具体资源执行这个具体操作？”**

因此安全控制从：

```text
Agent
  ↓
Tool Permission
  ↓
ALLOW / DENY
```

进一步发展为：

```text
Agent
  ↓
Tool Permission
  ↓
Tool
  ↓
Resource
  ↓
Action
  ↓
Resource Policy
  ↓
ALLOW / DENY
```

这使系统具备了更细粒度的 Agent 资源访问控制能力。
