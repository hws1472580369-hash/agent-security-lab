# AGENTS.md

## 项目是什么

Agent Security Lab —— 一个插在 LLM Agent 和真实工具之间的安全网关，对每一次工具调用做独立的确定性安全检查（认证 → 鉴权 → Schema → 资源策略 → 风险 → 决策）。

**核心理念**：LLM 不可信（会被 Prompt 注入诱导），安全必须放在确定性的网关层，而不是 LLM 层。

## 目录结构

- `src/agent/` —— LLM 层（DeepSeek 接入 + 多轮工具调用循环）
- `src/security/` —— 网关核心（九步流水线）
- `src/tools/` —— 工具实现与元数据
- `src/database/` —— SQLite 连接 + 建表 / 种子数据
- `src/audit/` —— 审计日志
- `src/main.py` —— FastAPI 入口
- `data/` —— 资源文件 + 生成的 `security.db`（不提交）
- `reports/` —— 阶段报告
- `tests/` —— pytest

## 怎么跑

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m src.database.models          # 初始化 / 重建数据库
uvicorn src.main:app --reload          # 起服务
pytest tests/ -v                       # 跑测试（16 个）
```

## 验证约定

- 改完代码，先跑 `pytest tests/ -v`，全绿再提交。
- 改了 `models.py` 的种子数据或改了资源文件名后，删掉 `data/security.db` 并重跑 `python -m src.database.models` 重建。

## 注意事项

- `data/security.db` 是运行时生成的，**不要提交**（已 gitignore；若已被跟踪，执行 `git rm --cached data/security.db`）。
- `.env` 存 `DEEPSEEK_API_KEY`，**不要提交**（已 gitignore）。
- 资源文件名保持中性（如 `internal_notes.txt` 而非 `secret.txt`）——文件名本身是 LLM 的语义信号。
- 所有工具调用都必须经过 `SecurityEngine`（默认拒绝），不直接执行工具。
- 报告按 Phase 写进 `reports/`，一个 Phase 一篇。
