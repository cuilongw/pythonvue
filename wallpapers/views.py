import json

from PIL import Image
from django.core.files.storage import default_storage
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTStatelessUserAuthentication

from DjangoProject2.pagination import StandardPagination
from user.models import Notification
from user.permissions import IsAdmin

from .models import BrowseRecord, DownloadRecord, Favorite, Wallpaper
from .serializers import (
    DownloadRecordSerializer,
    FavoriteSerializer,
    WallpaperPagination,
    WallpaperSerializer,
)


# --------------------------------------------------------------------------- #
# 小工具
# --------------------------------------------------------------------------- #
def parse_tags(raw_tags):
    """把前端传来的 tags 统一成 list，兼容 JSON 字符串和逗号分隔字符串。"""
    if not raw_tags:
        return []
    if isinstance(raw_tags, (list, tuple)):
        return [str(tag).strip() for tag in raw_tags if str(tag).strip()]
    try:
        value = json.loads(raw_tags)
        if isinstance(value, list):
            return [str(tag).strip() for tag in value if str(tag).strip()]
        if isinstance(value, str):
            return [value.strip()] if value.strip() else []
    except (TypeError, ValueError):
        pass
    return [tag.strip() for tag in str(raw_tags).split(",") if tag.strip()]


def get_userrole(request):
    """从 query / body / 已登录用户里取当前用户名。"""
    role = request.query_params.get("userrole")
    if not role:
        try:
            role = request.data.get("userrole")
        except Exception:
            role = None
    if not role:
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            role = getattr(user, "username", "")
    return (role or "").strip()


def notify(userrole, message, notification_type="system", title=""):
    if not userrole:
        return
    Notification.objects.create(
        userrole=userrole,
        title=title,
        message=message,
        notification_type=notification_type,
    )


def inspect_image(image_file):
    """读取图片尺寸并自动判断壁纸类型。"""
    try:
        with Image.open(image_file) as img:
            width, height = img.size
    except Exception as exc:
        raise ValueError(f"图片处理失败: {exc}")

    aspect_ratio = width / height
    if 0.8 <= aspect_ratio <= 1.2 and max(width, height) <= 2048:
        media_type = "avatar"
    elif aspect_ratio > 1.2 and width >= height and width >= 1920:
        media_type = "computer"
    elif aspect_ratio < 0.8 and height > width and height >= 1920:
        media_type = "mobile"
    else:
        media_type = "unknown"
    return width, height, media_type


def apply_wallpaper_filters(queryset, request):
    """列表接口共用的筛选逻辑：标题 / 标签 / 分类 / 类型 / 分辨率。"""
    params = request.query_params

    media_type = params.get("media_type")
    if media_type:
        queryset = queryset.filter(media_type=media_type)

    tags = params.get("tags")
    if tags:
        queryset = queryset.filter(tags__icontains=tags)

    title = params.get("title")
    if title:
        queryset = queryset.filter(title__icontains=title)

    category = params.get("category")
    if category:
        queryset = queryset.filter(category=category)

    resolution = params.get("resolution")
    if resolution == "1K":
        queryset = queryset.filter(resolution__lt="1280x720")
    elif resolution == "2K":
        queryset = queryset.filter(
            resolution__gte="1280x720", resolution__lt="2560x1440"
        )
    elif resolution == "4K":
        queryset = queryset.filter(
            resolution__gte="2560x1440", resolution__lt="3840x2160"
        )
    elif resolution == "8K":
        queryset = queryset.filter(
            resolution__gte="3840x2160", resolution__lt="7680x4320"
        )
    elif resolution == "其他":
        queryset = queryset.filter(resolution__gte="7680x4320")
    return queryset


# --------------------------------------------------------------------------- #
# 上传
# --------------------------------------------------------------------------- #
class BulkUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    authentication_classes = [JWTStatelessUserAuthentication]

    def post(self, request):
        files = request.FILES.getlist("images")
        if not files:
            raise ValidationError({"images": "请至少选择一张图片"})

        userrole = get_userrole(request)
        created_data = []

        for img in files:
            try:
                width, height, media_type = inspect_image(img)

                wallpaper = Wallpaper.objects.create(
                    title=request.POST.get("title") or img.name.rsplit(".", 1)[0],
                    image=img,
                    image_url=img,
                    category=request.POST.get("category", "未分类"),
                    description=request.POST.get("description", ""),
                    media_type=media_type,
                    tags=parse_tags(request.POST.get("tags")),
                    resolution=f"{width}x{height}",
                    userrole=userrole,
                    status="pending",
                )
                created_data.append(WallpaperSerializer(wallpaper).data)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        notify(
            userrole,
            f"你上传的 {len(created_data)} 张壁纸已提交，等待管理员审核。",
            notification_type="audit",
            title="壁纸已提交审核",
        )
        return Response(
            {"count": len(created_data), "results": created_data},
            status=status.HTTP_201_CREATED,
        )


# --------------------------------------------------------------------------- #
# 公开列表 / 搜索
# --------------------------------------------------------------------------- #
class WallpaperListView(ListAPIView):
    """壁纸分页，只返回审核通过的壁纸。"""

    serializer_class = WallpaperSerializer
    pagination_class = WallpaperPagination

    def get_queryset(self):
        queryset = Wallpaper.objects.filter(status="approved")
        return apply_wallpaper_filters(queryset, self.request)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["debug"] = {
            "page_size": self.pagination_class.page_size,
            "total_items": self.get_queryset().count(),
        }
        return response


class WallpaperSearchView(ListAPIView):
    """按标签搜索（自动补全用），返回数组，不分页。"""

    serializer_class = WallpaperSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Wallpaper.objects.filter(status="approved")
        tags = self.request.query_params.get("tags")
        if tags:
            queryset = queryset.filter(tags__icontains=tags)
        return queryset


# --------------------------------------------------------------------------- #
# 下载
# --------------------------------------------------------------------------- #
class WallpaperDownloadView(APIView):
    def post(self, request, pk):
        try:
            wallpaper = Wallpaper.objects.get(pk=pk)
        except Wallpaper.DoesNotExist:
            return Response({"error": "壁纸不存在"}, status=status.HTTP_404_NOT_FOUND)

        wallpaper.downloads += 1
        wallpaper.save(update_fields=["downloads"])

        userrole = get_userrole(request)
        if userrole:
            DownloadRecord.objects.create(userrole=userrole, wallpaper=wallpaper)
            BrowseRecord.objects.create(userrole=userrole, wallpaper=wallpaper)

        return Response(
            {
                "code": 200,
                "message": "下载次数更新成功",
                "downloads": wallpaper.downloads,
            },
            status=status.HTTP_200_OK,
        )


# --------------------------------------------------------------------------- #
# 收藏
# --------------------------------------------------------------------------- #
class FavoriteView(APIView):
    """单张壁纸的收藏状态：GET 查询、POST 收藏、DELETE 取消。"""

    def get_object(self, pk):
        try:
            return Wallpaper.objects.get(pk=pk)
        except Wallpaper.DoesNotExist:
            return None

    def get(self, request, pk):
        wallpaper = self.get_object(pk)
        if wallpaper is None:
            return Response({"error": "壁纸不存在"}, status=status.HTTP_404_NOT_FOUND)

        userrole = get_userrole(request)
        favorite = bool(
            userrole
            and Favorite.objects.filter(userrole=userrole, wallpaper=wallpaper).exists()
        )
        return Response({"favorite": favorite, "is_favorite": favorite})

    def post(self, request, pk):
        wallpaper = self.get_object(pk)
        if wallpaper is None:
            return Response({"error": "壁纸不存在"}, status=status.HTTP_404_NOT_FOUND)

        userrole = get_userrole(request)
        if not userrole:
            return Response(
                {"code": 400, "message": "缺少 userrole"}, status=status.HTTP_400_BAD_REQUEST
            )

        Favorite.objects.get_or_create(userrole=userrole, wallpaper=wallpaper)
        return Response(
            {"code": 200, "message": "收藏成功", "favorite": True},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        userrole = get_userrole(request)
        if not userrole:
            return Response(
                {"code": 400, "message": "缺少 userrole"}, status=status.HTTP_400_BAD_REQUEST
            )

        deleted, _ = Favorite.objects.filter(userrole=userrole, wallpaper_id=pk).delete()
        if not deleted:
            return Response(
                {"code": 200, "message": "尚未收藏", "favorite": False},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"code": 200, "message": "已取消收藏", "favorite": False},
            status=status.HTTP_200_OK,
        )


class FavoriteListView(ListAPIView):
    """我的收藏，支持 /favorites/ 和 /favorites/<media_type>/。"""

    serializer_class = FavoriteSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        userrole = get_userrole(self.request)
        queryset = Favorite.objects.select_related("wallpaper").filter(
            wallpaper__status="approved"
        )
        if not userrole:
            return queryset.none()
        queryset = queryset.filter(userrole=userrole)

        media_type = self.kwargs.get("media_type") or self.request.query_params.get(
            "media_type"
        )
        if media_type:
            queryset = queryset.filter(wallpaper__media_type=media_type)

        title = self.request.query_params.get("title")
        if title:
            queryset = queryset.filter(wallpaper__title__icontains=title)

        tags = self.request.query_params.get("tags")
        if tags:
            queryset = queryset.filter(wallpaper__tags__icontains=tags)

        return queryset


# --------------------------------------------------------------------------- #
# 下载历史
# --------------------------------------------------------------------------- #
class DownloadHistoryView(ListAPIView):
    serializer_class = DownloadRecordSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        userrole = get_userrole(self.request)
        queryset = DownloadRecord.objects.select_related("wallpaper")
        if not userrole:
            return queryset.none()
        queryset = queryset.filter(userrole=userrole)

        media_type = self.request.query_params.get("media_type")
        if media_type:
            queryset = queryset.filter(wallpaper__media_type=media_type)

        title = self.request.query_params.get("title")
        if title:
            queryset = queryset.filter(wallpaper__title__icontains=title)

        tags = self.request.query_params.get("tags")
        if tags:
            queryset = queryset.filter(wallpaper__tags__icontains=tags)

        return queryset


class DownloadHistoryDeleteView(APIView):
    def delete(self, request, pk):
        deleted, _ = DownloadRecord.objects.filter(pk=pk).delete()
        if not deleted:
            return Response(
                {"code": 404, "message": "记录不存在"}, status=status.HTTP_404_NOT_FOUND
            )
        return Response({"code": 200, "message": "已删除下载记录"})


# --------------------------------------------------------------------------- #
# 后台：待审核 / 编辑 / 审核 / 删除
# --------------------------------------------------------------------------- #
class PendingWallpaperView(ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = WallpaperSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = Wallpaper.objects.filter(status="pending")
        return apply_wallpaper_filters(queryset, self.request)


class WallpaperEditView(APIView):
    permission_classes = [IsAdmin]
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    def patch(self, request, pk):
        try:
            wallpaper = Wallpaper.objects.get(pk=pk)
        except Wallpaper.DoesNotExist:
            return Response({"error": "壁纸不存在"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        for field in ("title", "description", "category", "media_type", "resolution"):
            if field in data:
                setattr(wallpaper, field, data.get(field))

        if "tags" in data:
            wallpaper.tags = parse_tags(data.get("tags"))

        image = request.FILES.get("image")
        if image is not None:
            try:
                width, height, media_type = inspect_image(image)
            except ValueError as exc:
                return Response(
                    {"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
                )
            wallpaper.image = image
            wallpaper.save()
            # 让压缩图字段指向同一个文件，避免再复制一份
            wallpaper.image_url = wallpaper.image.name
            wallpaper.resolution = f"{width}x{height}"
            wallpaper.media_type = media_type

        wallpaper.save()
        return Response(
            {"code": 200, "message": "保存成功", "data": WallpaperSerializer(wallpaper).data}
        )


class WallpaperReviewView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            wallpaper = Wallpaper.objects.get(pk=pk)
        except Wallpaper.DoesNotExist:
            return Response({"error": "壁纸不存在"}, status=status.HTTP_404_NOT_FOUND)

        action = (request.data.get("action") or "").lower()
        raw_status = (request.data.get("status") or "").lower()

        if action == "approve" or raw_status == "approved":
            new_status = "approved"
            message = "审核通过"
        elif action == "reject" or raw_status == "rejected":
            new_status = "rejected"
            message = "已驳回"
        elif raw_status in ("pending", "approved", "rejected"):
            new_status = raw_status
            message = "状态已更新"
        else:
            return Response(
                {"error": "无效的审核动作"}, status=status.HTTP_400_BAD_REQUEST
            )

        wallpaper.status = new_status
        wallpaper.review_remark = request.data.get("remark", "")
        wallpaper.reviewed_at = timezone.now()
        wallpaper.save(update_fields=["status", "review_remark", "reviewed_at"])

        if new_status == "approved":
            notify(
                wallpaper.userrole,
                f"你上传的壁纸《{wallpaper.title}》审核通过。",
                notification_type="audit",
                title="审核通过",
            )
        elif new_status == "rejected":
            notify(
                wallpaper.userrole,
                f"你上传的壁纸《{wallpaper.title}》未通过审核。",
                notification_type="audit",
                title="审核未通过",
            )

        return Response(
            {
                "code": 200,
                "message": message,
                "status": wallpaper.status,
                "id": wallpaper.id,
            }
        )


class WallpaperDeleteView(APIView):
    permission_classes = [IsAdmin]

    def delete(self, request, pk):
        try:
            wallpaper = Wallpaper.objects.get(pk=pk)
        except Wallpaper.DoesNotExist:
            return Response({"error": "壁纸不存在"}, status=status.HTTP_404_NOT_FOUND)

        file_paths = {
            str(wallpaper.image).strip(),
            str(wallpaper.image_url).strip(),
        }
        file_paths.discard("")
        file_paths.discard("None")

        wallpaper.delete()
        for path in file_paths:
            try:
                default_storage.delete(path)
            except Exception:
                pass

        return Response({"code": 200, "message": "删除成功"})
