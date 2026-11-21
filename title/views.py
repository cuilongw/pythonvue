from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.views import APIView
from rest_framework.response import Response

from user.permissions import IsAdmin

from .models import CategoryItem, CategoryList, NavigationItem
from .serializers import (
    CategoryItemSerializer,
    CategoryListSerializer,
    NavigationItemSerializer,
)


class NavigationBarView(APIView):
    """壁纸首页头部导航栏接口视图"""

    def get(self, request):
        navigation_items = NavigationItem.objects.all()
        serializer = NavigationItemSerializer(navigation_items, many=True)
        return Response(serializer.data)


class CategoryItemView(ListCreateAPIView):
    """分类项列表 + 新增（写操作仅管理员）"""

    queryset = CategoryItem.objects.all()
    serializer_class = CategoryItemSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAdmin()]
        return []


class CategoryItemDetailView(RetrieveUpdateDestroyAPIView):
    """分类项详情 / 修改 / 删除（写操作仅管理员）"""

    queryset = CategoryItem.objects.all()
    serializer_class = CategoryItemSerializer

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH", "DELETE"):
            return [IsAdmin()]
        return []


class CategoryListView(APIView):
    """分类列表接口视图"""

    def get(self, request):
        category_items = CategoryList.objects.all()
        serializer = CategoryListSerializer(category_items, many=True)
        return Response(serializer.data)
