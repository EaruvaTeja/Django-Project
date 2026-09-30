"""
Orders App API Serializers

Serializers for the new Orders REST API.

We have THREE categories:

READ serializers (Model -> JSON):
    OrderItemReadSerializer   - one OrderItem with nested menu_item
    OrderReadSerializer       - one Order with nested items + restaurant

NESTED read serializers (used inside the above):
    OrderMenuItemSerializer    - minimal menu item identity
    OrderRestaurantSerializer  - minimal restaurant identity

WRITE serializer (JSON -> validated data):
    OrderCreateSerializer      - validates delivery_address and notes
                                 (items come from the user's Cart, NOT the client)

Design rules:
- Never expose the raw `user` FK (ownership comes from the JWT token).
- `OrderItem.price` is the SNAPSHOT price at placement time, NOT the
  current MenuItem.price. That is why the nested menu serializer
  deliberately does NOT include the menu item's current price.
- The client cannot send items, quantities, or prices. Those come
  from the server-side Cart. This prevents tampering.
"""

from rest_framework import serializers

from restaurants.models import MenuItem, Restaurant
from .models import Order, OrderItem


# ==================================================================
# NESTED READ SERIALIZERS
# ==================================================================

class OrderMenuItemSerializer(serializers.ModelSerializer):
    """
    Minimal menu item identity shown inside an order item.
    Includes `is_available` so the frontend can detect items that have
    gone out of stock since the order was placed.
    """
    class Meta:
        model = MenuItem
        fields = [
            'id',
            'name',
            'image',
            'is_vegetarian',
            'category',
            'is_available',
        ]
        read_only_fields = fields


class OrderRestaurantSerializer(serializers.ModelSerializer):
    """
    Minimal restaurant identity shown at the ORDER level.

    Just enough for the frontend to render the header:
    "Order #5 from Paradise Biryani"
    """
    class Meta:
        model = Restaurant
        fields = [
            'id',
            'name',
            'cuisine_type',
            'is_active',
        ]
        read_only_fields = fields


# ==================================================================
# ORDER ITEM READ
# ==================================================================

class OrderItemReadSerializer(serializers.ModelSerializer):
    """
    Serialize ONE OrderItem for reading.

    Fields:
    - menu_item: nested identity of what was ordered
    - quantity: how many were ordered
    - price: SNAPSHOT price at the time of order (from OrderItem.price)
    - special_instructions: any customer notes for this item
    - subtotal: calculated @property (price × quantity)

    The `price` here is NOT the live menu price. It's the permanent
    snapshot stored when the order was placed.
    """
    menu_item = OrderMenuItemSerializer(read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'menu_item',
            'quantity',
            'price',
            'special_instructions',
            'subtotal',
        ]
        read_only_fields = fields


# ==================================================================
# ORDER READ
# ==================================================================

class OrderReadSerializer(serializers.ModelSerializer):
    """
    Serialize a FULL Order for reading.

    Includes:
    - Nested restaurant info (minimal)
    - Nested items list
    - status (machine-friendly: 'pending', 'confirmed', ...)
    - status_display (human-friendly: 'Pending', 'Confirmed', ...)
    - Full money breakdown (all frozen snapshots at order time):
        subtotal      - sum of item subtotals (pre-tax, pre-delivery)
        delivery_fee  - frozen delivery charge
        gst_amount    - frozen 18% GST
        total_amount  - subtotal + delivery_fee + gst_amount
    - timestamps

    Does NOT include:
    - The raw `user` FK — ownership is implicit from the JWT.
    """
    restaurant = OrderRestaurantSerializer(read_only=True)
    items = OrderItemReadSerializer(many=True, read_only=True)
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
    )

    class Meta:
        model = Order
        fields = [
            'id',
            'restaurant',
            'status',
            'status_display',
            'subtotal',         # <-- NEW
            'delivery_fee',     # <-- NEW
            'gst_amount',       # <-- NEW
            'total_amount',
            'delivery_address',
            'notes',
            'items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


# ==================================================================
# ORDER CREATE (INPUT ONLY)
# ==================================================================

class OrderCreateSerializer(serializers.Serializer):
    """
    Validate input for POST /api/orders/.

    Expected JSON body:
        {
            "delivery_address": "123 Main St, City",
            "notes": "Please ring the bell"   # optional
        }

    IMPORTANT: This serializer does NOT accept an `items` field.
    The items are read from the authenticated user's Cart on the
    server side. The client can only tell us WHERE to deliver and
    optionally add notes — never WHAT to order or at WHAT price.

    This is a plain Serializer (not ModelSerializer) because the
    view orchestrates the actual Order creation:
        - Read request.user.cart
        - Validate the cart contents
        - Create Order + OrderItems with snapshot prices
        - Clear the cart
    The serializer's job is only to validate shape and content
    of the two fields we accept from the client.
    """

    delivery_address = serializers.CharField(
        max_length=500,
        allow_blank=False,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )

    def validate_delivery_address(self, value):
        """
        Ensure the delivery address is not just whitespace.
        """
        if not value.strip():
            raise serializers.ValidationError(
                "Delivery address cannot be empty."
            )
        return value.strip()