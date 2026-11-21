from django.urls import path

from user.views import (
    LoginView,
    NotificationAllReadView,
    NotificationListView,
    NotificationReadView,
    PasswordResetView,
    RegisterView,
    SendCodeView,
    UserBanView,
    UserHistoryView,
    UserListView,
)

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("send-code/", SendCodeView.as_view(), name="send_code"),
    path("password-reset/", PasswordResetView.as_view(), name="password_reset"),
    # 用户管理
    path("users/", UserListView.as_view(), name="user_list"),
    path("users/<int:pk>/ban/", UserBanView.as_view(), name="user_ban"),
    # 消息通知
    path("notifications/", NotificationListView.as_view(), name="notification_list"),
    path(
        "notifications/all/read/",
        NotificationAllReadView.as_view(),
        name="notification_read_all",
    ),
    path(
        "notifications/<int:pk>/read/",
        NotificationReadView.as_view(),
        name="notification_read",
    ),
    # 浏览历史
    path("history/", UserHistoryView.as_view(), name="user_history"),
]
