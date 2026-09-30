from django.urls import path

from . import api_views


urlpatterns = [
    # Restaurant APIs
    path('',api_views.RestaurantListAPIView.as_view(),name='restaurant-list'),

    path('<int:pk>/',api_views.RestaurantDetailAPIView.as_view(),name='restaurant-detail'),

    # Restaurant Menu API
    path('<int:restaurant_id>/menu/',api_views.RestaurantMenuListAPIView.as_view(),name='restaurant-menu-list'),
    path('<int:restaurant_id>/menu/<int:pk>/',api_views.MenuItemDetailAPIView.as_view(),name='menu-item-detail'),
]

