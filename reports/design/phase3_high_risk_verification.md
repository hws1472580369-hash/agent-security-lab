# 验证 HIGH_RISK 场景：加测试数据 + 完整测试

> 记录架构重构后，如何用一条测试数据验证 HIGH_RISK 场景真正能触发。
> 这是 Phase 3 架构重构成功的关键证据。

---

## 一、背景

### 1.1 之前的困境

架构重构前：

- 所有能到 Risk 层 HIGH 分的场景，都被 Policy 层提前拦截
- `risk_factors` 表里的 `SECRET=60` 从来没生效过
- 动态规则加的分没机会被用上

**表现**：想测"高风险请求被 Risk 拒绝"，找不到能到 Risk 层的场景。

### 1.2 架构重构

完成的架构改动：

- Policy 只做硬边界判断（资源+动作+条件）
- Risk 只算分，不做拒绝
- Decision 综合裁决

**重构完成后**，理论上能测 HIGH_RISK 了。

**但**：现有数据里，所有能到 50 分的场景还是被 Policy 拦。

### 1.3 缺什么

需要一个"**Policy 通过 + Risk 分数 >= 50**"的场景。

---

## 二、加测试数据

### 2.1 设计思路

**原则**：只加最少的数据，把 HIGH_RISK 打通，不要污染其他场景。

**关键点**：

- 新资源，Policy 对它的操作**全部放行**
- 让 Risk 层有机会真正做决策
- 资源等级用 SENSITIVE（基础分不会太低，也不至于像 SECRET 那样直接到 90 分）

### 2.2 加什么

**新增资源**：

| 字段 | 值 |
|---|---|
| name | `test_risk.txt` |
| type | `file` |
| level | `SENSITIVE` |

**新增策略**：

| 动作 | allowed | condition |
|---|---|---|
| read | 1 | NULL |
| delete | 1 | NULL |

**为什么 read 和 delete 都放行**：

- read：验证中等风险（30 分 → MEDIUM → PENDING）
- delete：验证高风险（50 分 → HIGH → DENY）
- 两个场景一次覆盖

### 2.3 改动位置

**文件**：`src/database/models.py`

**改动 1**：`insert_resources()` 加一行

```python
resources = [
    ("public.txt", "file", "PUBLIC"),
    ("sensitive.txt", "file", "SENSITIVE"),
    ("secret.txt", "file", "SECRET"),
    ("test_risk.txt", "file", "SENSITIVE")   # 新增
]
```

**改动 2**：`insert_resource_policies()` 加两行

```python
policies = [
    ("public.txt", "read", 1),
    ("public.txt", "delete", 1),
    ("sensitive.txt", "read", 1),
    ("sensitive.txt", "delete", 0),
    ("secret.txt", "read", 0),
    ("secret.txt", "delete", 0),
    ("test_risk.txt", "read", 1),      # 新增
    ("test_risk.txt", "delete", 1)     # 新增
]
```

**跑初始化**：

```bash
python -m src.database.models
```

---

## 三、测试验证

### 3.1 清空历史 PENDING

为了测试环境干净，先把历史 PENDING 全部处理掉：

```powershell
$ids = 4,6,7,8,9,10,11
foreach ($id in $ids) {
    $body = '{"reviewer":"admin_001","action":"APPROVED","reject_reason":null}'
    Invoke-RestMethod -Uri "http://127.0.0.1:8000/approve/$id" -Method Post -ContentType "application/json" -Body $body
    Write-Host "已批准 id=$id"
}
```

---

### 3.2 用例 1：中等风险（read）

**请求**：

```json
{
  "message": "读取 test_risk.txt",
  "a": 0,
  "b": 0,
  "api_key": "key_agent_002"
}
```

**预期逻辑**：

- ① 认证 → agent_002
- ② 工具 → read_file
- ③ 鉴权 → file_agent 有 file.read → 通过
- ④ Schema → 通过
- ⑤ Policy → test_risk.txt 的 read allowed=1 → passed=True
- ⑥ Risk → read(10) + SENSITIVE(20) + file_agent(0) = **30 分**
- ⑦ Decision → Policy 通过 + 分数 30 >= 30 → **PENDING**
- ⑧ 写审批表
- ⑨ 写审计

**实际返回**：

```json
{
  "reply": "风险等级中等，需要人工审批",
  "error_code": null,
  "status": "PENDING",
  "approval_id": 12
}
```

**结论**：✅ 通过。Policy 放行，Risk 算分 30，Decision 正确裁决为 PENDING。

---

### 3.3 用例 2：高风险（delete）

**请求**：

```json
{
  "message": "删除 test_risk.txt",
  "a": 0,
  "b": 0,
  "api_key": "key_agent_002"
}
```

**预期逻辑**：

- ① 认证 → agent_002
- ② 工具 → delete_file
- ③ 鉴权 → file_agent 有 file.delete → 通过
- ④ Schema → 通过
- ⑤ Policy → test_risk.txt 的 delete allowed=1 → passed=True
- ⑥ Risk → delete(30) + SENSITIVE(20) + file_agent(0) = **50 分**
- ⑦ Decision → Policy 通过 + 分数 50 >= 50 → **DENY (HIGH_RISK)**
- ⑧ 不是 PENDING，不写审批表
- ⑨ 写审计

**实际返回**：

```json
{
  "reply": "风险等级过高，拒绝执行",
  "error_code": "HIGH_RISK"
}
```

**结论**：✅ 通过。**这是 HIGH_RISK 第一次被真正触发。**

---

### 3.4 用例 3：动态规则（未测）

**思路**：

1. 用 admin_001 连续 3 次读 sensitive.txt → 每次 `CONDITION_NOT_MET`
2. **立刻**用 admin_001 读 test_risk.txt
3. 预期：
   - 基础分 = read(10) + SENSITIVE(20) + admin(-10) = 20
   - 动态规则 +30 = **50 分**
   - → HIGH_RISK

**为什么用 admin_001**：

- 它会因为 condition 被拒，不污染 agent_002 的历史记录
- 它的基础分比 file_agent 低（-10），能显示动态规则的效果

**状态**：未执行。留待后续验证。

---

## 四、这次验证证明了什么

### 4.1 架构重构成功

**之前的现象**：

- 读 secret.txt → Policy 层拒绝 → `RESOURCE_ACCESS_DENIED`
- 删 sensitive.txt → Policy 层拒绝 → `RESOURCE_ACCESS_DENIED`
- **HIGH_RISK 永远测不到**

**现在的现象**：

- 读 test_risk.txt → Policy 放行 → Risk 算分 30 → PENDING
- 删 test_risk.txt → Policy 放行 → Risk 算分 50 → **HIGH_RISK**

**关键变化**：Risk 层真正参与了最终决策。

### 4.2 "数据驱动"生效

**加这个测试场景只做了两件事**：

1. 加一行资源
2. 加两行策略

**没有改任何代码。**

Policy 自动放行、Risk 自动算分、Decision 自动裁决、审计自动记录。

**这就是架构清晰之后的效果**：加场景 = 加数据。

### 4.3 测试数据设计原则

**只加最少的数据**：

- 不加新 Agent（用现有的 agent_002）
- 不加新工具
- 只加一个资源 + 两条策略

**目标聚焦**：

- 只打通"Policy 通过 + Risk 高分"这一个缺口
- 其他缺口（TOOL_NOT_FOUND、SCHEMA_VALIDATION_FAILED 等）后续单独处理

**数据命名**：

- `test_risk.txt` 明确表示"测试用"
- 后续如果需要区分，可以在 `resources` 表加 `is_test` 字段

---

## 五、遗留问题

1. **用例 3 未测**：动态规则真正影响决策的路径还没完整验证。
2. **其他错误码仍测不到**：`TOOL_NOT_FOUND`、`SCHEMA_VALIDATION_FAILED`、`POLICY_NOT_FOUND` 等需要单独处理。
3. **`RESOURCE_NOT_FOUND`**：需要实测能否通过 HTTP 层触发。
4. **测试数据命名规范**：`test_` 前缀暂时够用，但如果未来加更多测试数据，需要统一命名规范。

---

## 六、下一步

1. **测用例 3**（动态规则）：验证动态规则真正影响决策。
2. **补其他测试场景**：需要 `POLICY_NOT_FOUND` 等错误码的测试数据。
3. **写测试矩阵**：把所有可测场景列成表，明确哪些已测、哪些待测。
4. **清理死代码**：Phase 3 收尾时删掉 `get_risk_level` 和 `make_risk_decision`。

---

## 七、一句话总结

> **加一个资源（`test_risk.txt`）+ 两条策略（read/delete 都放行），**
>
> **就打通了"Policy 通过 + Risk 高分"的场景，**
>
> **第一次真正触发了 `HIGH_RISK`。**
>
> **这证明架构重构成功：数据驱动生效，加场景不用改代码。**