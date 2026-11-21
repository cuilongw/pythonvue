from rest_framework import serializers

from DjangoProject2.pagination import StandardPagination  # noqa: F401  (便于统一从这里导入)
from .models import BrowseRecord, DownloadRecord, Favorite, Wallpaper


class WallpaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallpaper
        fields = "__all__"


class WallpaperPagination(StandardPagination):
    page_size = 9  # 每页显示的图片数量


class FavoriteSerializer(serializers.ModelSerializer):
    wallpaper = WallpaperSerializer(read_only=True)
    wallpaper_id = serializers.IntegerField(source="wallpaper.id", read_only=True)

    class Meta:
        model = Favorite
        fields = ["id", "wallpaper_id", "wallpaper", "created_at"]


class DownloadRecordSerializer(serializers.ModelSerializer):
    wallpaper = WallpaperSerializer(read_only=True)
    wallpaper_id = serializers.IntegerField(source="wallpaper.id", read_only=True)

    class Meta:
        model = DownloadRecord
        fields = ["id", "wallpaper_id", "wallpaper", "created_at"]


class BrowseRecordSerializer(serializers.ModelSerializer):
    wallpaper = WallpaperSerializer(read_only=True)
    wallpaper_id = serializers.IntegerField(source="wallpaper.id", read_only=True)

    class Meta:
        model = BrowseRecord
        fields = ["id", "wallpaper_id", "wallpaper", "created_at"]
