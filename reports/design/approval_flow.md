```markdown
# 审批流设计（Phase 3）

## 1. 现状问题

当前 `REQUIRE_APPROVAL` 是“假拒绝”：系统说“需要人工审批”，但直接返回了 allowed=False，没有挂起机制，Tool 也不会在审批通过后执行。

## 2. 表结构

CREATE TABLE approval_requests(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    reviewer TEXT,
    reviewed_at TEXT,
    reject_reason TEXT
);

## 3. 状态流转

创建 → PENDING → APPROVED / REJECTED
                ↓              ↓
           Agent 来取       Agent 来取
           执行 Tool        返回拒绝理由

## 4. 接口设计

- GET /approvals              列出所有 PENDING 请求（管理员用）
- POST /approve/{id}          管理员审批
- GET /result/{id}            Agent 查询审批结果

## 5. 待解决的问题

- 审批通过后，Tool 是立即执行还是等 Agent 来取？
- 审批超时怎么办？
- 多个管理员同时审批同一个请求，怎么防止冲突？