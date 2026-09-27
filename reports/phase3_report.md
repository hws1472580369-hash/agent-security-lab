# Phase 3 阶段总结报告

**项目名称**：Agent Security Lab
**当前阶段**：Phase 3 — Security Engine 完善
**报告时间**：2026-09-17

---

## 一、Phase 3 的目标

Phase 3 的核心目标（来自最初的路线图）：

> Security Engine 完善：动态规则、更复杂 Policy、风险评分

Phase 2 结束时，系统已经具备：

- Authentication / Authorization / Policy
- SQLite 数据库驱动
- Real Tool（真实文件读写）
- Schema 校验

但存在明显不足：

- 没有真正的"人工审批"机制
- 风险判断只是查表，不支持多维度
- Policy 只能表达"资源+动作→允许/拒绝"，不支持条件
- 没有基于历史行为的动态判断
- 没有执行层的安全防线

Phase 3 就是来解决这些问题的。

---

## 二、Phase 3 完成的功能清单

| # | 功能 | 目标 |
|---|---|---|
| 1 | 审计日志结构化 | 从纯文本到 SQLite 表 |
| 2 | 真正的审批流（HITL） | 从"假拒绝"到"真挂起" |
| 3 | 结果缓存（幂等性） | 避免重复执行工具 |
| 4 | 风险评分引擎 | 从"查表"到"加权算分" |
| 5 | 更复杂 Policy（条件） | 支持角色、时间等条件 |
| 6 | 动态规则 | 基于历史行为调整风险 |
| 7 | 架构重构（Policy/Risk 分离） | 决策职责集中 |
| 8 | 路径隔离 | 执行层的纵深防御 |
| 9 | 频率限制 | 防高频轰炸 |
| 10 | 时间窗条件 | Policy 条件扩展 |

---

## 三、详细说明

### 3.1 审计日志结构化

**改动前**：`logger.py` 往 `audit.log` 写纯文本。

**改动后**：写进 `audit_logs` 表。

**表结构**：

```sql
CREATE TABLE audit_logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    agent_id TEXT,
    tool_name TEXT,
    arguments TEXT,
    allowed INTEGER NOT NULL,
    reason TEXT,
    error_code TEXT,
    status TEXT
)
```

**新增字段**：

- `error_code`：机器可读的错误码
- `status`：区分 `ALLOWED` / `PENDING` / `DENIED`

**意义**：

- 从"人读"变成"机器可查"
- 为动态规则、频率限制提供数据基础

### 3.2 真正的审批流（HITL）

**改动前**：MEDIUM 风险直接拒绝，"需要人工审批"是句空话。

**改动后**：完整的异步审批闭环。

**新增表**：`approval_requests`

```sql
CREATE TABLE approval_requests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    reviewer TEXT,
    reviewed_at TEXT,
    reject_reason TEXT,
    result TEXT
)
```

**新增接口**：

| 接口 | 谁用 | 干什么 |
|---|---|---|
| `GET /approvals` | 管理员 | 查看待审批列表 |
| `POST /approve/{id}` | 管理员 | 批准或拒绝 |
| `GET /result/{id}` | Agent | 查询审批结果 |

**审批流程**：

```
Agent 发请求 → MEDIUM → PENDING → 写审批表
    ↓
管理员审批 → APPROVED / REJECTED
    ↓
Agent 查结果 → 执行工具 或 返回拒绝理由
```

### 3.3 结果缓存（幂等性）

**问题**：Agent 反复查 `/result/{id}`，工具被反复执行。对 `delete_file` 是灾难。

**解决**：第一次执行后，把结果存进 `approval_requests.result` 字段。以后查询直接返回缓存。

**效果**：

```
第一次查 /result/5 → 执行工具 → 存缓存 → 返回结果
第二次查 /result/5 → 直接返回缓存（message 带"（缓存结果）"）
```

**术语**：幂等设计（Idempotency）。

### 3.4 风险评分引擎

**改动前**：查 `risk_policies` 表，二维组合（action + resource_level）→ 风险等级。

**改动后**：加权算分。

**新增表**：`risk_factors`

```sql
CREATE TABLE risk_factors(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    factor_type TEXT NOT NULL,
    factor_value TEXT NOT NULL,
    score INTEGER NOT NULL,
    UNIQUE(factor_type, factor_value)
)
```

**分数表**：

| 维度 | 值 | 分 |
|---|---|---|
| action | read | 10 |
| action | delete | 30 |
| action | execute | 20 |
| action | search | 5 |
| resource_level | PUBLIC | 0 |
| resource_level | SENSITIVE | 20 |
| resource_level | SECRET | 60 |
| resource_level | NONE | 0 |
| role | admin | -10 |
| role | normal_agent | 0 |
| role | file_agent | 0 |

**阈值**：

- < 30：LOW → ALLOWED
- 30-49：MEDIUM → PENDING
- >= 50：HIGH → DENIED

**意义**：从"查表"升级为"算分"，可以加更多维度。

**顺带修复的 Bug**：`tools` 表里 calculator 的 action 是 `execute`，但 `risk_policies` 表里写的是 `calculator`，两边不一致导致 500 错误。新方案用统一的值，bug 消失。

### 3.5 更复杂 Policy（条件）

**改动前**：只能表达"资源 + 动作 → 允许/拒绝"。

**改动后**：支持条件。

**新增字段**：`resource_policies.condition`

**例子**：

```json
{"role": "file_agent"}
```

意思是："sensitive.txt 允许 read，但必须 file_agent。"

**新增函数**：`check_condition(condition_str, agent_role)`

**支持的字段**：

| 字段 | 含义 |
|---|---|
| `role` | 角色匹配 |
| `hour_min` | 最小小时（含） |
| `hour_max` | 最大小时（不含） |

**新增错误码**：`CONDITION_NOT_MET`

**意义**：Policy 从"二元判断"升级为"多元判断"。条件用 JSON 存，扩展时不用改表结构。

### 3.6 动态规则

**目标**：某 Agent 最近 5 分钟被拒 3 次 → 风险分 +30。

**新增函数**：`get_history_penalty(agent_id)`

```python
def get_history_penalty(agent_id):
    cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
    # 查 audit_logs：这个 Agent 最近 5 分钟被拒几次
    count = ...
    return 30 if count >= 3 else 0
```

**效果**：

- 正常 Agent 读 sensitive.txt：30 分 → MEDIUM → PENDING
- 被拒 3 次的 Agent 读 sensitive.txt：60 分 → HIGH → DENY

**对应现实**：手机密码锁（错 3 次锁定）、银行反欺诈、Google 异常登录检测。

### 3.7 架构重构（Policy/Risk 分离）

**这是 Phase 3 最重要的改动。**

**问题**：Policy 和 Risk 都在做"拒绝"这件事。

- Policy 用布尔值（allowed 0/1）直接拒绝
- Risk 用分数（>= 50）拒绝

**两个层都在拒绝，谁先跑谁生效。** Policy 在前，拦住了能到 Risk 的场景，导致 Risk 层的 `HIGH_RISK` 分支从来没被执行过。

**修正方向**：参考 PDP/PEP 模式。

**改动后**：

| 层 | 职责 | 输出 |
|---|---|---|
| Policy | 硬边界判断 | `{"passed": bool, "error_code": str, "reason": str}` |
| Risk | 风险评估 | 分数（int） |
| Decision | 统一裁决 | `SecurityDecision` |

**执行顺序**：

```
① 认证 → ② 工具检查 → ③ 鉴权 → ④ Schema
    ↓
⑤ Policy（硬边界，不中断）
    ↓
⑥ Risk（算分，不中断）
    ↓
⑦ Decision（综合裁决）
```

**关键变化**：

- Policy 和 Risk 都跑完，不中断
- 只有 Decision 层输出最终决策
- Policy 拒绝优先于 Risk 分数

**行为兼容性**：四个原有场景行为不变。

### 3.8 路径隔离

**问题**：如果 `file_name` 是 `"../../etc/passwd"`，工具函数会读系统文件。

**解决**：在 `registry.py` 里加路径检查。

```python
BASE_DIR = Path("data").resolve()

def _is_path_safe(file_name):
    try:
        target = (BASE_DIR / file_name).resolve()
        target.relative_to(BASE_DIR)
        return True
    except (ValueError, OSError):
        return False
```

**效果**：

- `public.txt` → 正常读取
- `../etc/passwd` → 路径越界

**术语**：纵深防御（Defense in Depth）。

### 3.9 频率限制

**目标**：某 Agent 1 分钟内请求超过 50 次 → 拒绝。

**新增文件**：`src/security/rate_limiter.py`

**新增错误码**：`RATE_LIMITED`

**插入位置**：认证之后、工具检查之前。

**为什么放这**：能拿到 `agent_id`，且尽早拦截。

### 3.10 时间窗条件

**目标**：Policy 的 condition 支持时间段限制。

**例子**：

```json
{"role": "file_agent", "hour_min": 9, "hour_max": 18}
```

意思是："只有 file_agent 角色，且在 9:00-18:00 之间，才允许执行。"

**实现**：在 `check_condition` 里加时间判断。

---

## 四、架构演进

### Phase 2 → Phase 3 的关键变化

| 维度 | Phase 2 | Phase 3 |
|---|---|---|
| 审计日志 | 纯文本 | SQLite 表 |
| 审批流 | 无（假拒绝） | 完整 HITL |
| 结果缓存 | 无 | 有 |
| 风险评分 | 查表（二维） | 算分（多维） |
| Policy | 布尔判断 | 条件判断 |
| 动态规则 | 无 | 有 |
| 决策逻辑 | Policy/Risk 各自决策 | Decision 统一裁决 |
| 执行层防御 | 无 | 路径隔离 |
| 滥用防护 | 无 | 频率限制 |

### 决策层的核心变化

**改动前**：

```
Policy → 直接输出 SecurityDecision
Risk → 直接输出 SecurityDecision
```

**改动后**：

```
Policy → 输出判断结果（字典）
Risk → 输出分数（int）
Decision → 综合两者，输出 SecurityDecision
```

**这是从"多层决策"到"单点决策"的转变，符合 PDP/PEP 模式。**

---

## 五、测试验证

### 5.1 已验证的场景

| # | 场景 | 预期结果 |
|---|---|---|
| 1 | 认证失败 | `AUTHENTICATION_FAILED` |
| 2 | 鉴权拒绝 | `AUTHORIZATION_DENIED` |
| 3 | 资源禁止 | `RESOURCE_ACCESS_DENIED` |
| 4 | 条件不满足 | `CONDITION_NOT_MET` |
| 5 | 正常放行 | ALLOWED |
| 6 | 中风险挂起 | PENDING |
| 7 | 高风险拒绝 | `HIGH_RISK` |
| 8 | 路径穿越 | 路径越界 |
| 9 | 频率限制 | `RATE_LIMITED` |
| 10 | 时间窗通过/拒绝 | 分别返回 PENDING / `CONDITION_NOT_MET` |
| 11 | 审批流（批准/拒绝） | 返回结果 / 返回拒绝理由 |
| 12 | 结果缓存 | 第二次返回缓存 |

### 5.2 尚未验证的场景

| # | 场景 | 原因 |
|---|---|---|
| 1 | 动态规则完整生效 | 需要"同一 Agent 被拒 3 次后，第 4 次被推成 HIGH"的完整场景 |
| 2 | `TOOL_NOT_FOUND` | `detect_intent` 会先过滤 |
| 3 | `SCHEMA_VALIDATION_FAILED` | FastAPI 先校验 |
| 4 | `POLICY_NOT_FOUND` | 缺数据 |

**详见** `reports/design/phase3_test_matrix.md`。

---

## 六、核心设计模式

| 模式 | 用在哪 |
|---|---|
| Pipeline | engine.py 九步流水线 |
| PDP/PEP | Policy/Risk 提供信息，Decision 统一裁决 |
| Data-Driven | 规则、分数、策略全在数据库 |
| State Machine | approval_requests 三态流转 |
| HITL | MEDIUM 风险挂起等审批 |
| Idempotency | 结果缓存 |
| Default Deny | 找不到规则就拒绝 |
| Defense in Depth | 九层检查 + 路径隔离 |

---

## 七、遗留问题

1. **测试数据污染**：`test_*.txt` 混在生产数据里，没有区分标记
2. **部分错误码测不到**：需要直接调 `engine` 绕过 HTTP 层
3. **缺自动化测试**：所有测试都是手动跑的，没有 pytest
4. **阈值硬编码**：频率限制的 50 次/分钟写死在代码里
5. **Risk 分数没有审计**：`audit_logs` 只记录了最终决策，没记录分数

---

## 八、Phase 3 的核心意义

**Phase 1**：证明了 Agent Tool Calling 可以通过 Security Gateway 进行安全控制。

**Phase 2**：证明了安全配置可以从 Python 硬编码迁移到 SQLite，并通过 RBAC、Resource Policy 和真实 Tool 对实际资源进行访问控制。

**Phase 3**：完成了从"能用的网关"到"完整的 Security Engine"的演进：

- 从"同步决策"到"异步审批"（HITL）
- 从"查表"到"算分"（风险评分）
- 从"布尔判断"到"条件判断"（Policy）
- 从"静态规则"到"动态调整"（动态规则）
- 从"多层决策"到"单点裁决"（架构重构）
- 从"逻辑防御"到"纵深防御"（路径隔离）

---

## 九、下一步规划

| 阶段 | 内容 |
|---|---|
| Phase 4 | 管理系统（可选） |
| Phase 5 | 工程化：Docker + SQLAlchemy + Migration |
| Phase 6+ | 真实 Agent 接入：LangChain / LangGraph / MCP |

**建议优先级**：Phase 5 → Phase 6 → Phase 4

---

## 十、一句话总结

> **Phase 3 的核心工作：把"能用"的系统升级成了"能扛"的系统。**
>
> **六个关键升级：审批流、结果缓存、风险评分、条件策略、架构重构、纵深防御。**
>
