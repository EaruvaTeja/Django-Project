"""
Orders App Serializers

Serializers in Django REST Framework (DRF) convert complex data types
(like Django model instances) to/from JSON format.

Think of a serializer as a bridge between:
- Python objects (Django models) <-> JSON (for API requests/responses)

This file defines serializers for the Order API endpoint.
"""

from rest_framework import serializers
from .models import Order, OrderItem


class OrderItemSerializer(serializers.Serializer):
    """
    Serializer for individual order items.
    
    This is NOT a ModelSerializer because we're receiving raw data
    from the API request, not serializing existing database records.
    
    Fields expected in API request:
    - menu_item_id: ID of the menu item being ordered
    - quantity: How many of this item
    - special_instructions: Optional notes for this item
    """
    menu_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    special_instructions = serializers.CharField(required=False, allow_blank=True)
    
    def validate_menu_item_id(self, value):
        """
        Custom validation to ensure the menu item exists.
        This method is automatically called by DRF when validating menu_item_id.
        """
        from restaurants.models import MenuItem
        
        try:
            MenuItem.objects.get(id=value)
        except MenuItem.DoesNotExist:
            raise serializers.ValidationError(f"Menu item with id {value} does not exist")
        
        return value
    
    def validate_quantity(self, value):
        """Ensure quantity is positive."""
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value


class OrderSerializer(serializers.Serializer):
    """
    Serializer for placing an order via API.
    
    This serializer validates the incoming JSON data for an order.
    It expects:
    - items: List of OrderItemSerializer data
    - delivery_address: String address for delivery
    - notes: Optional order notes
    
    Note: We're using a regular Serializer instead of ModelSerializer
    because we want fine-grained control over the validation and creation process.
    For a more complex app, you might use nested ModelSerializers.
    """
    items = serializers.ListField(
        child=OrderItemSerializer(),
        allow_empty=False,
        error_messages={'empty': 'You must order at least one item'}
    )
    delivery_address = serializers.CharField(max_length=500)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_items(self, value):
        """
        Validate that all items are from the same restaurant.
        This is called after individual item validation.
        """
        from restaurants.models import MenuItem
        
        if not value:
            raise serializers.ValidationError("Order must have at least one item")
        
        # Get the restaurant from the first item
        first_item = value[0]
        first_menu_item = MenuItem.objects.get(id=first_item['menu_item_id'])
        restaurant = first_menu_item.restaurant
        
        # Check all other items are from the same restaurant
        for item in value[1:]:
            menu_item = MenuItem.objects.get(id=item['menu_item_id'])
            if menu_item.restaurant != restaurant:
                raise serializers.ValidationError(
                    f"All items must be from the same restaurant. "
                    f"'{menu_item.name}' is from a different restaurant."
                )
        
        return value
    
    def validate_delivery_address(self, value):
        """Ensure delivery address is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Delivery address cannot be empty")
        return value
