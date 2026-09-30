"""
Restaurants App Admin Configuration

This file registers our models with Django's built-in admin panel.
The admin panel allows you to manage restaurants and menu items through a web interface.

Access the admin at: http://127.0.0.1:8000/admin/
(You'll need to create a superuser first: python manage.py createsuperuser)
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Restaurant, MenuItem


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    """
    Admin configuration for Restaurant model.

    list_display: Columns shown in the list view
    list_filter: Filters available on the right sidebar
    search_fields: Fields that can be searched
    list_editable: Fields that can be edited directly in the list view
    fieldsets: Grouped sections shown in the detail form
    """

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = [
        'name',
        'image_thumbnail',
        'cuisine_type',
        'rating',
        'delivery_time',
        'distance_km',
        'is_active',
        'created_at',
    ]
    list_filter = ['is_active', 'cuisine_type', 'rating']
    search_fields = ['name', 'description', 'address', 'cuisine_type']
    list_editable = ['is_active', 'rating', 'distance_km']
    ordering = ['-rating', 'name']

    # ------------------------------------------------------------------
    # Detail form — grouped into collapsible sections
    # ------------------------------------------------------------------
    fieldsets = [
        ('Basic Info', {
            'fields': ['name', 'description', 'cuisine_type']
        }),
        ('Contact & Location', {
            'fields': ['address']
        }),
        ('Delivery & Rating', {
            'fields': ['rating', 'delivery_time', 'distance_km', 'is_active']
        }),
        ('Image', {
            'fields': ['image'],
            'description': (
                'Upload a cover image for this restaurant. '
                'Recommended: 800x450px, JPG or PNG.'
            ),
        }),
    ]

    # ------------------------------------------------------------------
    # Custom column — small thumbnail in the list view
    # ------------------------------------------------------------------
    @admin.display(description='Image')
    def image_thumbnail(self, obj):
        """
        Show a small thumbnail in the list view.
        Displays '—' when no image is set.
        """
        if obj.image:
            return format_html(
                '<img src="{}" style="height:40px;width:60px;'
                'object-fit:cover;border-radius:4px;border:1px solid #ddd;" />',
                obj.image.url,
            )
        return '—'


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for MenuItem model.
    """
    list_display = [
        'name',
        'restaurant',
        'category',
        'price',
        'rating',
        'rating_count',
        'is_vegetarian',
        'is_available',
    ]
    list_filter = [
        'is_available',
        'is_vegetarian',
        'category',
        'restaurant',
    ]
    search_fields = ['name', 'description']
    list_editable = ['is_available', 'price', 'rating']
    ordering = ['restaurant', 'category', 'name']