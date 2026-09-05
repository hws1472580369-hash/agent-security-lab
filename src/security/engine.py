from src.security.authorization import check_agent_permission
from src.security.policy import check_policy
from src.security.decision import SecurityDecision
from src.security.authentication import authenticate
from src.audit.logger import log_event



class SecurityEngine:


    def __init__(self, tools):

        self.tools = tools



    def evaluate(
            self,
            tool_name,
            arguments,
            api_key
    ):


        # =========================
        # 1. Authentication
        # =========================

        agent_id = authenticate(api_key)


        if agent_id is None:


            decision = SecurityDecision(

                allowed=False,

                error_code="AUTHENTICATION_FAILED",

                reason="身份认证失败"

            )


            log_event(

                "unknown",

                tool_name,

                arguments,

                False,

                decision.reason

            )


            return decision




        # =========================
        # 2. Tool Exist Check
        # =========================


        tool = self.tools.get(tool_name)



        if tool is None:


            decision = SecurityDecision(

                allowed=False,

                error_code="TOOL_NOT_FOUND",

                reason="Tool不存在"

            )


            log_event(

                agent_id,

                tool_name,

                arguments,

                False,

                decision.reason

            )


            return decision




        # =========================
        # 3. Authorization
        # =========================


        decision = check_agent_permission(

            tool_name,

            agent_id,

            self.tools

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





        # =========================
        # 4. Schema Validation
        # =========================


        schema = tool.get("schema")



        if schema is not None:


            try:

                validated_args = schema(**arguments)


            except Exception:


                decision = SecurityDecision(

                    allowed=False,

                    error_code="SCHEMA_VALIDATION_FAILED",

                    reason="参数不符合Schema"

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





        # =========================
        # 5. Resource Policy
        # =========================


        decision = check_policy(

            tool_name,

            arguments

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





        # =========================
        # 6. ALLOW
        # =========================


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