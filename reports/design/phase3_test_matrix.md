# Phase 3 测试矩阵

> 记录系统当前能测什么、不能测什么、缺什么。

---

## 一、已验证的场景

| # | 场景 | 输入 | 预期结果 |
|---|---|---|---|
| 1 | 认证失败 | 错误 api_key | `AUTHENTICATION_FAILED` |
| 2 | 鉴权拒绝 | agent_001 读 public.txt | `AUTHORIZATION_DENIED` |
| 3 | 资源禁止 | agent_002 读 secret.txt | `RESOURCE_ACCESS_DENIED` |
| 4 | 条件不满足 | admin_001 读 sensitive.txt | `CONDITION_NOT_MET` |
| 5 | 正常放行 | agent_002 读 public.txt | ALLOWED |
| 6 | 中风险挂起 | agent_002 读 sensitive.txt | PENDING |
| 7 | 高风险拒绝 | agent_002 删 test_risk.txt | `HIGH_RISK` |
| 8 | 路径穿越 | 读 `../etc/passwd` | 路径越界 |
| 9 | 频率限制 | 快速连发请求 | `RATE_LIMITED` |
| 10 | 时间窗通过 | 读 test_timewindow.txt | PENDING |
| 11 | 时间窗拒绝 | condition 设为 22-23 后读 | `CONDITION_NOT_MET` |
| 12 | 审批流（批准） | PENDING → APPROVED | 返回结果 |
| 13 | 审批流（拒绝） | PENDING → REJECTED | 返回拒绝理由 |
| 14 | 结果缓存 | 二次查 /result | 返回缓存 |

---

## 二、能测但还没测

| # | 场景 | 需要什么 |
|---|---|---|
| 15 | 动态规则完整生效 | 同一 Agent 被拒 3 次后，第 4 次被推成 HIGH |

---

## 三、测不到的场景

| # | 错误码 | 原因 |
|---|---|---|
| 16 | `TOOL_NOT_FOUND` | `detect_intent` 会先过滤掉未知工具 |
| 17 | `SCHEMA_VALIDATION_FAILED` | FastAPI 的 `UserMessage` 会先校验参数 |
| 18 | `RESOURCE_NOT_FOUND` | `detect_intent` 拦住了非常规文件名 |
| 19 | `POLICY_NOT_FOUND` | 缺数据（需要一个"只定义 read 不定义 delete"的资源） |
| 20 | `AGENT_NOT_FOUND` | 理论上不可达（认证已通过） |
| 21 | 工具被禁用 | 缺数据（需要把某个工具的 enabled 改成 0） |

---

## 四、解决方式

测不到的场景，三种处理方式：

| 方式 | 适用 | 例子 |
|---|---|---|
| 加测试数据 | 数据缺失 | `POLICY_NOT_FOUND` |
| 直接调 engine | HTTP 层拦截 | `TOOL_NOT_FOUND`、`SCHEMA_VALIDATION_FAILED` |
| 接受现状 | 防御性代码 | `AGENT_NOT_FOUND` |

---

## 五、测试数据现状

| 资源 | 用途 | condition |
|---|---|---|
| public.txt | 公开文件 | NULL |
| sensitive.txt | 角色条件测试 | `{"role": "file_agent"}` |
| secret.txt | 资源禁止测试 | NULL |
| test_risk.txt | HIGH_RISK 测试 | NULL |
| test_timewindow.txt | 时间窗测试 | `{"hour_min": 0, "hour_max": 23}` |

**Agent**：agent_001、agent_002、admin_001

**问题**：测试数据混在生产数据里，没有明确区分标记。

---

## 六、遗留问题

1. **测试数据污染**：`test_*.txt` 和真实数据混在一起
2. **HTTP 层拦截**：部分错误码只能通过直接调 `engine` 测试
3. **缺自动化测试**：所有测试都是手动跑的，没有 pytest
4. **阈值硬编码**：频率限制的 20 次/分钟写死在代码里

---

## 七、后续改进方向

| 方向 | 优先级 |
|---|---|
| 环境隔离（测试库 / 生产库分开） | 高 |
| pytest 自动化测试 | 高 |
| 把阈值改成配置项 | 中 |
| 测试数据加 `is_test` 字段 | 中 |

---

## 八、一句话

> **核心场景已全部验证。剩余测不到的场景，要么缺数据，要么被 HTTP 层拦截，属于已知缺口，不影响当前项目价值。**