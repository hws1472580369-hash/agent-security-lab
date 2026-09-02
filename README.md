 Agent Security Lab

面向人工智能 Agent 的实验性安全框架。

 1. 项目简介

随着大型语言模型（LLM）逐渐具备调用外部工具、访问文件和操作数据库等能力，AI Agent 不再只是生成文本，而是能够对外部环境产生实际影响。

因此，Agent 的 Tool 调用需要受到安全控制。

本项目旨在设计并实现一个面向 AI Agent 的安全控制框架，在 Agent 请求执行 Tool 时，对其进行身份认证、权限检查、参数验证和安全策略检查，从而降低 Agent 越权操作和危险 Tool 调用的风险。

当前项目处于实验性开发阶段。



2. 当前版本

v0.1.0 — Basic Agent Security Gateway

Phase 1 主要实现了一个基础的 Agent Security Gateway。

当前安全检查流程：

Agent Request
      ↓
Authentication
      ↓
Authorization
      ↓
Schema Validation
      ↓
Policy Check
      ↓
Security Decision
      ↓
Tool Executor
      ↓
Tool
3. Phase 1 已实现功能
Authentication

通过 API Key 对 Agent 进行身份认证。

Authorization

根据 Agent 的 Role 判断其是否具有调用某个 Tool 所需要的权限。

Schema Validation

使用 Pydantic 对 Tool 参数进行结构和类型验证。

Policy Check

对 Tool 的具体操作进行安全策略检查。

当前已经实现文件路径安全检查，用于阻止类似：

../secret.txt

这样的路径穿越操作。

SecurityDecision

使用统一的安全决策对象描述检查结果：

allowed
error_code
reason
Audit Logging

记录 Agent 的安全操作和安全检查结果，用于后续审计和实验分析。

4. 实验结果
Test 1：权限不足
normal_agent
      ↓
delete_file
      ↓
Authorization
      ↓
DENIED

结果：

AUTHORIZATION_DENIED
Test 2：正常 Tool 调用
normal_agent
      ↓
search
      ↓
Security Gateway
      ↓
ALLOW
      ↓
Tool Executor

结果：

搜索成功
Test 3：路径穿越攻击
file_agent
      ↓
delete_file("../secret.txt")
      ↓
Policy Check
      ↓
DENIED

结果：

POLICY_DENIED
5. 项目结构
agent-security-lab/
│
├── data/
│   └── test_data.txt
│
├── src/
│   ├── main.py
│   │
│   ├── security/
│   │   ├── authentication.py
│   │   ├── authorization.py
│   │   └── decision.py
│   │
│   ├── tools/
│   │   ├── registry.py
│   │   └── executor.py
│   │
│   └── audit/
│       └── logger.py
│
├── tests/
├── reports/
├── README.md
├── requirements.txt
└── .gitignore
6. 技术栈
Python
FastAPI
Pydantic
Git
GitHub
7. 后续计划
Phase 2

真实 Tool + SQLite 数据库

计划加入：

File Tool
Database Tool
Search Tool
Read / Write Tool
SQLite 数据库
真实测试数据
Phase 3

Agent Security Attack Simulation

研究：

越权调用
敏感数据访问
Tool 参数攻击
路径穿越
不安全 Tool 调用
Phase 4

Risk Assessment

加入 Agent Tool 调用风险评估机制。

Phase 5

Detection & Monitoring

加入：

Runtime Monitoring
Attack Detection
Security Events
Risk Scoring
Audit Analysis
8. Version History
Version	Description
v0.1.0	Basic Agent Security Gateway
9. Project Goal

最终目标是构建一个具有可扩展性的 Agent Security Framework，为 AI Agent 的 Tool 调用提供统一的安全控制层。

未来计划探索与不同 Agent Framework 的集成，使安全控制能够作为独立的 Middleware / SDK 使用。