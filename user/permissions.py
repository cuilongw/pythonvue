"""权限：只允许管理员执行后台写操作。

项目使用自定义的 SysUser 表 + 无状态 JWT，token 里带 username，
所以这里直接比对用户名，避免依赖 django.contrib.auth 的用户体系。
"""

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    message = "需要管理员权限"

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return getattr(user, "username", "") == "admin"
