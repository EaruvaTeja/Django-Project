"""
Restaurants App API Serializers

Serializers for Restaurant + MenuItem.
"""

from rest_framework import serializers

from .models import Restaurant, MenuItem


# ==================================================================
# RESTAURANT
# ==================================================================

class RestaurantSerializer(serializers.ModelSerializer):
    """
    Full restaurant serializer used by both list and detail endpoints.

    Exposes `distance_km` so the frontend can compute the delivery fee
    client-side (mirror of the backend tier logic).
    """
    class Meta:
        model = Restaurant
        fields = [
            'id',
            'name',
            'description',
            'address',
            'cuisine_type',
            'rating',
            'delivery_time',
            'distance_km',      # <-- NEW
            'image',
            'is_active',
            'created_at',
        ]


# ==================================================================
# MENU ITEM
# ==================================================================

class MenuItemSerializer(serializers.ModelSerializer):
    """
    Menu item for a specific restaurant.
    """
    class Meta:
        model = MenuItem
        fields = [
            'id',
            'restaurant',
            'name',
            'description',
            'price',
            'image',
            'is_vegetarian',
            'is_available',
            'category',
            'rating',
            'rating_count',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'restaurant',
            'created_at',
        ]


# ==================================================================
# MENU ITEM + NESTED RESTAURANT (used by /api/menu-items/)
# ==================================================================

class MenuItemWithRestaurantSerializer(serializers.ModelSerializer):
    """
    Menu item with its full restaurant nested.
    Used by the /api/menu-items/ endpoint (home showcase).
    """
    restaurant = RestaurantSerializer(read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id',
            'restaurant',
            'name',
            'description',
            'price',
            'image',
            'is_vegetarian',
            'is_available',
            'category',
            'rating',
            'rating_count',
            'created_at',
        ]