from rest_framework import serializers

from user.models import Notification, SysUser


class SysUserSerializer(serializers.ModelSerializer):
    banned = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = SysUser
        fields = [
            "id",
            "username",
            "avatar",
            "email",
            "phonenumber",
            "login_date",
            "status",
            "banned",
            "role",
            "create_time",
            "update_time",
            "remask",
        ]
        read_only_fields = fields

    def get_banned(self, obj):
        # status 为 False 表示被封禁，None 视为正常
        return obj.status is False

    def get_role(self, obj):
        return "admin" if obj.username == "admin" else "user"


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "userrole",
            "title",
            "message",
            "notification_type",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields
