from django.http import JsonResponse
from django.views import View
from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
import json
from user.models import SysUser
from user.serializers import SysUserSerializer


class LoginView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")
        except Exception as e:
            return JsonResponse({"code": 400, "message": "请求数据格式错误"})

        # 前端 401 时会带 refresh 来这里换新的 access token
        if data.get("refresh") and not username:
            try:
                refresh = RefreshToken(data["refresh"])
            except TokenError:
                return JsonResponse({"code": 401, "message": "刷新凭证无效或已过期"})
            return JsonResponse(
                {"code": 200, "access": str(refresh.access_token), "refresh": str(refresh)}
            )

        if not username or not password:
            return JsonResponse({"code": 400, "message": "用户名或密码不能为空"})

        try:
            user = SysUser.objects.get(username=username)
            if not check_password(password, user.password):
                return JsonResponse({"code": 400, "message": "用户名或密码错误"})

            # 使用 RefreshToken 生成 token
            refresh = RefreshToken.for_user(user)
            refresh["username"] = user.username
            token = {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        except SysUser.DoesNotExist:
            return JsonResponse({"code": 400, "message": "用户名或密码错误"})

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
        try:
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")
        except Exception as e:
            return JsonResponse({"code": 400, "message": "请求数据格式错误"})

        # 检查参数是否为空
        if not username or not password:
            return JsonResponse({"code": 400, "message": "用户名或密码不能为空"})

        # 检查用户名是否已存在
        if SysUser.objects.filter(username=username).exists():
            return JsonResponse({"code": 400, "message": "用户名已存在"})

        # 创建用户
        try:
            user = SysUser.objects.create(
                username=username,
                password=make_password(password),  # 加密密码
            )
            return JsonResponse(
                {"code": 200, "message": "注册成功", "user_id": user.id}
            )
        except Exception as e:
            return JsonResponse({"code": 500, "message": "注册失败", "error": str(e)})
