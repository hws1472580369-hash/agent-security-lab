# Agent Security Lab

一个插在 **LLM Agent 与真实工具之间**的安全网关：对每一次工具调用做**独立、确定性**的检查，而不是指望模型自觉。

安全不能放在模型里——模型会被提示注入诱导；它只能放在模型**绕不过去**的地方。

支持两种接入方式，**共用同一套九步安全引擎**：

- **MCP 线（主线）**：通过 MCP 协议（streamable HTTP）接入任意第三方客户端；**凭证从连接层进入，LLM 接触不到钥匙**
- **FastAPI 线**：传统 HTTP 接口，用于本地演示与回归测试

## 为什么需要它

LLM 不可控：会被 Prompt Injection 诱导、会犯错、会被越权诱导。Agent 调用工具时不能直接执行，必须先经过安全检查。

## 架构

```text
Agent (LLM)
      │
      ▼
┌──────────────── Security Gateway ────────────────┐
│  Authentication     你是谁                        │
│  Authorization      你角色能用这个工具吗           │
│  Schema Validation  参数格式对吗                  │
│  Resource Policy    这个资源允许这个动作吗         │
│  Risk Assessment    这件事有多危险                 │
│  Decision           ALLOW / PENDING / DENY       │
└──────────────────────────────────────────────────┘
      │
      ▼
Tool Executor → 真实资源
      │
      ▼
Audit Log
```

## 九步流水线

| # | 步骤 | 判断什么 | 失败错误码 |
| :- | :-- | :-- | :-- |
| 1 | 认证 | 身份是谁（外部已认证则直接采用） | `AUTHENTICATION_FAILED` |
| 1.5 | 限流 | 请求是否过于频繁 | `RATE_LIMITED` |
| 2 | 工具存在 | 工具是否已注册且启用 | `TOOL_NOT_FOUND` |
| 3 | 鉴权 | 该角色的权限清单里有吗 | `AUTHORIZATION_DENIED` |
| 4 | Schema | 参数是否符合定义 | `SCHEMA_VALIDATION_FAILED` |
| 5 | 资源策略 | 该资源 + 该动作是否允许（含条件） | `RESOURCE_ACCESS_DENIED` / `CONDITION_NOT_MET` |
| 6 | 风险评分 | 动作 × 资源等级 × 角色 × 历史行为 | — |
| 7 | 决策 | ≥50 拒绝 / ≥30 待审批 / 其余放行 | `HIGH_RISK` |
| 8 | 执行 | 真正调用工具 | — |
| 9 | 审计 | 写一条结构化记录 | — |

## 核心特性

- **数据驱动**：Agent、Role、Permission、Resource、Policy、Tool Metadata 全部存 SQLite，支持动态配置
- **动态 Schema 校验**：从数据库读取 JSON Schema，运行时生成 Pydantic 模型校验参数
- **RBAC 权限模型**：Agent → Role → Permission 三层结构
- **风险分级**：LOW / MEDIUM / HIGH，对应 ALLOW / REQUIRE_APPROVAL / DENY；同一身份短时间被拒多次会累加风险分（限流 / 熔断）
- **审计日志**：所有决策（通过或拒绝）结构化落库，支持查询和分析
- **默认拒绝**：没有明确允许的，一律拒绝
- **凭证外部化**：钥匙从 HTTP `Authorization` 请求头进入，工具签名里不再有 `api_key`

## 快速开始

### 方式一：MCP 线（Docker，推荐）

```bash
docker compose up --build        # 构建并启动网关，监听 127.0.0.1:8001
```

网关对外暴露 4 个工具：`read_file` / `delete_file` / `calculator` / `search`。

用自带的 MCP 客户端验证一次调用：

```bash
pip install -r requirements-dev.txt
python scripts/mcp_client_test.py --token key_agent_002 --tool read_file --args '{"file_name": "public.txt"}'
```

### 方式二：FastAPI 线（本地）

```bash
pip install -r requirements.txt
python -m src.database.models   # 初始化数据库
uvicorn src.main:app --reload
```

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "读取 public.txt", "api_key": "key_agent_002"}'
```

## 测试

```bash
pip install -r requirements-dev.txt
pytest tests/ -v          # 16 个用例
```

> `passed` 表示“结果符合预期”，**不等于放行**——用例里既有放行断言，也有各类拒绝断言。

## 目录结构

```text
src/
├── agent/          LLM 层
│   ├── llm_agent.py              LLM 接入（DeepSeek）
│   └── agent_loop.py             多轮工具调用循环
├── mcp/
│   └── server.py                 MCP 服务端 + 连接层凭证
├── security/       安全检查核心（九步流水线）
│   ├── engine.py                 流水线调度
│   ├── authentication.py         身份认证
│   ├── authorization.py          RBAC 鉴权
│   ├── policy.py                 资源策略
│   ├── risk.py                   风险评估
│   ├── rate_limiter.py           限流 / 熔断
│   ├── approval_repository.py    审批流
│   └── decision.py               决策对象
├── tools/          工具层
│   ├── registry.py               工具函数实现
│   ├── repository.py             工具元数据查询
│   └── executor.py               工具执行
├── database/       数据层
│   ├── database.py               连接管理
│   └── models.py                 表结构 + 种子数据
├── audit/          审计
│   └── logger.py                 日志落库
├── models/
│   └── request.py                请求模型
└── main.py                       FastAPI 入口
```

## 实验结果

在真实第三方客户端（Cherry Studio + DeepSeek）上做了三轮红队实验，共 **10 个批次、186 条审计记录**，原始数据见 [审计记录](docs/审计记录.md)：

- **干净组 108 条**（批次一~三）：客户端只保留 MCP 工具，验证网关判定是否正确、可解释。
- **真实组 61 条**（批次四~七）：客户端内置工具与联网全部打开，验证“客户端有别的路时会不会绕过网关”。
- **补充实验 17 条**（批次九~十）：删除绕过、正常业务基线。另有 1 批外联测试（数据外泄）刻意 0 条记录。

三条核心结论：

1. **网关判定确定、可解释、有审计**：同一输入永远得到同一结论，五种错误码分别对应不同关卡。
2. **网关只覆盖“经过它”的调用**：本地文件、联网、浏览器、历史会话都在它的视野之外。
3. **绕过不需要模型“背叛”，只需要用户一句明确的话**。

## 阶段进度

- ☑ Phase 1：基础安全网关
- ☑ Phase 2：SQLite + RBAC + Resource Policy + 真实工具
- ☑ Phase 2.5：Tool Metadata 入库
- ☑ Phase 3：Security Engine 完善（审批流 / 风险评分 / 条件策略 / 动态规则 / 纵深防御）
- ☑ Phase 4：LLM 接入 + Prompt 注入红队测试
- ☑ Phase 5：MCP 标准化接入 + 连接层凭证 + 容器化 + 红队评估

## 文档索引

| 文档 | 内容 |
| :-- | :-- |
| [Phase 1 & 2 报告](reports/phase1_phase2_report.md) | 基础网关 + 数据库 |
| [Phase 2.5 报告](reports/Phase2.5_Report.md) | 工具元数据入库 |
| [资源策略测试](reports/resource_policy_test.md) | 资源策略用例 |
| [Phase 3 报告](reports/phase3_report.md) | 安全引擎完善 |
| [Phase 4 报告](reports/phase4_report.md) | LLM 接入 + 注入测试 |
| [Phase 5 报告](reports/phase5_report.md) | MCP 接入 + 红队评估 |
| [项目框架总览](docs/项目框架总览.md) | 架构与两条线 |
| [实验记录表](docs/实验记录表.md) | 干净组矩阵 |
| [审计记录](docs/审计记录.md) | 186 条原始审计 |
| [干净组审计清单](docs/干净组审计清单.md) | 108 条分类统计 |

## 说明

- 仓库中的客户资料、产品话术、制度口径均为**实验用虚构数据**，不涉及真实客户或机构内部信息。
- `scripts/fake_compliance_server.py` 是只回 `OK` 的**演示用假服务**，不是真实合规系统。
- `data/security.db` 为运行时生成，可删掉后执行 `python -m src.database.models` 重建；`.env` 存 `DEEPSEEK_API_KEY`，不提交。

