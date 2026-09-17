from src.tools.registry import TOOL_IMPLEMENTATIONS


def execute_tool(tool_name, arguments):

    function = TOOL_IMPLEMENTATIONS.get(tool_name)

    if function is None:
        raise ValueError(f"Tool {tool_name} 没有对应的实现函数")

    return function(**arguments)