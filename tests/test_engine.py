"""网关核心逻辑的独立测试。不依赖 LLM。"""

from src.security.engine import SecurityEngine
from src.models.request import SecurityRequest


engine = SecurityEngine()


# =========================
# 认证层
# =========================

def test_authentication_failed():
    """无效 API Key → AUTHENTICATION_FAILED"""
    request = SecurityRequest(
        api_key="key_wrong",
        tool="read_file",
        arguments={"file_name": "public.txt"},
    )
    decision = engine.evaluate(request)

    assert decision.allowed is False
    assert decision.error_code == "AUTHENTICATION_FAILED"
    assert decision.status == "DENIED"


# =========================
# 鉴权层
# =========================

def test_authorization_denied():
    """agent_001（normal_agent）没有 file.read → AUTHORIZATION_DENIED"""
    request = SecurityRequest(
        api_key="key_agent_001",
        tool="read_file",
        arguments={"file_name": "public.txt"},
    )
    decision = engine.evaluate(request)

    assert decision.allowed is False
    assert decision.error_code == "AUTHORIZATION_DENIED"


# =========================
# 资源策略层
# =========================

def test_resource_access_denied_read_secret():
    """agent_002 读 internal_notes.txt → RESOURCE_ACCESS_DENIED"""
    request = SecurityRequest(
        api_key="key_agent_002",
        tool="read_file",
        arguments={"file_name": "internal_notes.txt"},
    )
    decision = engine.evaluate(request)

    assert decision.allowed is False
    assert decision.error_code == "RESOURCE_ACCESS_DENIED"


def test_resource_access_denied_delete_sensitive():
    """agent_002 删 customer_records.txt → RESOURCE_ACCESS_DENIED"""
    request = SecurityRequest(
        api_key="key_agent_002",
        tool="delete_file",
        arguments={"file_name": "customer_records.txt"},
    )
    decision = engine.evaluate(request)

    assert decision.allowed is False
    assert decision.error_code == "RESOURCE_ACCESS_DENIED"


def test_condition_not_met():
    """admin_001 读 customer_records.txt → CONDITION_NOT_MET（condition 要求 file_agent）"""
    request = SecurityRequest(
        api_key="key_admin_001",
        tool="read_file",
        arguments={"file_name": "customer_records.txt"},
    )
    decision = engine.evaluate(request)

    assert decision.allowed is False
    assert decision.error_code == "CONDITION_NOT_MET"


# =========================
# Schema 校验层
# =========================

def test_schema_validation_failed():
    """参数缺失 → SCHEMA_VALIDATION_FAILED"""
    request = SecurityRequest(
        api_key="key_agent_002",
        tool="read_file",
        arguments={},   # 缺 file_name
    )
    decision = engine.evaluate(request)

    assert decision.allowed is False
    assert decision.error_code == "SCHEMA_VALIDATION_FAILED"


# =========================
# 风险层
# =========================

def test_read_public_allowed():
    """agent_002 读 public.txt → ALLOWED（分数 10）"""
    request = SecurityRequest(
        api_key="key_agent_002",
        tool="read_file",
        arguments={"file_name": "public.txt"},
    )
    decision = engine.evaluate(request)

    assert decision.allowed is True
    assert decision.status == "ALLOWED"


def test_read_sensitive_pending():
    """agent_002 读 customer_records.txt → PENDING（分数 30）"""
    request = SecurityRequest(
        api_key="key_agent_002",
        tool="read_file",
        arguments={"file_name": "customer_records.txt"},
    )
    decision = engine.evaluate(request)

    assert decision.allowed is False
    assert decision.status == "PENDING"
    assert decision.approval_id is not None


def test_delete_test_risk_high_risk():
    """agent_002 删 test_risk.txt → HIGH_RISK（分数 50）"""
    request = SecurityRequest(
        api_key="key_agent_002",
        tool="delete_file",
        arguments={"file_name": "test_risk.txt"},
    )
    decision = engine.evaluate(request)

    assert decision.allowed is False
    assert decision.status == "DENIED"
    assert decision.error_code == "HIGH_RISK"

# =========================
# 工具检查层
# =========================

def test_tool_not_found():
    """请求一个不存在的工具 → TOOL_NOT_FOUND"""
    request = SecurityRequest(
        api_key="key_agent_002",
        tool="nonexistent_tool",
        arguments={},
    )
    decision = engine.evaluate(request)

    assert decision.allowed is False
    assert decision.error_code == "TOOL_NOT_FOUND"


# =========================
# 资源层
# =========================

def test_resource_not_found():
    """请求一个不在 resources 表里的文件 → RESOURCE_NOT_FOUND"""
    request = SecurityRequest(
        api_key="key_agent_002",
        tool="read_file",
        arguments={"file_name": "nonexistent.txt"},
    )
    decision = engine.evaluate(request)

    assert decision.allowed is False
    assert decision.error_code == "RESOURCE_NOT_FOUND"


# =========================
# 频率限制层
# =========================

def test_rate_limited():
    """快速连发超过阈值 → RATE_LIMITED"""
    from src.audit.logger import log_event

    # 先造 N 条请求记录（假设阈值 20）
    for i in range(55):
        log_event(
            agent_id="agent_002",
            tool_name="search",
            arguments={"query": f"test{i}"},
            allowed=True,
            reason="测试",
            error_code=None,
            status="ALLOWED",
        )

    # 第 26 次请求 → 应该被限流
    request = SecurityRequest(
        api_key="key_agent_002",
        tool="search",
        arguments={"query": "触发限流"},
    )
    decision = engine.evaluate(request)

    assert decision.allowed is False
    assert decision.error_code == "RATE_LIMITED" 

# =========================
# 路径穿越（工具层）
# =========================

def test_path_traversal_blocked():
    """路径穿越攻击 → 工具层返回路径越界"""
    from src.tools.registry import read_file

    result = read_file("../../etc/passwd")
    assert "路径越界" in result


def test_path_traversal_with_absolute_path():
    """绝对路径攻击 → 工具层返回路径越界"""
    from src.tools.registry import read_file

    result = read_file("/etc/passwd")
    assert "路径越界" in result


# =========================
# 动态规则（Risk 层）
# =========================

def test_dynamic_penalty_triggers_pending():
    """被拒 3 次后，正常请求被推高到 PENDING"""
    from src.audit.logger import log_event

    # 造 3 条 DENIED 记录
    for _ in range(3):
        log_event(
            agent_id="agent_002",
            tool_name="read_file",
            arguments={"file_name": "internal_notes.txt"},
            allowed=False,
            reason="测试",
            error_code="RESOURCE_ACCESS_DENIED",
            status="DENIED",
        )

    # 现在发一个"本该 ALLOWED"的请求
    # 基础分：read(10) + PUBLIC(0) + file_agent(0) = 10
    # 动态惩罚：+30
    # 总分：40 → MEDIUM → PENDING
    request = SecurityRequest(
        api_key="key_agent_002",
        tool="read_file",
        arguments={"file_name": "public.txt"},
    )
    decision = engine.evaluate(request)

    assert decision.status == "PENDING"      
