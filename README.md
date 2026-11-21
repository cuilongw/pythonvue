# 壁纸网站后端（DjangoProject2）

一个壁纸网站的后端，使用 Django + Django REST Framework 完成，配套前端在 `../xixixix`（Vue 3 + Vite）。

## 技术栈

- Python 3.10+（当前验证版本 3.11.9）
- Django 5.1.7 / Django REST Framework 3.15.2
- djangorestframework-simplejwt（登录签发 JWT）
- MySQL 8（默认库名 `db_admin3`），通过 PyMySQL 驱动连接
- Pillow（上传图片时读取分辨率、自动判断壁纸类型）

## 目录结构

```
DjangoProject2/
├── DjangoProject2/          # 项目配置（settings / urls / PyMySQL 适配）
├── user/                    # 用户：登录、注册、JWT
├── wallpapers/              # 壁纸：批量上传、分页、搜索、下载计数
├── title/                   # 首页导航栏、分类列表、分类项
├── media/                   # 上传的图片（wallpapers/ 原图，yasuo/ 压缩图）
├── scripts/ensure_db.py     # 检查并创建 MySQL 数据库
├── start.bat                # Windows 一键启动
└── manage.py
```

## 快速开始（Windows）

### 一键启动

双击 `start.bat` 即可，脚本会自动完成：创建虚拟环境 → 安装依赖 → 检查/创建数据库 → 执行迁移 → 启动服务。

启动后访问 <http://127.0.0.1:8000/>，看到「欢迎访问首页！」说明后端正常。

### 手动启动

```powershell
# 1. 创建并激活虚拟环境
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 安装依赖（国内网络可用镜像）
python -m pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# 3. 建库 + 迁移
python scripts\ensure_db.py
python manage.py migrate

# 4. 启动
python manage.py runserver 127.0.0.1:8000
```

### 初始化演示数据（可选）

```powershell
python manage.py seed_demo
```

会创建演示账号、首页导航栏和分类数据，可重复执行：

| 账号 | 密码 | 说明 |
| --- | --- | --- |
| `admin` | `admin123` | 管理员演示账号 |
| `test` | `test1234` | 普通用户演示账号 |

如果想把仓库里 `media/wallpapers` 下尚未入库的图片全部导入数据库，有两种方式：

```powershell
# 方式一：走上传接口（推荐，和前端上传走同一套逻辑，会计算分辨率、自动判断类型）
python scripts\upload_media.py

# 方式二：直接写数据库，不复制文件（速度快，适合只想补数据）
python manage.py seed_demo --with-media
```

`upload_media.py` 需要后端已经启动（默认 `http://127.0.0.1:8000`），支持参数：

```powershell
python scripts\upload_media.py --base-url http://127.0.0.1:8000 --username admin --password admin123
python scripts\upload_media.py --dry-run          # 只统计待上传数量
python scripts\upload_media.py --batch-mb 20 --batch-files 6   # 控制单个请求大小
```

已上传的文件名记录在 `scripts/.uploaded_media.txt`，重复执行会自动跳过；要全部重传就删掉这个文件。

## 配置

数据库默认连接 `127.0.0.1:3306/db_admin3`，账号 `root/123456`，可以用环境变量覆盖：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DB_ENGINE` | `mysql` | 设为 `sqlite` 可在没有 MySQL 时用 `db.sqlite3` 启动 |
| `DB_NAME` | `db_admin3` | 数据库名 |
| `DB_USER` | `root` | 用户名 |
| `DB_PASSWORD` | `123456` | 密码 |
| `DB_HOST` | `127.0.0.1` | 主机 |
| `DB_PORT` | `3306` | 端口 |

例如临时用 SQLite 跑起来：

```powershell
$env:DB_ENGINE="sqlite"; python manage.py migrate; python manage.py runserver
```

## 接口一览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 首页探活 |
| POST | `/user/login/` | 登录，返回 `code/token/user`；带 `{"refresh": "..."}` 可换新 access |
| POST | `/user/register/` | 注册（密码 PBKDF2 加密存储） |
| GET | `/title/navigation-bar/` | 导航栏 |
| GET | `/title/category-list/` | 分类列表 |
| GET | `/title/category-item/` | 分类项（分类 / 分辨率 / 标签） |
| GET | `/wallpapers/wallpapers/page/` | 壁纸分页，支持 `page`、`pageSize`、`category`、`resolution`、`media_type`、`tags`、`title` |
| GET | `/wallpapers/wallpapers/search/` | 按标签搜索，返回数组 |
| POST | `/wallpapers/bulk-upload/` | 批量上传，`multipart/form-data`，字段 `images`（可多个）、`title`、`category`、`description`、`tags` |
| POST | `/wallpapers/wallpapers/download/<id>/` | 下载次数 +1 |

上传接口需要请求头 `Authorization: Bearer <access token>`。access token 默认 5 分钟有效，前端会用 refresh token 自动续期。

## 与前端联调

前端 `xixixix` 的 `src/utils/request.js` 里 `baseURL` 是 `http://localhost:8000/`，Vite 开发端口是 `5000`。

后端已开启 CORS（允许所有来源、允许 `Authorization` 请求头），直接启动前端即可联调：

```powershell
cd ..\xixixix
npm run dev
```

## 这次为了「能跑起来」改了什么

1. **补依赖**：原 `requirements.txt` 里的 `mysqlclient` 在 Windows 上需要 C 编译器，改为纯 Python 的 `PyMySQL`；移除与 Django 5 不兼容、且代码里未启用的 `djangorestframework-jwt`。
2. **PyMySQL 适配**：`DjangoProject2/__init__.py` 中调用 `pymysql.install_as_MySQLdb()`。
3. **数据库可配置**：`settings.py` 的数据库改为读环境变量，并新增 `scripts/ensure_db.py` 自动建库。
4. **JWT 认证修正**：项目用的是自定义 `SysUser` 表，而 SimpleJWT 默认会去 `auth_user` 表查用户，导致带 token 的请求报 `user_not_found`。已改用 `JWTStatelessUserAuthentication`，并在 token 里写入 `username`。
5. **批量上传修正**：原代码用 `TokenAuthentication` 却要求 `Bearer` 头，且手工只校验前缀不校验签名，现已统一走 JWT 认证；`tags` 字符串会解析成列表再存 JSONField。
6. **分页排序**：`Wallpaper` 增加 `Meta.ordering`，避免分页时出现 `UnorderedObjectListWarning`。
7. **迁移同步**：补了 `media_type` 默认值、模型排序两个迁移，保证 `makemigrations` 不再漂移。
8. **时间/语言**：时区改为 `Asia/Shanghai`，语言 `zh-hans`。
9. **MySQL 8 认证**：MySQL 8 默认 `caching_sha2_password`，PyMySQL 完整认证需要 `cryptography`，已加入依赖。
10. **图片入库脚本**：新增 `scripts/upload_media.py`，走 `/wallpapers/bulk-upload/` 接口把 `media/wallpapers` 的图片批量入库（支持断点续传、token 过期自动重登）。
11. **分页参数兼容**：前端传 `pageSize`、后端只认 `page_size`，已在分页类里同时兼容两者。

## 常见问题

- **`Unknown database 'db_admin3'`**：先执行 `python scripts\ensure_db.py`，或手动 `CREATE DATABASE db_admin3 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`。
- **连不上 MySQL**：确认 MySQL80 服务已启动（`Get-Service MySQL80`），并核对 `DB_USER` / `DB_PASSWORD`。
- **端口 8000 被占用**：`python manage.py runserver 127.0.0.1:8001`，同时把前端 `request.js` 的 `baseURL` 改成对应端口。
- **上传返回 401**：登录拿到的 access token 过期了，重新登录或走前端自动刷新逻辑。
- **控制台中文乱码**：只是 Windows 控制台编码问题，数据本身是 UTF-8；`chcp 65001` 即可正常显示。

## 尚未实现的前端接口

前端还调用了一些后端目前没有的接口，访问会返回 404，属于待补齐的功能（不影响现有页面启动）：

`/user/users/`、`/user/users/<id>/ban/`、`/user/history/`、`/user/notifications/`、`/user/send-code/`、`/user/password-reset/`、`/wallpapers/favorites/`、`/wallpapers/favorite/<id>/favorite/`、`/wallpapers/download-history/`、`/wallpapers/wallpapers/pending/`、`/wallpapers/wallpapers/<id>/(edit|review|delete)/`、`/title/category-item/<id>/` 的增删改。
