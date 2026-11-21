"""
让 Django 的 MySQL 后端直接使用纯 Python 的 PyMySQL 驱动，
避免在 Windows 上编译 mysqlclient 失败。
"""

import pymysql

pymysql.install_as_MySQLdb()
