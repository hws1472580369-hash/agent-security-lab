# Phase 3 架构重构：Policy 与 Risk 的职责分离

> 记录一次从"发现问题"到"完成重构"的完整过程。
> 这次重构解决了 Policy 和 Risk 职责重叠的问题，让 Risk 层的所有逻辑真正生效。

---

## 一、问题的发现

### 1.1 起因：测不到 HIGH_RISK

动态规则写完，理论上应该生效：

> 某 Agent 最近 5 分钟被拒 3 次 → 风险分 +30 → 把 MEDIUM 推成 HIGH → 拒绝

测试步骤：

1. 用 admin_001 连续发 3 次读 sensitive.txt 的请求
2. 每次都被 `CONDITION_NOT_MET` 拒绝
3. 第 4 次再发一次，期望变成 `HIGH_RISK`

**结果**：第 4 次还是 `CONDITION_NOT_MET`。

### 1.2 排查过程

**第一层排查**：动态规则本身有没有问题？

```bash
python -c "from src.security.risk import get_history_penalty; print(get_history_penalty('admin_001'))"
# 30
```

函数返回 30，动态规则本身没问题。

**第二层排查**：为什么加了 30 分，决策还是 CONDITION_NOT_MET？

看 `engine.py` 的执行顺序：

```
⑤ Resource Policy
    ↓ 不通过 → 直接返回 CONDITION_NOT_MET
⑥ Risk Assessment（走不到）
```

**关键**：`admin_001` 的角色是 `admin`，但 `sensitive.txt` 的 condition 要求 `file_agent`。

Policy 在第 ⑤ 步就拒绝了。**永远走不到第 ⑥ 步的 Risk。**

动态规则给 Risk 加的分，根本没机会被用上。

### 1.3 更深层的发现

盯着数据表看了一会儿：

| 请求 | Policy 判断 | Risk 判断 |
|---|---|---|
| 读 public.txt | 允许 | 10 分 → LOW |
| 读 sensitive.txt | 允许 | 30 分 → MEDIUM |
| 读 secret.txt | **拒绝** | 70 分 → HIGH（走不到） |
| 删 sensitive.txt | **拒绝** | 50 分 → HIGH（走不到） |

**发现**：Policy 和 Risk 都在做"拒绝"这件事。

- Policy 说："规则不允许"
- Risk 说："风险太高"

两个都在拒绝，谁先跑谁生效。`secret.txt` 和 `delete sensitive.txt` 这两个"本该 HIGH_RISK"的场景，全都被 Policy 提前拦截了。

**这不是数据不够的问题，是架构问题。**

---

## 二、问题的本质

### 2.1 Policy 和 Risk 用相同的输入

| 维度 | Policy | Risk |
|---|---|---|
| 输入 | action + resource | action + resource_level |
| 方式 | 布尔判断（allowed 0/1） | 加权算分 |
| 输出 | 允许 / 拒绝 | 分数 → 等级 |
| 副作用 | 直接做最终决策 | 直接做最终决策 |

**两者都在用"操作 + 资源"判断"能不能做"，只是一个用布尔，一个用分数。**

### 2.2 职责重叠导致的问题

1. **Policy 提前拦截**：所有能触发 HIGH_RISK 的场景都被 Policy 拦住
2. **Risk 层被架空**：`risk_factors` 里的 `SECRET=60` 从来没生效过
3. **动态规则白加**：给 Risk 加的分，走不到 Risk 就没用
4. **测试困难**：想测 HIGH_RISK 找不到能到 Risk 层的场景

### 2.3 为什么会走到这一步

**项目演进历史**：

```
Phase 1：认证 → 鉴权 → Schema → Policy（4 层，职责清晰）
Phase 2.5：在 Policy 后面加了一层 Risk
Phase 3：Risk 改成算分，加了动态规则
```

**问题出在 Phase 2.5**：加 Risk 时，假设"Policy 决定能不能做，Risk 决定多危险"——两者不重叠。

**但实际运行时**：

- Policy 不通过 → 拒绝
- Risk 分数高 → 也拒绝

**两个层都在做拒绝，只是理由不同。**

---

## 三、修正方向的选择

### 3.1 参考工业界的 PDP/PEP 模式

- **PDP（决策点）**：综合所有信息，输出最终决策
- **PEP（执行点）**：拦截请求，执行决策

**核心**：**决策只在一个地方做。** Policy 和 Risk 都是"信息提供者"。

### 3.2 对比四个方向

| 方向 | 描述 | 评价 |
|---|---|---|
| A | Policy 和 Risk 明确分工 | 正确方向，但要明确"不做最终决策" |
| B | 合并 Policy 和 Risk | 短期省事，长期臃肿 |
| C | Policy 决策 + Risk 提供信息 | 最干净，符合 PDP/PEP |
| D | 保持现状 | Risk 层被架空，后续功能难扩展 |

**选择 C。**

### 3.3 关键设计决策

**执行顺序**：**Policy 和 Risk 都跑完，最后 Decision 统一裁决。**

**为什么不让 Policy 拒绝就中断**：

- 如果 Policy 拒绝就中断，Risk 层永远走不到
- 动态规则需要的"历史记录"不够全（Policy 拒绝的记录可能也有价值）
- 多算一次分，性能损失可以忽略

**为什么 Policy 拒绝优先于 Risk 分数**：

- 硬规则不容商量，Policy 拒绝就是最终拒绝
- 但 Risk 仍然要跑（记录下来供审计和动态规则用）

---

## 四、具体改动

### 4.1 五个步骤

| # | 文件 | 改什么 |
|---|---|---|
| 1 | `risk.py` | 新增 `get_risk_score`，返回分数 |
| 2 | 单测 | 验证分数计算正确 |
| 3 | `policy.py` | `check_policy` 返回 `{passed, error_code, reason}` |
| 4 | `decision.py` | 新增 `make_decision`，综合判断 |
| 5 | `engine.py` | Policy 和 Risk 都跑完，再进 Decision |

### 4.2 `risk.py` 新增函数

```python
def get_risk_score(context):
    """
    计算风险分数，返回原始分数（int）。
    不做等级映射，由 Decision 层决定怎么处理。
    """
    score = 0
    score += get_factor_score("action", context.action)
    if context.resource_level is not None:
        score += get_factor_score("resource_level", context.resource_level)
    if context.role is not None:
        score += get_factor_score("role", context.role)
    score += get_history_penalty(context.agent_id)
    return score
```

**关键**：不再调 `score_to_risk_level`，直接返回原始分数。

### 4.3 `policy.py` 改造

**改动前**：返回 `SecurityDecision`（直接做决策）

**改动后**：返回字典，只描述硬边界判断结果

```python
return {
    "passed": True / False,
    "error_code": None / "RESOURCE_ACCESS_DENIED" / ...,
    "reason": "..."
}
```

**关键**：不再构造 `SecurityDecision`，不再 import `SecurityDecision`。

### 4.4 `decision.py` 新增 `make_decision`

```python
def make_decision(policy_result, risk_score):
    # 1. 硬边界拒绝优先
    if not policy_result["passed"]:
        return SecurityDecision(
            decision="DENY",
            allowed=False,
            status="DENIED",
            error_code=policy_result["error_code"],
            reason=policy_result["reason"]
        )

    # 2. 硬边界通过，看风险分
    if risk_score >= 50:
        return SecurityDecision(decision="DENY", status="DENIED", error_code="HIGH_RISK", ...)
    elif risk_score >= 30:
        return SecurityDecision(decision="REQUIRE_APPROVAL", status="PENDING", ...)
    else:
        return SecurityDecision(decision="ALLOW", status="ALLOWED", ...)
```

**关键**：**决策集中在这一层做。** 阈值（50、30）只在这里出现。

### 4.5 `engine.py` 流水线调整

**改动前**：

```
⑤ Policy → 拒绝就中断
⑥ Risk → 拒绝就中断
⑦ make_risk_decision → 直接输出决策
```

**改动后**：

```
⑤ Policy → 跑完，记录 policy_result
⑥ Risk → 跑完，记录 risk_score
⑦ make_decision → 综合两个结果，输出最终决策
```

**关键**：Policy 和 Risk 都"不中断"，所有信息汇总到 Decision 层。

---

## 五、测试验证

### 5.1 行为兼容性测试

四个原有场景，行为**完全不变**：

| 场景 | 改动前 | 改动后 |
|---|---|---|
| 读 public.txt (agent_002) | ALLOW | ALLOW |
| 读 sensitive.txt (agent_002) | PENDING | PENDING |
| 读 secret.txt (agent_002) | RESOURCE_ACCESS_DENIED | RESOURCE_ACCESS_DENIED |
| 读 sensitive.txt (admin_001) | CONDITION_NOT_MET | CONDITION_NOT_MET |

**结论**：架构重构没有破坏原有行为。

### 5.2 新架构带来的变化

**变化 1：Risk 层真正执行**

改动前，读 secret.txt 走不到 Risk。改动后，所有请求都会跑 Risk，分数算出来了（70 分）。

**变化 2：动态规则真正生效**

改动前，admin_001 被拒 3 次加的分用不上。改动后，加上分后能被 Decision 层用上（虽然因为 Policy 拒绝，最终仍是拒绝——但分数确实被计算并被考虑过）。

**变化 3：未来能测到 HIGH_RISK**

只要构造"Policy 通过 + 分数 >= 50"的场景，就能触发 HIGH_RISK。

---

## 六、反思与收获

### 6.1 技术收获

**1. 分层防御的前提是"职责不重叠"**

之前以为"分层防御 = 每一层独立判断"。现在明白：**分层的意义在于每层回答不同的问题**。如果两层回答同一个问题，就是冗余。

**2. 决策应该集中，评估应该分散**

- 决策集中：只有一个地方输出最终决策，方便维护和调试
- 评估分散：各种检查独立，方便扩展和测试

**3. 接口隔离降低改动成本**

因为 `SecurityDecision` 的格式没变，所以：

- `main.py` 不用改
- `logger.py` 不用改
- `approval_repository.py` 不用改
- 只有核心三个文件（`policy.py`、`risk.py`、`decision.py`）和 `engine.py` 要改

**4. 单测是重构的安全网**

每改一个文件就跑一次单测，确认函数行为正确。**五步改动每一步都验证，避免"改到最后发现前面错了"。**

### 6.2 方法论收获

**1. 加功能前先看架构**

加新功能前问三个问题：

- 这个功能属于哪一层？
- 它和现有层的关系是什么？
- 会不会和现有层职责重叠？

**2. "测试数据不够"可能是"架构问题"的表象**

发现"测不到 HIGH_RISK"时，第一反应是"数据不够"。后来发现，**是架构导致的"走不到 Risk"**。

**以后遇到"某个场景测不到"，先假设是架构问题，再看是不是真的缺数据。**

**3. 架构问题越早发现，改动成本越低**

如果一直拖着，后面加路径隔离、频率限制时，问题会叠加。**早发现、早改，是最省成本的做法。**

### 6.3 一个观察

**"只顾着加功能，忘了看架构"是所有工程师都会犯的错。**

区别在于：

- 有的人一直加功能，最后项目变成一团乱麻
- 有的人中途停下来，反思架构，重新设计

**这次的中途停下来，是项目从"能跑"到"能扩展"的转折点。**

---

## 七、遗留问题

1. **死代码还没清理**：`get_risk_level` 和 `make_risk_decision` 两个旧函数还在文件里，等整个 Phase 3 收尾时一起清。
2. **测试数据还不够**：虽然架构改好了，但"Policy 通过 + 分数 >= 50"的场景还没有测试数据，需要后续扩充。
3. **Risk 分数没有被审计记录**：现在 `audit_logs` 只记录了最终决策，没记录 Risk 算出的分数。以后可以加一个字段记录分数，方便排查。

---

## 八、一句话总结

> **这次重构的本质：把"决策"从多个层收拢到一个层。**
>
> **Policy 从"决策者"降级为"信息提供者"**
> **Risk 从"决策者"降级为"信息提供者"**
> **Decision 从"映射器"升级为"唯一决策者"**
>
> **行为兼容，架构清晰，未来可扩展。**