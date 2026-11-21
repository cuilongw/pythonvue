"""项目通用分页。

前端各页面读取分页数据的方式不太统一（`count` / `total` / `pagination.total` 都出现过），
所以这里一次把几种常见字段都返回，避免再对不上。
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "pageSize"
    max_page_size = 500

    def get_page_size(self, request):
        raw = request.query_params.get("pageSize") or request.query_params.get("page_size")
        if raw:
            try:
                return max(1, min(int(raw), self.max_page_size))
            except (TypeError, ValueError):
                pass
        return self.page_size

    def get_paginated_response(self, data):
        total = self.page.paginator.count
        page = self.page.number
        size = self.page.paginator.per_page
        return Response(
            {
                "count": total,
                "total": total,
                "page": page,
                "pageSize": size,
                "pagination": {
                    "total": total,
                    "total_count": total,
                    "page": page,
                    "page_size": size,
                },
                "results": data,
            }
        )
