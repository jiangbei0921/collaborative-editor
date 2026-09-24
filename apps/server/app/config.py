import os
from pathlib import Path

# 默认数据库路径：基于当前文件位置计算，确保不受启动目录影响
_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "editor.db"

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", _DEFAULT_DB_PATH))