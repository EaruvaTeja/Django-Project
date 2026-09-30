"""
Cart App API Serializers

Serializers in DRF convert between Python objects and JSON.

We have TWO categories:

READ serializers (Model -> JSON):
    Used for responses to GET /api/cart/.
    They expose nested info (menu_item, restaurant) so the frontend
    has everything it needs in one request.

WRITE serializers (JSON -> validated data):
    Used for POST /api/cart/add/ and PATCH /api/cart/items/<id>/.
    They validate incoming data but do NOT save models directly.
    The view handles saving logic (increment vs create, restaurant checks).

Design rules:
- Never expose raw cart_id or user_id to the client (ownership comes from JWT).
- Never expose another user's data (enforced at view level, not serializer).
- Price fields use LIVE MenuItem.price for CartItem (no snapshot here).
- Snapshot prices only happen later, in OrderItem.
"""

from rest_framework import serializers

from restaurants.models import MenuItem, Restaurant
from .models import Cart, CartItem


# ==================================================================
# NESTED READ SERIALIZERS
# ==================================================================

class CartMenuItemSerializer(serializers.ModelSerializer):
    """
    Minimal menu item info shown INSIDE a cart item.

    Why not use the full MenuItemSerializer from restaurants app?
        Because we don't need description, created_at, etc. in the cart.
        Only the fields the frontend needs to render a cart row.
    """
    class Meta:
        model = MenuItem
        fields = [
            'id',
            'name',
            'price',
            'image',
            'is_vegetarian',
            'category',
        ]
        read_only_fields = fields


class CartRestaurantSerializer(serializers.ModelSerializer):
    """
    Minimal restaurant info shown at the CART level.

    Includes `image` and `distance_km` so the frontend can:
      - Show the restaurant's cover
      - Compute the delivery fee client-side (mirror of the backend tier)
    """
    class Meta:
        model = Restaurant
        fields = [
            'id',
            'name',
            'cuisine_type',
            'delivery_time',
            'distance_km',      # <-- NEW
            'image',
        ]
        read_only_fields = fields


# ==================================================================
# CART READ SERIALIZERS
# ==================================================================

class CartItemReadSerializer(serializers.ModelSerializer):
    """
    Serialize ONE CartItem for reading.

    Includes:
    - Nested menu_item info (via CartMenuItemSerializer)
    - subtotal (calculated @property on CartItem)
    - timestamps

    Does NOT include:
    - The raw `cart` FK (implied by context)
    - The raw `menu_item` FK id (we show nested object instead)
    """
    menu_item = CartMenuItemSerializer(read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = CartItem
        fields = [
            'id',
            'menu_item',
            'quantity',
            'special_instructions',
            'subtotal',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class CartReadSerializer(serializers.ModelSerializer):
    """
    Serialize the FULL Cart for reading (GET /api/cart/).

    Includes:
    - Nested restaurant info (or null if cart is empty)
    - Nested items list
    - item_count and total (@property on Cart)
    - timestamps

    Does NOT include:
    - The raw `user` FK (security — client only sees their own cart).
    """
    restaurant = CartRestaurantSerializer(read_only=True)
    items = CartItemReadSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Cart
        fields = [
            'id',
            'restaurant',
            'items',
            'item_count',
            'total',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


# ==================================================================
# CART WRITE SERIALIZERS
# ==================================================================

class CartAddItemSerializer(serializers.Serializer):
    """
    Validate input for POST /api/cart/add/.

    Expected JSON body:
        {
            "menu_item_id": 12,
            "quantity": 2,
            "special_instructions": "Extra spicy"   # optional
        }

    This is a plain Serializer (NOT ModelSerializer) because:
        The view does NOT call .save() directly.
        The view implements custom logic:
            - Find/create the user's cart
            - Enforce one-restaurant-per-cart
            - Either CREATE a new CartItem or INCREMENT existing quantity
        Those decisions do not belong inside a serializer.

    Validation performed here:
        1. menu_item_id refers to an existing MenuItem
        2. The MenuItem is currently available
        3. The MenuItem's restaurant is active
    """

    menu_item_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)
    special_instructions = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
    )

    def validate(self, attrs):
        """
        Cross-field validation.

        We inject the resolved MenuItem object into the validated data
        under the key 'menu_item'. The view will use it directly,
        avoiding a second DB query.
        """
        menu_item_id = attrs['menu_item_id']

        try:
            menu_item = (
                MenuItem.objects
                .select_related('restaurant')
                .get(id=menu_item_id)
            )
        except MenuItem.DoesNotExist:
            raise serializers.ValidationError({
                'menu_item_id': (
                    f"Menu item with id {menu_item_id} does not exist."
                )
            })

        if not menu_item.is_available:
            raise serializers.ValidationError({
                'menu_item_id': (
                    "This menu item is currently unavailable."
                )
            })

        if not menu_item.restaurant.is_active:
            raise serializers.ValidationError({
                'menu_item_id': (
                    "This restaurant is not currently accepting orders."
                )
            })

        # Attach resolved object for the view (not a DB field).
        attrs['menu_item'] = menu_item

        return attrs


class CartItemUpdateSerializer(serializers.ModelSerializer):
    """
    Validate input for PATCH /api/cart/items/<cart_item_id>/.

    Allowed fields:
        - quantity
        - special_instructions

    Forbidden (must not be modifiable by customer):
        - cart
        - menu_item
        - anything ownership-related

    Both fields are OPTIONAL so a PATCH may include only one of them.
    """

    quantity = serializers.IntegerField(min_value=1, required=False)

    class Meta:
        model = CartItem
        fields = [
            'quantity',
            'special_instructions',
        ]
        extra_kwargs = {
            'special_instructions': {'required': False},
        }