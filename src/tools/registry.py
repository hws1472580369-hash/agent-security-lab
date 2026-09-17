from pathlib import Path


# 允许访问的根目录（绝对路径）
BASE_DIR = Path("data").resolve()


def _is_path_safe(file_name: str) -> bool:
    """
    检查 file_name 解析后的路径是否在 data/ 目录下。
    防止路径穿越攻击（如 ../../etc/passwd）。
    """
    try:
        target = (BASE_DIR / file_name).resolve()
        target.relative_to(BASE_DIR)   # 如果 target 不在 BASE_DIR 下会抛 ValueError
        return True
    except (ValueError, OSError):
        return False


def search(query):
    return f"搜索结果：找到了关于「{query}」的信息"


def calculator(a, b):
    return a + b


def delete_file(file_name):
    if not _is_path_safe(file_name):
        return f"路径越界：{file_name}"

    path = (BASE_DIR / file_name).resolve()

    if not path.exists():
        return f"文件不存在：{file_name}"

    path.unlink()
    return f"已删除文件：{file_name}"


def read_file(file_name):
    if not _is_path_safe(file_name):
        return f"路径越界：{file_name}"

    path = (BASE_DIR / file_name).resolve()

    with open(path, "r", encoding="utf-8") as f:
        return f.read()


TOOL_IMPLEMENTATIONS = {
    "search": search,
    "calculator": calculator,
    "delete_file": delete_file,
    "read_file": read_file,
}