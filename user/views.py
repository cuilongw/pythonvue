import json
import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from DjangoProject2.pagination import StandardPagination
from user.models import EmailCode, Notification, SysUser
from user.permissions import IsAdmin
from user.serializers import NotificationSerializer, SysUserSerializer

from wallpapers.models import BrowseRecord
from wallpapers.serializers import BrowseRecordSerializer


def parse_json_body(request):
    try:
        return json.loads(request.body or b"{}")
    except (TypeError, ValueError):
        return None


def as_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on")
    if value is None:
        return default
    return bool(value)


class LoginView(View):
    def post(self, request):
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({"code": 400, "message": "请求数据格式错误"})

        username = data.get("username")
        password = data.get("password")

        # 前端 401 时会带 refresh 来这里换新的 access token
        if data.get("refresh") and not username:
            try:
                refresh = RefreshToken(data["refresh"])
            except TokenError:
                return JsonResponse({"code": 401, "message": "刷新凭证无效或已过期"})
            return JsonResponse(
                {
                    "code": 200,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                }
            )

        if not username or not password:
            return JsonResponse({"code": 400, "message": "用户名或密码不能为空"})

        try:
            user = SysUser.objects.get(username=username)
        except SysUser.DoesNotExist:
            return JsonResponse({"code": 400, "message": "用户名或密码错误"})

        if user.status is False:
            return JsonResponse({"code": 403, "message": "账号已被封禁"})

        if not check_password(password, user.password):
            return JsonResponse({"code": 400, "message": "用户名或密码错误"})

        user.login_date = timezone.now()
        user.save(update_fields=["login_date"])

        refresh = RefreshToken.for_user(user)
        refresh["username"] = user.username
        token = {"refresh": str(refresh), "access": str(refresh.access_token)}

        return JsonResponse(
            {
                "code": 200,
                "token": token,
                "user": SysUserSerializer(user).data,
                "Info": "登录成功",
            }
        )


class RegisterView(View):
    def post(self, request):
        data = parse_json_body(request)
        if data is None:
            return JsonResponse({"code": 400, "message": "请求数据格式错误"})

        username = (data.get("username") or "").strip()
        password = data.get("password") or ""

        if not username or not password:
            return JsonResponse({"code": 400, "message": "用户名或密码不能为空"})
        if len(password) < 6:
            return JsonResponse({"code": 400, "message": "密码至少 6 位"})
        if SysUser.objects.filter(username=username).exists():
            return JsonResponse({"code": 400, "message": "用户名已存在"})

        try:
            user = SysUser.objects.create(
                username=username,
                password=make_password(password),
                email=(data.get("email") or None),
                phonenumber=(data.get("phonenumber") or None),
                status=True,
                create_time=timezone.now(),
            )
            Notification.objects.create(
                userrole=username,
                title="欢迎加入",
                message="注册成功，快去挑选喜欢的壁纸吧！",
                notification_type="system",
            )
            return JsonResponse(
                {"code": 200, "message": "注册成功", "user_id": user.id}
            )
        except Exception as e:
            return JsonResponse({"code": 500, "message": "注册失败", "error": str(e)})


# --------------------------------------------------------------------------- #
# 用户管理（后台）
# --------------------------------------------------------------------------- #
class UserListView(ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = SysUserSerializer
    pagination_class = StandardPagination
    queryset = SysUser.objects.all().order_by("id")


class UserBanView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            target = SysUser.objects.get(pk=pk)
        except SysUser.DoesNotExist:
            return Response(
                {"code": 404, "message": "用户不存在"}, status=status.HTTP_404_NOT_FOUND
            )

        if target.username == "admin":
            return Response({"code": 403, "message": "不能封禁管理员账号"})

        ban = as_bool(request.data.get("ban"), default=True)
        target.status = not ban
        target.update_time = timezone.now()
        target.save(update_fields=["status", "update_time"])

        if ban:
            Notification.objects.create(
                userrole=target.username,
                title="账号已被封禁",
                message="你的账号已被管理员封禁，如有疑问请联系管理员。",
                notification_type="system",
            )

        return Response(
            {
                "code": 200,
                "message": "已封禁该用户" if ban else "已恢复该用户",
                "banned": ban,
                "id": target.id,
            }
        )


# --------------------------------------------------------------------------- #
# 消息通知
# --------------------------------------------------------------------------- #
class NotificationListView(APIView):
    def get(self, request):
        userrole = (request.query_params.get("userrole") or "").strip()
        if not userrole:
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                userrole = getattr(user, "username", "")

        try:
            limit = max(1, min(int(request.query_params.get("limit", 10)), 100))
        except (TypeError, ValueError):
            limit = 10
        try:
            offset = max(0, int(request.query_params.get("offset", 0)))
        except (TypeError, ValueError):
            offset = 0

        queryset = Notification.objects.filter(userrole=userrole) if userrole else Notification.objects.none()
        total = queryset.count()
        items = queryset[offset : offset + limit]
        return Response(
            {
                "count": total,
                "total": total,
                "limit": limit,
                "offset": offset,
                "results": NotificationSerializer(items, many=True).data,
            }
        )


class NotificationReadView(APIView):
    def post(self, request, pk):
        updated = Notification.objects.filter(pk=pk).update(is_read=True)
        if not updated:
            return Response(
                {"code": 404, "message": "消息不存在"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response({"code": 200, "message": "已标记为已读"})


class NotificationAllReadView(APIView):
    def post(self, request):
        userrole = (request.data.get("userrole") or request.query_params.get("userrole") or "").strip()
        if not userrole:
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                userrole = getattr(user, "username", "")
        if not userrole:
            return Response(
                {"code": 400, "message": "缺少 userrole"}, status=status.HTTP_400_BAD_REQUEST
            )
        count = Notification.objects.filter(userrole=userrole, is_read=False).update(
            is_read=True
        )
        return Response({"code": 200, "message": f"已标记 {count} 条为已读"})


# --------------------------------------------------------------------------- #
# 邮箱验证码 / 重置密码
# --------------------------------------------------------------------------- #
class SendCodeView(APIView):
    def post(self, request):
        email = (request.data.get("email") or "").strip()
        if not email:
            return Response(
                {"code": 400, "message": "请输入邮箱"}, status=status.HTTP_400_BAD_REQUEST
            )

        code = f"{random.randint(0, 999999):06d}"
        EmailCode.objects.filter(email=email, purpose="reset_password", used=False).update(
            used=True
        )
        EmailCode.objects.create(
            email=email,
            code=code,
            purpose="reset_password",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        send_mail(
            subject="【壁纸网站】找回密码验证码",
            message=f"你的验证码是 {code}，5 分钟内有效。如非本人操作请忽略。",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@wallpaper.local"),
            recipient_list=[email],
            fail_silently=True,
        )

        payload = {"code": 200, "message": "验证码已发送，请查收邮箱"}
        # 开发环境用控制台邮件后端时，直接把验证码带回来，方便本地调试
        if settings.DEBUG and "console" in getattr(settings, "EMAIL_BACKEND", ""):
            payload["dev_code"] = code
        return Response(payload)


class PasswordResetView(APIView):
    def post(self, request):
        email = (request.data.get("email") or "").strip()
        code = (request.data.get("code") or "").strip()
        new_password = request.data.get("new_password") or request.data.get("password") or ""

        if not email or not code or not new_password:
            return Response(
                {"code": 400, "message": "邮箱、验证码和新密码都不能为空"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(new_password) < 6:
            return Response(
                {"code": 400, "message": "密码至少 6 位"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record = (
            EmailCode.objects.filter(
                email=email,
                purpose="reset_password",
                used=False,
                expires_at__gt=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )
        if record is None or record.code != code:
            return Response(
                {"code": 400, "message": "验证码无效或已过期"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = SysUser.objects.filter(email=email).first()
        if user is None:
            return Response(
                {"code": 400, "message": "该邮箱未绑定任何账号"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.password = make_password(new_password)
        user.update_time = timezone.now()
        user.save(update_fields=["password", "update_time"])
        record.used = True
        record.save(update_fields=["used"])

        return Response({"code": 200, "message": "密码重置成功，请使用新密码登录"})


# --------------------------------------------------------------------------- #
# 浏览历史
# --------------------------------------------------------------------------- #
class UserHistoryView(ListAPIView):
    serializer_class = BrowseRecordSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        userrole = (self.request.query_params.get("userrole") or "").strip()
        queryset = BrowseRecord.objects.select_related("wallpaper")
        if not userrole:
            return queryset.none()
        return queryset.filter(userrole=userrole)
