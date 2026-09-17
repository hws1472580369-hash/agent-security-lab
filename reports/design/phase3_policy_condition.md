# Policy 条件检查设计（Phase 3）

## 1. 现状问题

之前的 `resource_policies` 表只能表达"资源 + 动作 → 允许/拒绝"。

比如：

- sensitive.txt → read → 允许
- sensitive.txt → delete → 拒绝

**问题**：不能表达"谁来执行"。

比如"只有 file_agent 能读 sensitive.txt"——这种"带条件的策略"就做不到。

## 2. 设计方案

给 `resource_policies` 表加一个 `condition` 字段（TEXT 类型），存 JSON 格式的条件。

**例子**：

| 资源 | 动作 | 允许 | 条件 |
|---|---|---|---|
| sensitive.txt | read | 1 | `{"role": "file_agent"}` |

意思是："sensitive.txt 允许 read，但必须 file_agent。"

**为什么用 JSON**：

- 字段不固定，随时可以加新条件（时间、频率、IP）
- 不用改表结构
- 解析灵活

## 3. 支持的条件类型（当前）

| 键 | 含义 | 例子 |
|---|---|---|
| `role` | 只有这个角色匹配 | `{"role": "file_agent"}` |

**匹配规则**：

- 所有键必须同时满足
- 缺省键 = 不限制
- 空 JSON 或 NULL = 无条件

## 4. 表结构

```sql
ALTER TABLE resource_policies ADD COLUMN condition TEXT;
```

**示例数据**：

```sql
UPDATE resource_policies
SET condition = '{"role": "file_agent"}'
WHERE resource_id = (SELECT id FROM resources WHERE name = 'sensitive.txt')
  AND action = 'read';
```

## 5. 代码改动

### 5.1 `models.py`

新增 `add_condition_column_to_resource_policies()`：幂等地给表加字段。

新增 `update_resource_policy_conditions()`：给 sensitive.txt 的 read 策略加条件。

### 5.2 `policy.py`

新增 `check_condition(condition_str, agent_role)` 函数：

- 输入：JSON 字符串（来自数据库）+ 当前角色
- 输出：True（匹配）/ False（不匹配）

修改 `check_policy`：

- 签名加了 `agent_role` 参数
- SQL 多查一列 `condition`
- 匹配到策略后，先检查 condition，通过才放行

新增错误码：`CONDITION_NOT_MET`。

### 5.3 `engine.py`

把 `role = get_agent_role(agent_id)` 从第 ⑥ 步提前到第 ⑤ 步之前。

`check_policy` 调用时多传一个 `role`。

## 6. 测试结果

| 场景 | Agent | 角色 | 结果 |
|---|---|---|---|
| 读 sensitive.txt | agent_002 | file_agent | PENDING（条件满足） |
| 读 sensitive.txt | admin_001 | admin | CONDITION_NOT_MET（条件不满足） |
| 读 public.txt | agent_002 | file_agent | ALLOW（无条件） |

**三条路径全部符合预期。**

## 7. 与真实产品的对应

**Policy 从"硬规则"升级为"带条件的规则"**，对应真实产品：

- **OPA（Open Policy Agent）**：用 Rego 语言写条件策略
- **AWS Cedar**：用 Cedar 语言写策略
- **Kubernetes 准入控制器**：支持条件判断

我们的 JSON 条件是这些工业级策略语言的**最简实现**。

## 8. 遗留问题

- 当前只支持 `role` 条件。未来可加：`hour_min` / `hour_max`（时间段）、`agent_id`（特定 Agent）、`frequency`（频率）
- condition 里的 JSON 解析失败时返回 False（拒绝）——这是安全的默认值，但日志里没记录"解析失败"的具体原因，排查时不方便
- 没有对 condition 做 schema 校验。管理员配置时写错键名（比如 `role` 写成 `rol`），不会报错，只会当成"没有这个条件"

## 9. 下一步

Phase 3 最后一步：**动态规则**。

基于 `audit_logs` 的历史数据调整风险，比如：

- 某 Agent 过去 5 分钟被拒 3 次 → 提升风险等级
- 凌晨 2 点调 delete_file → 直接拒绝