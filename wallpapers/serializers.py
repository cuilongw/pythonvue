from rest_framework import serializers
from .models import Wallpaper
from rest_framework.pagination import PageNumberPagination


class WallpaperSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallpaper
        fields = "__all__"


class WallpaperPagination(PageNumberPagination):
    page_size = 9  # 每页显示的图片数量
    page_size_query_param = "page_size"  # 允许客户端通过查询参数指定每页数量
    max_page_size = 100  # 每页最大数量限制

    def get_page_size(self, request):
        # 前端传的是驼峰 pageSize，这里做一下兼容
        raw = request.query_params.get("pageSize")
        if raw:
            try:
                return min(int(raw), self.max_page_size)
            except (TypeError, ValueError):
                pass
        return super().get_page_size(request)
