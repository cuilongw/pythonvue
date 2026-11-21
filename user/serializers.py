from rest_framework import serializers

from user.models import SysUser


class SysUserSerializer(serializers.ModelSerializer):
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
            "create_time",
            "update_time",
            "remask",
        ]
        read_only_fields = fields
