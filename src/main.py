from fastapi import FastAPI
from pydantic import BaseModel
from src.security.engine import SecurityEngine
from src.tools.executor import execute_tool
from src.models.request import SecurityRequest
from src.security.approval_repository import (
    list_pending_approvals,
    get_approval_request,
    update_approval_status,
    save_approval_result
)
app = FastAPI()


# Security Gateway
security_engine = SecurityEngine()


# =========================
# 用户请求数据结构
# =========================

class UserMessage(BaseModel):

    message: str

    a: int

    b: int

    api_key: str

class ApprovalAction(BaseModel):
    reviewer: str                    # 审批人，比如 "admin_001"
    action: str                      # "APPROVED" 或 "REJECTED"
    reject_reason: str | None = None # 拒绝理由（只有拒绝时才填）


# =========================
# 模拟 Agent 意图识别
# =========================

def detect_intent(message):

    if "搜索" in message or "查" in message:

        return "search"


    elif "计算" in message:

        return "calculator"


    elif "删除" in message:

        return "delete_file"


    elif "读取" in message or "查看" in message:

        return "read_file"


    else:
        

        return "unknown"



# =========================
# 模拟 Agent 参数生成
# =========================

def extract_file_name(message):

    return (
        message
        .replace("删除", "")
        .replace("读取", "")
        .replace("查看", "")
        .strip()
    )



# =========================
# Chat API
# =========================

@app.post("/chat")
def chat(data: UserMessage):


    user_message = data.message

    api_key = data.api_key



    # =========================
    # 1. Agent Layer
    # 生成 Tool Request
    # =========================

    tool_name = detect_intent(
        user_message
    )

    # =========================
    # 3. 构造 arguments
    # =========================

    if tool_name == "search":


        arguments = {

            "query": user_message

        }



    elif tool_name == "calculator":


        arguments = {

            "a": data.a,

            "b": data.b

        }



    elif tool_name == "delete_file":


        file_name = extract_file_name(
            user_message
        )


        arguments = {

            "file_name": file_name

        }



    elif tool_name == "read_file":


        file_name = extract_file_name(
            user_message
        )


        arguments = {

            "file_name": file_name

        }



    else:


        return {

            "reply": "暂不支持这个工具。"

        }



    # =========================
    # 4. Security Gateway
    # =========================

    request = SecurityRequest(
        api_key=api_key,
        tool=tool_name,
        arguments=arguments,
    )

    decision = security_engine.evaluate(request)

    # =========================
    # 5. 安全拒绝
    # =========================
    if not decision.allowed:
        response = {
            "reply": decision.reason,
            "error_code": decision.error_code,
        }
        if decision.status == "PENDING":
            response["status"] = "PENDING"
            response["approval_id"] = decision.approval_id
        return response

    # =========================
    # 6. 执行 Tool
    # =========================
    result = execute_tool(
        tool_name,
        decision.arguments,
    )

    # =========================
    # 7. 返回结果
    # =========================
    return {
        "reply": str(result),
    }

@app.get("/approvals")
def list_approvals():
    return {"pending": list_pending_approvals()}

@app.post("/approve/{approval_id}")
def approve_request(approval_id: int, action_data:ApprovalAction):
    request_info = get_approval_request(approval_id)

    if request_info is None:
        return {
            "status": "error",
            "message": f"审批请求{approval_id}不存在"
				}
    update_approval_status(
        approval_id=approval_id,
        status=action_data.action,
        reviewer=action_data.reviewer,
        reject_reason=action_data.reject_reason          
		)
    return{
        "status":"success",
        "message":f"审批请求{approval_id}已{action_data.action}",
        "reviewer":action_data.reviewer
		}

@app.get("/result/{approval_id}")
def get_result(approval_id: int):

    request_info = get_approval_request(approval_id)

    if request_info is None:
        return {
            "status": "error",
            "message": f"审批请求 {approval_id} 不存在"
        }

    # 情况 1：还在等审批
    if request_info["status"] == "PENDING":
        return {
            "status": "PENDING",
            "message": "审批还在进行中，请等待管理员处理"
        }

    # 情况 2：被拒绝
    if request_info["status"] == "REJECTED":
        return {
            "status": "REJECTED",
            "message": "审批被拒绝",
            "reject_reason": request_info["reject_reason"],
            "reviewer": request_info["reviewer"]
        }

        # 情况 3：已批准
    if request_info["status"] == "APPROVED":

        # 3.1 如果之前已经执行过，直接返回缓存结果
        if request_info["result"] is not None:
            return {
                "status": "APPROVED",
                "message": "审批通过，工具已执行（缓存结果）",
                "result": request_info["result"]
            }

        # 3.2 第一次执行，执行工具并保存结果
        result = execute_tool(
            request_info["tool_name"],
            request_info["arguments"]
        )
        result_str = str(result)

        save_approval_result(approval_id, result_str)

        return {
            "status": "APPROVED",
            "message": "审批通过，工具已执行",
            "result": result_str
        }