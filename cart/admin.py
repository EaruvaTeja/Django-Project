"""
Cart App Admin Configuration

This file registers the Cart and CartItem models with Django's admin panel.

Access the admin at: http://127.0.0.1:8000/admin/

Design:
- CartItem is shown INLINE inside Cart (so you can see items on the cart page).
- CartItem is ALSO registered standalone for cross-cart browsing.
- Read-only fields include calculated properties (subtotal, total, item_count).
- raw_id_fields prevent loading thousands of users into a dropdown.
"""

from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    """
    Inline admin for CartItems inside the Cart detail page.

    Why TabularInline?
        It renders as a compact table row per item,
        which is ideal for simple child models like CartItem.

    Why extra = 0?
        We don't want empty blank forms cluttering the page.
        The admin can click "Add another Cart item" if needed.
    """
    model = CartItem
    extra = 0
    # These are calculated @property fields, so they must be read-only.
    readonly_fields = ['subtotal', 'created_at', 'updated_at']
    fields = [
        'menu_item',
        'quantity',
        'special_instructions',
        'subtotal',
        'created_at',
        'updated_at',
    ]


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Cart model.

    list_display:
        Columns shown in the cart list view.
        - item_count and total are @property methods, so they are
          calculated dynamically (not stored in the database).

    list_filter:
        Right-side filter panel to narrow carts by restaurant or date.

    search_fields:
        Fields that can be searched by the search box.
        The double underscore (__) traverses relationships.

    raw_id_fields:
        Instead of a dropdown of ALL users (could be thousands),
        show a search input for the user id.

    readonly_fields:
        Timestamps and calculated properties should never be edited.

    inlines:
        Embed CartItemInline so items appear on the Cart detail page.
    """
    list_display = [
        'id',
        'user',
        'restaurant',
        'item_count',
        'total',
        'updated_at',
    ]
    list_filter = [
        'restaurant',
        'created_at',
        'updated_at',
    ]
    search_fields = [
        'user__username',
        'user__email',
        'restaurant__name',
    ]
    raw_id_fields = ['user']
    readonly_fields = [
        'created_at',
        'updated_at',
        'item_count',
        'total',
    ]
    inlines = [CartItemInline]
    ordering = ['-updated_at']

    # ------------------------------------------------------------------
    # Custom list columns for calculated properties
    # ------------------------------------------------------------------

    @admin.display(description='Items')
    def item_count(self, obj):
        """
        Display the total quantity of items in the cart.
        Pulled from the @property on the Cart model.
        """
        return obj.item_count

    @admin.display(description='Total')
    def total(self, obj):
        """
        Display the cart's total value.
        Pulled from the @property on the Cart model.
        """
        return obj.total


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """
    Standalone admin for CartItem.

    This is useful when browsing ALL cart items across users —
    for example, finding every cart that contains a specific menu item.

    The Cart inline view (via CartAdmin) is the primary editing path.
    """
    list_display = [
        'id',
        'cart',
        'menu_item',
        'quantity',
        'subtotal',
        'created_at',
    ]
    list_filter = [
        'menu_item__restaurant',
        'menu_item__category',
        'created_at',
    ]
    search_fields = [
        'cart__user__username',
        'menu_item__name',
    ]
    raw_id_fields = ['cart', 'menu_item']
    readonly_fields = [
        'subtotal',
        'created_at',
        'updated_at',
    ]
    ordering = ['-created_at']

    @admin.display(description='Subtotal')
    def subtotal(self, obj):
        """
        Display the CartItem subtotal (current price × quantity).
        """
        return obj.subtotal
    