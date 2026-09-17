# 动态规则设计（Phase 3）

## 1. 目标

风险评分从"只看当前请求"升级为"结合历史行为"。

## 2. 核心思想

如果某个 Agent 最近频繁被拒绝，说明它在试探边界，应该提升后续请求的风险等级。

## 3. 参数

| 参数 | 值 | 说明 |
|---|---|---|
| 统计窗口 | 5 分钟 | 只看最近 5 分钟 |
| 触发阈值 | 3 次 | 被拒 3 次以上触发惩罚 |
| 惩罚分数 | 30 分 | 一次性加分，不累加 |

## 4. 数据来源

`audit_logs` 表：

```sql
SELECT COUNT(*) FROM audit_logs
WHERE agent_id = ?
  AND allowed = 0
  AND timestamp >= ?  -- 5 分钟前
```

## 5. 评分逻辑

```
score = action分 + resource_level分 + role分 + 历史惩罚分
```

历史惩罚分：
- 被拒次数 < 3 → 0
- 被拒次数 >= 3 → 30

## 6. 场景验证

| 场景 | 历史被拒 | 惩罚 | 结果 |
|---|---|---|---|
| 正常请求 | 0 次 | 0 | 分数不变 |
| 试探 3 次后 | 3 次 | +30 | MEDIUM → HIGH |
| 停止 6 分钟后 | 0 次 | 0 | 恢复 |

## 7. 代码改动

### 7.1 risk.py 新增

```python
def get_history_penalty(agent_id: str) -> int:
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) FROM audit_logs
        WHERE agent_id = ? AND allowed = 0 AND timestamp >= ?
        """,
        (agent_id, cutoff)
    )
    count = cursor.fetchone()[0]
    conn.close()
    
    return 30 if count >= 3 else 0
```

### 7.2 get_risk_level 修改

```python
def get_risk_level(context):
    score = 0
    score += get_factor_score("action", context.action)
    if context.resource_level is not None:
        score += get_factor_score("resource_level", context.resource_level)
    if context.role is not None:
        score += get_factor_score("role", context.role)
    
    score += get_history_penalty(context.agent_id)
    
    return score_to_risk_level(score)
```

## 8. 设计理由

- 用 `audit_logs` 而不是新建表：已有完整历史数据
- 惩罚一次性，不累加：被拒 3 次和 10 次风险一样
- 5 分钟窗口：兼顾"抓住试探"和"避免误判"
- ISO 字符串比较：字典序 = 时间序，无需转换

## 9. 边界情况

- 从未被拒 → 0 分
- 被拒 100 次 → 还是 30 分
- 误拒也算 → 宁可误杀，不可漏放

## 10. 遗留问题

- 参数硬编码（5 分钟 / 3 次 / 30 分），未来可数据化
- 没有给 `audit_logs` 加索引，数据量大时会慢
- 没有区分"被拒原因"，所有拒绝都算

## 11. 与真实产品的对应

对应真实风控系统：

- 银行反欺诈：基于用户近期行为调整交易风险
- Google 异常登录：多次失败登录 → 锁定账号
- AWS GuardDuty：基于历史行为检测异常

这是"行为分析"（Behavior Analytics）的简化实现。