from fastapi import FastAPI
from pydantic import BaseModel

from src.tools.registry import TOOLS
from src.security.engine import SecurityEngine
from src.tools.executor import execute_tool


app = FastAPI()


# Security Gateway
security_engine = SecurityEngine(TOOLS)


# =========================
# 用户请求数据结构
# =========================

class UserMessage(BaseModel):

    message: str

    a: int

    b: int

    api_key: str



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
    # 2. 查找 Tool
    # =========================

    tool = TOOLS.get(tool_name)


    if tool is None:

        return {

            "reply": "我不知道该使用哪个工具。"

        }



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

    decision = security_engine.evaluate(

        tool_name,

        arguments,

        api_key

    )



    # =========================
    # 5. 安全拒绝
    # =========================

    if not decision.allowed:


        return {

            "reply": decision.reason,

            "error_code": decision.error_code

        }



    # =========================
    # 6. 执行 Tool
    # =========================

    result = execute_tool(

        tool_name,

        arguments

    )



    # =========================
    # 7. 返回结果
    # =========================

    return {

        "reply": str(result)

    }