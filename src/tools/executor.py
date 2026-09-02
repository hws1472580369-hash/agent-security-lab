from src.tools.registry import TOOLS


def execute_tool(tool_name, arguments):

    tool = TOOLS.get(tool_name)

    if tool is None:
        raise ValueError("Tool 不存在")

    function = tool["function"]

    return function(**arguments)