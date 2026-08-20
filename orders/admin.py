"""
Orders App Admin Configuration

This file registers our Order and OrderItem models with Django's admin panel.
This allows you to view and manage orders through the admin interface.

Access the admin at: http://127.0.0.1:8000/admin/
"""

from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """
    Inline admin for OrderItems within an Order.
    
    This allows viewing and editing order items directly on the Order detail page.
    extra: Number of empty forms to show for adding new items
    readonly_fields: Fields that cannot be edited (calculated values)
    """
    model = OrderItem
    extra = 0  # Don't show empty forms by default
    readonly_fields = ['subtotal']
    fields = ['menu_item', 'quantity', 'price', 'special_instructions', 'subtotal']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Admin configuration for Order model.
    
    list_display: Columns shown in the order list
    list_filter: Filters for narrowing down orders
    search_fields: Fields that can be searched
    readonly_fields: Fields that cannot be edited (like timestamps)
    inlines: Related models to show inline (OrderItems)
    """
    list_display = ['id', 'user', 'restaurant', 'total_amount', 'status', 'created_at']
    list_filter = ['status', 'restaurant', 'created_at']
    search_fields = ['user__username', 'user__email', 'delivery_address']
    readonly_fields = ['created_at', 'updated_at', 'total_amount']
    inlines = [OrderItemInline]
    ordering = ['-created_at']  # Most recent orders first
    
    def save_model(self, request, obj, form, change):
        """
        Override save to recalculate total when order is modified.
        This ensures the total_amount stays accurate.
        """
        super().save_model(request, obj, form, change)
        obj.calculate_total()


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for OrderItem model.
    
    Usually accessed through the Order inline, but this provides a standalone view.
    """
    list_display = ['order', 'menu_item', 'quantity', 'price', 'subtotal']
    readonly_fields = ['subtotal']
    ordering = ['-order__created_at']
