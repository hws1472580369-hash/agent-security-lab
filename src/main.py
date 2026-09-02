from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path

from src.security.authentication import authenticate
from src.security.authorization import check_agent_permission
from src.security.decision import SecurityDecision
from src.tools.registry import TOOLS
from src.tools.executor import execute_tool
from src.audit.logger import log_event

app = FastAPI()
# 1. 用户请求的数据结构
# =========================

class UserMessage(BaseModel):
    message: str
    a: int
    b: int
    api_key: str 


def check_policy(tool_name, arguments):

    if tool_name == "delete_file":

        file_name = arguments["file_name"]

        base_dir = Path("data").resolve()
        target = (base_dir / file_name).resolve()

        # 防止访问 data 目录之外的文件
        if not target.is_relative_to(base_dir):
            return False

    return True


# =========================
# 10. 意图识别
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
# 11. 参数提取
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
# 12. Security Gateway
# =========================

def security_check(tool_name, arguments, agent_id):

    # 第一关：Tool 是否存在
    tool = TOOLS.get(tool_name)

    if tool is None:
        return SecurityDecision(
            allowed=False,
            error_code="TOOL_NOT_FOUND",
            reason="Tool 不存在"
        )

    # 第二关：Agent Permission
    decision = check_agent_permission(
        tool_name,
        agent_id,
        TOOLS
    )

    if not decision.allowed:

        log_event(
            agent_id,
            tool_name,
            arguments,
            False,
            decision.reason
        )

        return decision

    # 第三关：Schema
    schema = tool.get("schema")

    if schema is not None:
        try:
            validated_args = schema(**arguments)
        except Exception:
            decision = SecurityDecision(
                allowed=False,
                error_code="SCHEMA_VALIDATION_FAILED",
                reason="参数不符合 Schema"
            )

            log_event(
                agent_id,
                tool_name,
                arguments,
                False,
                decision.reason
            )

            return decision

        arguments = validated_args.model_dump()

    # 第四关：Policy
    if not check_policy(tool_name, arguments):

        decision = SecurityDecision(
            allowed=False,
            error_code="POLICY_DENIED",
            reason="操作不符合安全策略"
        )

        log_event(
            agent_id,
            tool_name,
            arguments,
            False,
            decision.reason
        )

        return decision

    # 所有安全检查通过
    decision = SecurityDecision(
        allowed=True,
        reason="安全检查通过"
    )

    log_event(
        agent_id,
        tool_name,
        arguments,
        True,
        decision.reason
    )

    return decision
# =========================
# 13. Chat API
# =========================

@app.post("/chat")
def chat(data: UserMessage):

    user_message = data.message

    api_key = data.api_key

    # Authentication
    agent_id = authenticate(api_key)

    if agent_id is None:
        return {
            "reply": "身份认证失败"
        }
    # =========================
    # 1. 意图识别
    # =========================

    intent = detect_intent(user_message)


    # =========================
    # 2. 找 Tool
    # =========================

    tool = TOOLS.get(intent)

    if tool is None:
        return {
            "reply": "我不知道该使用哪个工具。"
        }


    # =========================
    # 3. 准备 Tool 参数
    # =========================

    if intent == "search":
        arguments = {
            "query": user_message
        }
    elif intent == "calculator":
        arguments = {
            "a": data.a,
            "b": data.b
        }
    elif intent == "delete_file":
        file_name = extract_file_name(user_message)

        arguments = {
            "file_name": file_name
        }
    elif intent == "read_file":
        file_name = extract_file_name(user_message)

        arguments = {
            "file_name": file_name
        }
    else:
        return {
            "reply": "暂不支持这个工具。"
        }

    # =========================
    # 4. 进入 Security Gateway
    # =========================

    decision = security_check(
        intent,
        arguments,
        agent_id
    )

    # =========================
    # 5. 安全检查失败
    # =========================

    if not decision.allowed:
        return {
            "reply": decision.reason,
            "error_code": decision.error_code
        }


    # =========================
    # 6. 执行 Tool
    result = execute_tool(
        intent,
        arguments
    )
    # =========================
    # 7. 返回结果
    # =========================

    return {
        "reply": str(result)
    }