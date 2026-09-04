from src.security.decision import SecurityDecision


RESOURCE_POLICIES = {
    "public.txt": {
        "read": True,
        "delete": True
    },

    "sensitive.txt": {
        "read": True,
        "delete": False
    },

    "secret.txt": {
        "read": False,
        "delete": False
    }
}


def check_policy(tool_name, arguments):

    if tool_name not in ["read_file", "delete_file"]:
        return SecurityDecision(
            allowed=True,
            reason="无需进行资源策略检查"
        )

    file_name = arguments["file_name"]

    policy = RESOURCE_POLICIES.get(file_name)

    if policy is None:
        return SecurityDecision(
            allowed=False,
            error_code="RESOURCE_NOT_FOUND",
            reason=f"资源 {file_name} 不在允许访问的资源列表中"
        )

    action = "read" if tool_name == "read_file" else "delete"

    if not policy[action]:
        return SecurityDecision(
            allowed=False,
            error_code="RESOURCE_ACCESS_DENIED",
            reason=f"不允许对资源 {file_name} 执行 {action} 操作"
        )

    return SecurityDecision(
        allowed=True,
        reason="资源策略检查通过"
    )