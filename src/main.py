from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from src.agent.llm_agent import LLMAgent
from src.agent.agent_loop import AgentLoop
from src.security.engine import SecurityEngine
from src.tools.executor import execute_tool
from src.security.approval_repository import (
    list_pending_approvals,
    get_approval_request,
    update_approval_status,
    save_approval_result,
)
from src.security.authentication import authenticate
from src.security.authorization import get_agent_role
from src.audit.logger import log_event

app = FastAPI()

def _require_admin(api_key: str | None) -> str:
    """验证请求者是不是管理员。返回 agent_id 或抛 HTTPException。"""
    
    # ① 没带 Key → 401
    if api_key is None:
        raise HTTPException(status_code=401, detail="缺少 API Key")
    
    # ② Key 无效 → 401
    agent = authenticate(api_key)
    if agent is None:
        raise HTTPException(status_code=401, detail="无效的 API Key")
    
    # ③ 不是管理员 → 记审计 + 403
    if get_agent_role(agent) != "admin":
        log_event(
            agent, "approval_access", {},
            allowed=False,
            reason="越权访问审批接口",
            error_code="FORBIDDEN",
            status="DENIED",
        )
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    # ④ 都通过 → 返回 agent_id
    return agent

security_engine = SecurityEngine()
llm_agent = LLMAgent()
agent_loop = AgentLoop(llm_agent, security_engine)


class UserMessage(BaseModel):
    message: str
    api_key: str


class ApprovalAction(BaseModel):
    action: str
    reject_reason: str | None = None


@app.post("/chat")
def chat(data: UserMessage):
    return agent_loop.run(data.message, data.api_key)


@app.get("/approvals")
def list_approvals(x_api_key: str | None = Header(default=None)):
    _require_admin(x_api_key)
    return {"pending": list_pending_approvals()}


@app.post("/approve/{approval_id}")
def approve_request(
    approval_id: int,
    action_data: ApprovalAction,
    x_api_key: str | None = Header(default=None),
):
    agent = _require_admin(x_api_key)

    if action_data.action not in ("APPROVED", "REJECTED"):
        raise HTTPException(
            status_code=422,
            detail="action 必须是 APPROVED 或 REJECTED"
        )

    request_info = get_approval_request(approval_id)
    if request_info is None:
        raise HTTPException(status_code=404, detail="审批请求不存在")

    update_approval_status(
        approval_id=approval_id,
        status=action_data.action,
        reviewer=agent,
        reject_reason=action_data.reject_reason,
    )

    return {
        "status": "success",
        "message": f"审批请求{approval_id}已{action_data.action}",
        "reviewer": agent,
    }

@app.get("/result/{approval_id}")
def get_result(
    approval_id: int,
    x_api_key: str | None = Header(default=None),
):
    # ① 没带 Key → 401
    if x_api_key is None:
        raise HTTPException(status_code=401, detail="缺少 API Key")

    # ② Key 无效 → 401
    agent = authenticate(x_api_key)
    if agent is None:
        raise HTTPException(status_code=401, detail="无效的 API Key")

    # ③ 记录不存在 → 404
    request_info = get_approval_request(approval_id)
    if request_info is None:
        raise HTTPException(status_code=404, detail="审批请求不存在")

    # ④ 不是本人也不是 admin → 403 + 记审计
    if agent != request_info["agent_id"] and get_agent_role(agent) != "admin":
        log_event(
            agent, "result_access",
            {"approval_id": approval_id},
            allowed=False,
            reason="越权查看他人审批",
            error_code="FORBIDDEN",
            status="DENIED",
        )
        raise HTTPException(status_code=403, detail="无权查看此审批")

    # ⑤ 原有逻辑不变
    if request_info["status"] == "PENDING":
        return {
            "status": "PENDING",
            "message": "审批还在进行中，请等待管理员处理"
        }

    if request_info["status"] == "REJECTED":
        return {
            "status": "REJECTED",
            "message": "审批被拒绝",
            "reject_reason": request_info["reject_reason"],
            "reviewer": request_info["reviewer"],
        }

    if request_info["status"] == "APPROVED":
        if request_info["result"] is not None:
            return {
                "status": "APPROVED",
                "message": "审批通过，工具已执行（缓存结果）",
                "result": request_info["result"],
            }

        result = execute_tool(
            request_info["tool_name"],
            request_info["arguments"],
        )
        result_str = str(result)
        save_approval_result(approval_id, result_str)

        return {
            "status": "APPROVED",
            "message": "审批通过，工具已执行",
            "result": result_str,
        }