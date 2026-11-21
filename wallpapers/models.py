from django.db import models


class Wallpaper(models.Model):
    MEDIA_TYPES = (
        ("computer", "电脑壁纸"),
        ("mobile", "手机壁纸"),
        ("avatar", "头像"),
        ("unknown", "未分类"),
    )

    STATUS_CHOICES = (
        ("pending", "待审核"),
        ("approved", "已通过"),
        ("rejected", "已拒绝"),
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=50)
    media_type = models.CharField(
        max_length=20, choices=MEDIA_TYPES, default="computer"
    )
    tags = models.JSONField(blank=True, default=list)
    upload_date = models.DateTimeField(auto_now_add=True)
    downloads = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to="wallpapers/")
    image_url = models.ImageField(upload_to="yasuo/")
    resolution = models.CharField(max_length=20)
    # 上传者用户名（前端传的是 userrole），用于后台列表展示和审核通知
    userrole = models.CharField(max_length=150, blank=True, default="", db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="approved", db_index=True
    )
    review_remark = models.CharField(max_length=255, blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-upload_date", "-id"]

    def __str__(self):
        return self.title


class Favorite(models.Model):
    """用户收藏。项目用的是自定义 SysUser，所以这里用用户名字符串关联。"""

    userrole = models.CharField(max_length=150, db_index=True)
    wallpaper = models.ForeignKey(
        Wallpaper, on_delete=models.CASCADE, related_name="favorites"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["userrole", "wallpaper"], name="uniq_favorite_user_wallpaper"
            )
        ]

    def __str__(self):
        return f"{self.userrole} -> {self.wallpaper_id}"


class DownloadRecord(models.Model):
    """下载记录，对应前端的“下载历史”。"""

    userrole = models.CharField(max_length=150, db_index=True)
    wallpaper = models.ForeignKey(
        Wallpaper, on_delete=models.CASCADE, related_name="download_records"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.userrole} -> {self.wallpaper_id}"


class BrowseRecord(models.Model):
    """浏览记录，对应前端的“浏览历史”。"""

    userrole = models.CharField(max_length=150, db_index=True)
    wallpaper = models.ForeignKey(
        Wallpaper, on_delete=models.CASCADE, related_name="browse_records"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.userrole} -> {self.wallpaper_id}"
