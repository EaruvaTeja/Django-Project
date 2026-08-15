from django.urls import path
from . import views

app_name = 'restaurants'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('restaurant-dashboard/', views.restaurant_dashboard, name='restaurant_dashboard'),
    path('restaurant-dashboard/<int:restaurant_id>/', views.restaurant_dashboard, name='restaurant_dashboard_for_restaurant'),
    path('manage-meals/', views.manage_meals, name='manage_meals'),
    path('manage-meals/<int:restaurant_id>/', views.manage_meals, name='manage_meals_for_restaurant'),
    path('add-meal/', views.add_meal, name='add_meal'),
    path('add-meal/<int:restaurant_id>/', views.add_meal, name='add_meal_for_restaurant'),
    path('edit-meal/<int:meal_id>/', views.edit_meal, name='edit_meal'),
    path('delete-meal/<int:meal_id>/', views.delete_meal, name='delete_meal'),
    path('toggle-meal/<int:meal_id>/', views.toggle_meal_availability, name='toggle_meal'),
    path('settings/', views.restaurant_settings, name='restaurant_settings'),
    path('settings/<int:restaurant_id>/', views.restaurant_settings, name='restaurant_settings_for_restaurant'),
    path('detail/<int:restaurant_id>/', views.restaurant_detail, name='restaurant_detail'),
    path('restaurant-orders/', views.restaurant_orders, name='restaurant_orders'),
    path('restaurant-orders/<int:restaurant_id>/', views.restaurant_orders, name='restaurant_orders_for_restaurant'),
]
