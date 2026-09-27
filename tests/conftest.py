import os
import pytest
import tempfile
from pathlib import Path


@pytest.fixture(autouse=True)
def isolated_db():
    """
    每个测试函数都使用独立的临时数据库。
    测试结束后自动清理。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        os.environ["SECURITY_DB_PATH"] = str(db_path)

        # 初始化数据库（建表 + 灌数据）
        from src.database.models import init_db
        init_db()

        yield db_path

        # 清理环境变量
        os.environ.pop("SECURITY_DB_PATH", None)