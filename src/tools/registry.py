from pydantic import BaseModel


class CalculatorArgs(BaseModel):
    a: int
    b: int


class DeleteFileArgs(BaseModel):
    file_name: str


def search(query):
    return f"搜索结果：找到了关于「{query}」的信息"


def calculator(a, b):
    return a + b


def delete_file(file_name):
    return f"已删除文件：{file_name}"


TOOLS = {
    "search": {
        "function": search,
        "permission": "search.use"
    },

    "calculator": {
        "function": calculator,
        "schema": CalculatorArgs,
        "permission": "calculator.use"
    },

    "delete_file": {
        "function": delete_file,
        "schema": DeleteFileArgs,
        "permission": "file.delete"
    }
}