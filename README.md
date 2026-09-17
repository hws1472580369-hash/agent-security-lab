# Agent Security Lab

一个面向 AI Agent Tool Calling 场景的安全网关，插在 Agent 和真实工具之间，对每一次 Tool Call 做独立的安全检查。

## 为什么需要它

LLM 不可控：会被 Prompt Injection 诱导、会犯错、会被越权诱导。Agent 调用工具时不能直接执行，必须先经过安全检查。

## 架构

Agent (LLM)
↓
Security Gateway
├── Authentication 你是谁
├── Authorization 你角色配用这个工具吗
├── Schema Validation 参数格式对吗
├── Resource Policy 这个资源允许这个动作吗
├── Risk Assessment 这件事多危险
└── Decision ALLOW / PENDING / DENY
↓
Tool Executor → 真实资源
↓
Audit Log

## 核心特性

- **数据驱动**：Agent、Role、Permission、Resource、Policy、Tool Metadata 全部存 SQLite，支持动态配置
- **动态 Schema 校验**：从数据库读取 JSON Schema，运行时生成 Pydantic 模型校验参数
- **RBAC 权限模型**：Agent → Role → Permission 三层结构
- **风险分级**：LOW / MEDIUM / HIGH，对应 ALLOW / REQUIRE_APPROVAL / DENY
- **审计日志**：所有决策（通过或拒绝）结构化落库，支持查询和分析
- **默认拒绝**：没有明确允许的，一律拒绝

## 快速启动

```bash
pip install -r requirements.txt
python -m src.database.models   # 初始化数据库
uvicorn src.main:app --reload

## 测试请求
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "读取 public.txt", "a": 0, "b": 0, "api_key": "key_agent_002"}'

src/
├── security/       安全检查核心
│   ├── engine.py          安全流水线调度
│   ├── authentication.py  身份认证
│   ├── authorization.py   RBAC 鉴权
│   ├── policy.py          资源策略
│   ├── risk.py            风险评估
│   └── decision.py        决策对象
├── tools/          工具层
│   ├── registry.py        工具函数实现
│   ├── repository.py      工具元数据查询
│   └── executor.py        工具执行
├── database/       数据层
│   ├── database.py        连接管理
│   └── models.py          表结构 + 初始化
├── audit/          审计
│   └── logger.py          日志落库
└── main.py         FastAPI 入口

阶段进度
☑ Phase 1：基础安全网关
☑ Phase 2：SQLite + RBAC + Resource Policy + Real Tool
☑ Phase 2.5：Tool Metadata 入库
☑ Phase 3 第 1 步：审计日志结构化
□ Phase 3 第 2 步：真正的审批流（进行中）
□ Phase 3 第 3 步：风险评分引擎
详细报告见 reports/。

文档索引
Phase 1 & 2 阶段总结

Phase 2.5 报告

资源策略测试

