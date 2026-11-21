"""初始化演示数据：登录账号、导航栏、分类。

用法：
    python manage.py seed_demo                  # 只建账号 + 导航 + 分类
    python manage.py seed_demo --with-media     # 顺便把 media/wallpapers 里还没入库的图片导入
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from PIL import Image

from title.models import CategoryItem, CategoryList, NavigationItem
from user.models import SysUser
from wallpapers.models import Wallpaper


class Command(BaseCommand):
    help = "初始化演示账号、导航栏和分类数据（可重复执行）"

    def add_arguments(self, parser):
        parser.add_argument("--with-media", action="store_true", help="导入 media/wallpapers 下未入库的图片")
        parser.add_argument("--username", default="admin", help="演示账号用户名，默认 admin")
        parser.add_argument("--password", default="admin123", help="演示账号密码，默认 admin123")

    def handle(self, *args, **options):
        self.seed_users(options["username"], options["password"])
        self.seed_titles()
        if options["with_media"]:
            self.seed_media()
        self.stdout.write(self.style.SUCCESS("演示数据初始化完成"))

    def seed_users(self, username, password):
        users = [
            (username, password, "管理员演示账号", "admin@wallpaper.local"),
            ("test", "test1234", "普通用户演示账号", "test@wallpaper.local"),
        ]
        for name, raw_password, remark, email in users:
            user, created = SysUser.objects.get_or_create(
                username=name,
                defaults={
                    "password": make_password(raw_password),
                    "status": True,
                    "remask": remark,
                    "email": email,
                },
            )
            if not created and not user.password.startswith(("pbkdf2_", "argon2")):
                user.password = make_password(raw_password)
                user.save(update_fields=["password"])
            if not created and not user.email:
                user.email = email
                user.save(update_fields=["email"])
            self.stdout.write(("  + 新增用户 " if created else "  = 已存在用户 ") + name)

    def seed_titles(self):
        navigations = [
            ("首页", "/", 0, "House"),
            ("手机壁纸", "/phone", 1, "Iphone"),
            ("头像", "/avatar", 2, "User"),
            ("收藏", "/like", 3, "Star"),
            ("我的", "/my", 4, "User"),
        ]
        for title, path, order, icon in navigations:
            _, created = NavigationItem.objects.get_or_create(
                title=title,
                defaults={"path": path, "order": order, "icon": icon},
            )
            self.stdout.write(("  + 新增导航 " if created else "  = 已存在导航 ") + title)

        categories = [
            ("风景", "1920x1080", "自然,山,海", 0),
            ("动漫", "2560x1440", "二次元,插画", 1),
            ("明星", "1080x1920", "人物,写真", 2),
            ("游戏", "3840x2160", "电竞,原画", 3),
            ("简约", "2560x1440", "纯色,极简", 4),
        ]
        for name, resolution, tags, order in categories:
            _, created = CategoryItem.objects.get_or_create(
                name=name,
                defaults={"resolution": resolution, "tags": tags, "order": order},
            )
            self.stdout.write(("  + 新增分类 " if created else "  = 已存在分类 ") + name)

        for title, order in [("电脑壁纸", 0), ("手机壁纸", 1), ("头像", 2)]:
            _, created = CategoryList.objects.get_or_create(
                title=title, defaults={"order": order}
            )
            self.stdout.write(("  + 新增分类列表 " if created else "  = 已存在分类列表 ") + title)

    def seed_media(self):
        media_root = Path(settings.MEDIA_ROOT)
        source_dir = media_root / "wallpapers"
        if not source_dir.exists():
            self.stdout.write(self.style.WARNING(f"没有找到图片目录：{source_dir}"))
            return

        existing = set(Wallpaper.objects.values_list("image", flat=True))
        yasuo_dir = media_root / "yasuo"
        created_count = 0
        for path in sorted(source_dir.iterdir()):
            if not path.is_file():
                continue
            image_field = f"wallpapers/{path.name}"
            if image_field in existing:
                continue
            try:
                with Image.open(path) as img:
                    width, height = img.size
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f"  跳过无法识别的文件 {path.name}: {exc}"))
                continue

            aspect_ratio = width / height
            if 0.8 <= aspect_ratio <= 1.2 and max(width, height) <= 2048:
                media_type = "avatar"
            elif aspect_ratio > 1.2 and width >= 1920:
                media_type = "computer"
            elif aspect_ratio < 0.8 and height >= 1920:
                media_type = "mobile"
            else:
                media_type = "unknown"

            image_url = f"yasuo/{path.name}" if (yasuo_dir / path.name).exists() else image_field
            Wallpaper.objects.create(
                title=path.stem,
                description="",
                category="未分类",
                media_type=media_type,
                tags=[],
                image=image_field,
                image_url=image_url,
                resolution=f"{width}x{height}",
            )
            created_count += 1

        self.stdout.write(f"  + 从 media/wallpapers 导入壁纸 {created_count} 张")
