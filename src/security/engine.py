from src.security.authorization import (
    check_agent_permission,
    get_agent_role,
)

from src.security.risk import (
    RiskContext,
    get_action,
    get_resource,
    get_resource_level,
    get_risk_score,
)

from src.security.policy import check_policy

from src.security.decision import (
    SecurityDecision,
    make_decision,
)

from src.security.authentication import authenticate

from src.tools.repository import get_tool

from src.audit.logger import log_event

from pydantic import create_model

from src.security.approval_repository import create_approval_request

from src.security.rate_limiter import check_rate_limit


# JSON Schema 类型 → Python 类型映射
TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
}


def build_dynamic_schema(tool_name: str, schema_dict: dict):
    """
    根据数据库里的 JSON Schema，动态生成 Pydantic 模型
    """
    fields = {}
    required = schema_dict.get("required", [])
    properties = schema_dict.get("properties", {})

    for prop, details in properties.items():
        py_type = TYPE_MAP.get(details.get("type"), str)
        if prop in required:
            fields[prop] = (py_type, ...)      # 必填
        else:
            fields[prop] = (py_type, None)     # 可选

    return create_model(f"{tool_name}_schema", **fields)


class SecurityEngine:

    def __init__(self):
        pass

    def evaluate(self, request):

        tool_name = request.tool
        arguments = request.arguments

        # =========================
        # 1. Authentication
        # =========================
        if request.agent_id is not None:
            agent_id = request.agent_id
        else:
            agent_id = authenticate(request.api_key)

        if agent_id is None:

            decision = SecurityDecision(
                decision="DENY",
                allowed=False,
                status="DENIED",
                error_code="AUTHENTICATION_FAILED",
                reason="身份认证失败"
            )

            log_event(
                "unknown",
                tool_name,
                arguments,
                False,
                decision.reason,
                error_code=decision.error_code,
                status=decision.status,
                trigger_message=request.trigger_message,
            )

            return decision

				
		    # =========================
        # 1.5 Rate Limit Check
        # =========================
        if not check_rate_limit(agent_id):

            decision = SecurityDecision(
                decision="DENY",
                allowed=False,
                status="DENIED",
                error_code="RATE_LIMITED",
                reason="请求过于频繁，请稍后再试"
            )

            log_event(
                agent_id,
                tool_name,
                arguments,
                False,
                decision.reason,
                error_code=decision.error_code,
                status=decision.status,
                trigger_message=request.trigger_message,
            )

            return decision
        # =========================
        # 2. Tool Exist Check
        # =========================
        tool = get_tool(tool_name)

        if tool is None or not tool["enabled"]:

            decision = SecurityDecision(
                decision="DENY",
                allowed=False,
                status="DENIED",
                error_code="TOOL_NOT_FOUND",
                reason="Tool不存在或已被禁用"
            )

            log_event(
                agent_id,
                tool_name,
                arguments,
                False,
                decision.reason,
                error_code=decision.error_code,
                status=decision.status,
                trigger_message=request.trigger_message,
            )

            return decision

        # =========================
        # 3. Authorization
        # =========================
        decision = check_agent_permission(
            tool_name,
            agent_id,
            tool
        )

        if not decision.allowed:

            log_event(
                agent_id,
                tool_name,
                arguments,
                False,
                decision.reason,
                error_code=decision.error_code,
                status=decision.status,
                trigger_message=request.trigger_message,
            )

            return decision

        # =========================
        # 4. Schema Validation
        # =========================
        schema_dict = tool.get("schema")

        if schema_dict is not None:

            try:
                DynamicSchema = build_dynamic_schema(
                    tool_name,
                    schema_dict
                )
                validated_args = DynamicSchema(**arguments)

            except Exception:

                decision = SecurityDecision(
                    decision="DENY",
                    allowed=False,
                    status="DENIED",
                    error_code="SCHEMA_VALIDATION_FAILED",
                    reason="参数不符合Schema"
                )

                log_event(
                    agent_id,
                    tool_name,
                    arguments,
                    False,
                    decision.reason,
                    error_code=decision.error_code,
                    status=decision.status,
                    trigger_message=request.trigger_message,
                )

                return decision

            arguments = validated_args.model_dump()

        # =========================
        # 准备上下文（Policy 和 Risk 都要用）
        # =========================
        role = get_agent_role(agent_id)

        # =========================
        # 5. Resource Policy（硬边界判断，不中断）
        # =========================
        policy_result = check_policy(
            tool_name,
            arguments,
            tool,
            role
        )

        # =========================
        # 6. Risk Assessment（算分，不中断）
        # =========================
        action = get_action(tool)
        resource = get_resource(tool, arguments)
        resource_level = get_resource_level(resource)

        risk_context = RiskContext(
            agent_id=agent_id,
            role=role,
            tool=tool_name,
            action=action,
            resource=resource,
            resource_level=resource_level,
            arguments=arguments
        )

        risk_score = get_risk_score(risk_context)

        # =========================
        # 7. Decision（统一裁决）
        # =========================
        decision = make_decision(policy_result, risk_score)

        # =========================
        # 8. PENDING 处理
        # =========================
        if decision.status == "ALLOWED":
            decision.arguments = arguments

        elif decision.status == "PENDING":
            approval_id = create_approval_request(
                agent_id=agent_id,
                tool_name=tool_name,
                arguments=arguments
            )
            decision.approval_id = approval_id
            decision.arguments = arguments

        # DENIED 时什么都不做

        # =========================
        # 9. 审计
        # =========================
        log_event(
            agent_id,
            tool_name,
            arguments,
            decision.allowed,
            decision.reason,
            error_code=decision.error_code,
            status=decision.status,
            trigger_message=request.trigger_message,
            risk_score=decision.risk_score
        )

        return decision
