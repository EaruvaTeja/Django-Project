"""
Restaurants App Admin Configuration

This file registers our models with Django's built-in admin panel.
The admin panel allows you to manage restaurants and menu items through a web interface.

Access the admin at: http://127.0.0.1:8000/admin/
(You'll need to create a superuser first: python manage.py createsuperuser)
"""

from django.contrib import admin
from .models import Restaurant, MenuItem


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    """
    Admin configuration for Restaurant model.
    
    list_display: Columns shown in the list view
    list_filter: Filters available on the right sidebar
    search_fields: Fields that can be searched
    list_editable: Fields that can be edited directly in the list view
    """
    list_display = ['name', 'cuisine_type', 'rating', 'delivery_time', 'is_active', 'created_at']
    list_filter = ['is_active', 'cuisine_type', 'rating']
    search_fields = ['name', 'description', 'address', 'cuisine_type']
    list_editable = ['is_active', 'rating']
    ordering = ['-rating', 'name']


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for MenuItem model.
    
    This allows managing menu items with filtering by restaurant and category.
    """
    list_display = ['name', 'restaurant', 'category', 'price', 'is_vegetarian', 'is_available']
    list_filter = ['is_available', 'is_vegetarian', 'category', 'restaurant']
    search_fields = ['name', 'description']
    list_editable = ['is_available', 'price']
    ordering = ['restaurant', 'category', 'name']
