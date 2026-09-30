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
    """
    model = OrderItem
    extra = 0
    readonly_fields = ['subtotal']
    fields = [
        'menu_item',
        'quantity',
        'price',
        'special_instructions',
        'subtotal',
    ]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Admin configuration for Order model.
    """
    list_display = [
        'id',
        'user',
        'restaurant',
        'subtotal',
        'delivery_fee',
        'gst_amount',
        'total_amount',
        'status',
        'created_at',
    ]
    list_filter = ['status', 'restaurant', 'created_at']
    search_fields = ['user__username', 'user__email', 'delivery_address']
    readonly_fields = [
        'subtotal',
        'delivery_fee',
        'gst_amount',
        'total_amount',
        'created_at',
        'updated_at',
    ]
    inlines = [OrderItemInline]
    ordering = ['-created_at']

    def save_related(self, request, form, formsets, change):
        """
        Recompute ALL money fields AFTER inlines (items) are saved.

        Uses Order.recompute_fees() which:
          1. Re-derives delivery_fee from restaurant.distance_km
          2. Recomputes subtotal + gst + total from the (now saved) items
        """
        super().save_related(request, form, formsets, change)
        form.instance.recompute_fees()


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for OrderItem model.
    """
    list_display = ['order', 'menu_item', 'quantity', 'price', 'subtotal']
    readonly_fields = ['subtotal']
    ordering = ['-order__created_at']