from pydantic import BaseModel


class SecurityDecision(BaseModel):

    decision: str

    allowed: bool

    error_code: str | None = None

    reason: str | None = None

    arguments: dict | None = None
    
    status: str = "ALLOWED"
    
    approval_id: int | None = None

    risk_score: int | None = None
def make_decision(policy_result, risk_score):
    """
    综合硬边界判断（policy_result）和风险分数（risk_score），
    输出最终决策。

    优先级：
        1. Policy 拒绝 → 直接 DENY（用 Policy 的 error_code）
        2. Policy 通过 → 按 risk_score 分级
    """

    # 1. 硬边界拒绝优先
    if not policy_result["passed"]:
        return SecurityDecision(
            decision="DENY",
            allowed=False,
            status="DENIED",
            error_code=policy_result["error_code"],
            reason=policy_result["reason"],
            risk_score=risk_score,
        )

    # 2. 硬边界通过，看风险分
    if risk_score >= 50:
        return SecurityDecision(
            decision="DENY",
            allowed=False,
            status="DENIED",
            error_code="HIGH_RISK",
            reason="风险等级过高，拒绝执行",
            risk_score=risk_score,
        )

    elif risk_score >= 30:
        return SecurityDecision(
            decision="REQUIRE_APPROVAL",
            allowed=False,
            status="PENDING",
            reason="风险等级中等，需要人工审批",
            risk_score=risk_score,
        )

    else:
        return SecurityDecision(
            decision="ALLOW",
            allowed=True,
            status="ALLOWED",
            reason="风险等级较低，允许执行",
            risk_score=risk_score,
        )
if __name__ == "__main__":

    print(make_decision({"passed": True}, 10))

    print(make_decision({"passed": True}, 30))

    print(make_decision({"passed": True}, 50))