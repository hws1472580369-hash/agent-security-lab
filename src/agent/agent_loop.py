import json

from src.agent.llm_agent import SYSTEM_PROMPT
from src.models.request import SecurityRequest
from src.tools.executor import execute_tool
from src.security.authentication import authenticate
from src.audit.logger import log_event


class AgentLoop:
    """多轮 Agent 循环：LLM 的每一次工具调用都经过安全网关，拒绝即终止。"""

    def __init__(
        self,
        llm_agent,
        security_engine,
        system_prompt: str = SYSTEM_PROMPT,
        max_iterations: int = 5,
    ):
        self.llm_agent = llm_agent
        self.security_engine = security_engine
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations

    def run(self, message: str, api_key: str) -> dict:
        # 先认证：无论 LLM 是否调用工具，我们都需要知道这是哪个 Agent，
        # 才能把「LLM 直接回复（包括拒绝）」也写进审计日志。
        agent_id = authenticate(api_key)
        if agent_id is None:
            log_event(
                "unknown",
                "authentication",
                {"message": message},
                False,
                "身份认证失败",
                error_code="AUTHENTICATION_FAILED",
                status="DENIED",
            )
            return {"reply": "身份认证失败", "error_code": "AUTHENTICATION_FAILED"}

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": message},
        ]
        tools = self.llm_agent.tools

        for _ in range(self.max_iterations):
            assistant = self.llm_agent.chat(messages, tools)
            messages.append(assistant)

            tool_calls = assistant.get("tool_calls")
            if not tool_calls:
                reply = assistant.get("content") or "我没有理解你的意思。"
                # LLM 没有调用任何工具就返回：这可能是一次正常聊天，
                # 也可能是一次被 LLM 自己挡下的攻击。无论哪种都要留痕。
                log_event(
                    agent_id,
                    "llm_direct_reply",
                    {
                        "message": message,
                        "reply": reply[:500],
                    },
                    True,
                    "LLM 未调用工具，直接回复",
                    status="ALLOWED",
                    trigger_message=message,
                )
                return {"reply": reply}

            tool_call = tool_calls[0]
            tool_name = tool_call["function"]["name"]
            try:
                arguments = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                arguments = {}

            # 每一次工具调用都必须经过安全网关
            request = SecurityRequest(
                api_key=api_key,
                tool=tool_name,
                arguments=arguments,
                trigger_message=message,
            )
            decision = self.security_engine.evaluate(request)

            if decision.status == "DENIED":
                return {"reply": decision.reason, "error_code": decision.error_code}

            if decision.status == "PENDING":
                return {
                    "reply": decision.reason,
                    "error_code": decision.error_code,
                    "status": "PENDING",
                    "approval_id": decision.approval_id,
                }

            # ALLOWED：执行工具，把结果回填给 LLM，进入下一轮
            result = execute_tool(tool_name, decision.arguments)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": str(result),
                "content": f"<文件内容>\n{result}\n</文件内容>",
            })

        return {"reply": "超过最大轮数，已停止。"}
