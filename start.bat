@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"

if not exist "%PY%" (
    echo [1/4] 创建虚拟环境 .venv ...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -m venv .venv
    ) else (
        python -m venv .venv
    )
    if not exist "%PY%" (
        echo [x] 创建虚拟环境失败，请确认已安装 Python 3.10+ 并加入 PATH。
        pause
        exit /b 1
    )
) else (
    echo [1/4] 已存在虚拟环境 .venv
)

echo [2/4] 安装 / 检查依赖 ...
"%PY%" -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --disable-pip-version-check -q
if errorlevel 1 (
    echo [x] 依赖安装失败，请检查网络后重试。
    pause
    exit /b 1
)

echo [3/4] 检查数据库并执行迁移 ...
"%PY%" scripts\ensure_db.py
if errorlevel 1 (
    pause
    exit /b 1
)
"%PY%" manage.py migrate --noinput
if errorlevel 1 (
    echo [x] 数据库迁移失败，请检查 MySQL 配置。
    pause
    exit /b 1
)

echo [4/4] 启动开发服务器：http://127.0.0.1:8000
echo        接口前缀：/user/  /wallpapers/  /title/
"%PY%" manage.py runserver 127.0.0.1:8000

pause
