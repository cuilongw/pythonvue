"""确保 settings 里配置的 MySQL 数据库已经存在（不存在就创建）。

用法：
    python scripts/ensure_db.py
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DjangoProject2.settings")

import pymysql  # noqa: E402

from DjangoProject2.settings import DATABASES  # noqa: E402


def main():
    config = DATABASES["default"]
    engine = config["ENGINE"]

    if not engine.endswith("mysql"):
        print(f"当前数据库引擎是 {engine}，不需要预先建库。")
        return 0

    name = config["NAME"]
    try:
        conn = pymysql.connect(
            host=config["HOST"],
            port=int(config["PORT"]),
            user=config["USER"],
            password=config["PASSWORD"],
            charset="utf8mb4",
            connect_timeout=5,
        )
    except Exception as exc:
        print(f"[x] 连不上 MySQL（{config['HOST']}:{config['PORT']}）：{exc}")
        print("    请确认 MySQL 服务已启动，并检查 DB_USER / DB_PASSWORD 等环境变量。")
        return 1

    with conn.cursor() as cursor:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    conn.close()
    print(f"[ok] 数据库 `{name}` 已就绪。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
