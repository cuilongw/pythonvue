from django.urls import path

from . import views

urlpatterns = [
    # 上传
    path("bulk-upload/", views.BulkUploadView.as_view(), name="bulk_upload"),
    # 列表 / 搜索
    path("wallpapers/page/", views.WallpaperListView.as_view(), name="wallpaper_page"),
    path(
        "wallpapers/search/",
        views.WallpaperSearchView.as_view(),
        name="wallpaper_search",
    ),
    # 下载
    path(
        "wallpapers/download/<int:pk>/",
        views.WallpaperDownloadView.as_view(),
        name="wallpaper_download",
    ),
    # 后台：待审核 / 编辑 / 审核 / 删除
    path(
        "wallpapers/pending/",
        views.PendingWallpaperView.as_view(),
        name="wallpaper_pending",
    ),
    path(
        "wallpapers/<int:pk>/edit/",
        views.WallpaperEditView.as_view(),
        name="wallpaper_edit",
    ),
    path(
        "wallpapers/<int:pk>/review/",
        views.WallpaperReviewView.as_view(),
        name="wallpaper_review",
    ),
    path(
        "wallpapers/<int:pk>/delete/",
        views.WallpaperDeleteView.as_view(),
        name="wallpaper_delete",
    ),
    # 收藏
    path("favorites/", views.FavoriteListView.as_view(), name="favorite_list"),
    path(
        "favorites/<str:media_type>/",
        views.FavoriteListView.as_view(),
        name="favorite_list_by_type",
    ),
    path(
        "favorite/<int:pk>/favorite/",
        views.FavoriteView.as_view(),
        name="favorite_toggle",
    ),
    # 下载历史
    path(
        "download-history/",
        views.DownloadHistoryView.as_view(),
        name="download_history",
    ),
    path(
        "download-history/<int:pk>/",
        views.DownloadHistoryDeleteView.as_view(),
        name="download_history_delete",
    ),
]
