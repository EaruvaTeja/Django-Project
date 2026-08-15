from django.urls import path
from . import views

app_name = 'meals'

urlpatterns = [
    path('', views.meal_list, name='meal_list'),
    path('meal/<int:meal_id>/', views.meal_detail, name='meal_detail'),
    path('add-to-cart/<int:meal_id>/', views.add_to_cart, name='add_to_cart'),
    path('toggle-favorite/<int:meal_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('favorites/', views.user_favorites, name='user_favorites'),
]