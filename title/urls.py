from django.urls import path
from .views import (
    CategoryItemDetailView,
    CategoryItemView,
    CategoryListView,
    NavigationBarView,
)

urlpatterns = [
    path("navigation-bar/", NavigationBarView.as_view(), name="navigation_bar"),
    path("category-item/", CategoryItemView.as_view(), name="category_item"),
    path(
        "category-item/<int:pk>/",
        CategoryItemDetailView.as_view(),
        name="category_item_detail",
    ),
    path("category-list/", CategoryListView.as_view(), name="category_list"),
]
