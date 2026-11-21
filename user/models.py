from django.db import models

# Create your models here.


class SysUser(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=150)
    avatar = models.CharField(max_length=255, null=True, verbose_name="用户头像")
    email = models.EmailField(max_length=50, null=True, verbose_name="用户邮箱")
    phonenumber = models.CharField(max_length=11, null=True, verbose_name="用户手机")
    login_date = models.DateTimeField(null=True, verbose_name="登录时间")
    status = models.BooleanField(null=True, verbose_name="用户状态")
    create_time = models.DateTimeField(null=True, verbose_name="创建时间")
    update_time = models.DateTimeField(null=True, verbose_name="更新时间")
    remask = models.CharField(max_length=255, null=True, verbose_name="备注")

    class Meta:
        db_table = "sys_user"
        verbose_name = "用户表"


class Notification(models.Model):
    """站内消息通知，前端“消息通知”页面使用。"""

    TYPES = (
        ("system", "系统消息"),
        ("audit", "审核结果"),
        ("favorite", "收藏提醒"),
    )

    userrole = models.CharField(max_length=150, db_index=True, verbose_name="接收人")
    title = models.CharField(max_length=200, blank=True, default="", verbose_name="标题")
    message = models.TextField(verbose_name="内容")
    notification_type = models.CharField(
        max_length=50, choices=TYPES, default="system", verbose_name="类型"
    )
    is_read = models.BooleanField(default=False, verbose_name="是否已读")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "消息通知"

    def __str__(self):
        return f"{self.userrole}: {self.message[:30]}"


class EmailCode(models.Model):
    """邮箱验证码，用于找回密码。"""

    email = models.EmailField(db_index=True)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=32, default="reset_password")
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "邮箱验证码"

    def __str__(self):
        return f"{self.email}: {self.code}"

