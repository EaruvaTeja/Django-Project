"""
Cart App API Views

This module implements the Cart REST API.

Every endpoint:
- Requires JWT authentication (permission_classes = [IsAuthenticated])
- Derives the cart from request.user (NEVER from a client-provided cart_id)
- Returns the full updated cart, so the frontend always has fresh state

Ownership rule (learned from the Restaurant API bug):
    A CartItem id alone is NOT enough to fetch an item.
    We always combine it with cart__user=request.user.
    Otherwise User A could modify User B's cart by guessing IDs.

Restaurant rule:
    A cart can only contain items from ONE restaurant.
    Adding a MenuItem from a different restaurant is rejected
    with a structured error so the frontend can ask the user to clear
    the cart before switching restaurants.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem
from .api_serializers import (
    CartReadSerializer,
    CartAddItemSerializer,
    CartItemUpdateSerializer,
)


# ==================================================================
# HELPERS
# ==================================================================

def _get_or_create_user_cart(user):
    """
    Return the user's Cart, creating an empty one if it doesn't exist.

    Why get_or_create?
        A user might hit GET /api/cart/ before ever adding anything.
        Instead of returning 404, we hand back an empty cart.
        Cleaner for the frontend and simpler than wrapping every
        call site in try/except.
    """
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


def _reload_cart_with_relations(cart_id):
    """
    Re-fetch the cart with eager loading for serialization.

    Why not use the cart instance we already have?
        After mutations (add/patch/delete), the in-memory cart may be
        stale on its .items cache and .restaurant. Re-fetching with
        select_related + prefetch_related gives us a single efficient
        query path for the response serializer.
    """
    return (
        Cart.objects
        .select_related('restaurant')
        .prefetch_related('items__menu_item')
        .get(id=cart_id)
    )


# ==================================================================
# CART DETAIL (GET /api/cart/)
# ==================================================================

class CartDetailAPIView(APIView):
    """
    GET /api/cart/

    Return the authenticated user's cart.

    Behavior:
    - If the user has no cart yet, an empty cart is created silently.
    - Response always includes nested items, restaurant, totals.

    Security:
    - The cart is derived from request.user, never from URL or body.
    - A user can never view another user's cart.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = _get_or_create_user_cart(request.user)
        cart = _reload_cart_with_relations(cart.id)

        serializer = CartReadSerializer(cart)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==================================================================
# ADD ITEM (POST /api/cart/add/)
# ==================================================================

class CartAddItemAPIView(APIView):
    """
    POST /api/cart/add/

    Add a menu item to the authenticated user's cart.

    Request body:
        {
            "menu_item_id": 12,
            "quantity": 2,
            "special_instructions": "Extra spicy"   # optional
        }

    Business logic:
        1. Validate the menu item exists, is available, and its
           restaurant is active (handled by the serializer).
        2. Get or create the user's cart.
        3. Enforce one-restaurant-per-cart:
             - Empty cart -> adopt the menu item's restaurant.
             - Same restaurant -> continue.
             - Different restaurant -> reject with 400 and structured error.
        4. If the menu item is already in the cart, increment quantity
           (and optionally update special_instructions).
           Otherwise create a new CartItem.
        5. Return the full updated cart.

    Everything is wrapped in transaction.atomic() so a mid-operation
    failure leaves the database untouched.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # ----------------------------------------------------------
        # Step 1: Validate input
        # ----------------------------------------------------------
        serializer = CartAddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # The serializer injected the resolved MenuItem object
        # into validated_data under the key 'menu_item'.
        menu_item = serializer.validated_data['menu_item']
        quantity = serializer.validated_data['quantity']
        special_instructions = serializer.validated_data.get(
            'special_instructions', ''
        )

        # ----------------------------------------------------------
        # Step 2..4: Atomic cart mutation
        # ----------------------------------------------------------
        with transaction.atomic():
            cart = _get_or_create_user_cart(request.user)

            # Step 3: Restaurant consistency check
            if cart.restaurant_id is None:
                # Empty cart: adopt this menu item's restaurant.
                cart.restaurant = menu_item.restaurant
                cart.save(update_fields=['restaurant', 'updated_at'])

            elif cart.restaurant_id != menu_item.restaurant_id:
                # Different restaurant: reject. Do NOT silently mix.
                return Response(
                    {
                        'error': 'restaurant_mismatch',
                        'detail': (
                            f"Your cart contains items from "
                            f"'{cart.restaurant.name}'. You cannot add "
                            f"items from '{menu_item.restaurant.name}' "
                            f"to the same cart. Clear your cart first."
                        ),
                        'current_restaurant': {
                            'id': cart.restaurant.id,
                            'name': cart.restaurant.name,
                        },
                        'requested_restaurant': {
                            'id': menu_item.restaurant.id,
                            'name': menu_item.restaurant.name,
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Step 4: Increment existing item or create new one
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                menu_item=menu_item,
                defaults={
                    'quantity': quantity,
                    'special_instructions': special_instructions,
                },
            )

            if not created:
                # Item already in cart: bump quantity.
                cart_item.quantity += quantity

                # If the client sent new instructions, replace them.
                # If not, keep whatever the user set before.
                if special_instructions:
                    cart_item.special_instructions = special_instructions

                cart_item.save(
                    update_fields=[
                        'quantity',
                        'special_instructions',
                        'updated_at',
                    ]
                )

        # ----------------------------------------------------------
        # Step 5: Return the updated cart
        # ----------------------------------------------------------
        cart = _reload_cart_with_relations(cart.id)
        return Response(
            CartReadSerializer(cart).data,
            status=status.HTTP_200_OK,
        )


# ==================================================================
# UPDATE / DELETE ITEM (PATCH/DELETE /api/cart/items/<id>/)
# ==================================================================

class CartItemUpdateDeleteAPIView(APIView):
    """
    PATCH  /api/cart/items/<cart_item_id>/   -> update quantity / notes
    DELETE /api/cart/items/<cart_item_id>/   -> remove the item

    Ownership:
        The lookup combines:
            id = cart_item_id
            cart__user = request.user
        So even if User A guesses User B's cart_item_id, the query
        returns 404. This is the same nested-relationship rule we
        applied to the Restaurant API.
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, request, cart_item_id):
        """
        Fetch the CartItem, scoped to the authenticated user's cart.

        If the item does not exist OR belongs to another user,
        get_object_or_404 returns 404. We do NOT distinguish between
        the two cases, so an attacker cannot probe for existence.
        """
        return get_object_or_404(
            CartItem.objects.select_related('cart', 'menu_item'),
            id=cart_item_id,
            cart__user=request.user,
        )

    # --------------------------------------------------------------
    # PATCH: update one CartItem
    # --------------------------------------------------------------
    def patch(self, request, cart_item_id):
        cart_item = self.get_object(request, cart_item_id)

        serializer = CartItemUpdateSerializer(
            cart_item,
            data=request.data,
            partial=True,   # Both fields optional
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        cart = _reload_cart_with_relations(cart_item.cart_id)
        return Response(
            CartReadSerializer(cart).data,
            status=status.HTTP_200_OK,
        )

    # --------------------------------------------------------------
    # DELETE: remove one CartItem
    # --------------------------------------------------------------
    def delete(self, request, cart_item_id):
        cart_item = self.get_object(request, cart_item_id)
        cart_id = cart_item.cart_id

        with transaction.atomic():
            cart_item.delete()

            # If the cart is now empty, reset its restaurant.
            # Otherwise the cart would still be tagged to a restaurant
            # with no items, blocking the user from adding items from
            # a different restaurant next time.
            cart = Cart.objects.get(id=cart_id)
            if not cart.items.exists():
                if cart.restaurant_id is not None:
                    cart.restaurant = None
                    cart.save(update_fields=['restaurant', 'updated_at'])

        cart = _reload_cart_with_relations(cart_id)
        return Response(
            CartReadSerializer(cart).data,
            status=status.HTTP_200_OK,
        )


# ==================================================================
# CLEAR CART (DELETE /api/cart/clear/)
# ==================================================================

class CartClearAPIView(APIView):
    """
    DELETE /api/cart/clear/

    Remove every item from the authenticated user's cart.

    Behavior:
    - All CartItems are deleted.
    - Cart row itself remains (one cart per user, forever).
    - Restaurant is reset to None so the next added item can
      establish a new restaurant.

    Why keep the Cart row?
        The OneToOne relationship between User and Cart means
        the user always has exactly one cart. Removing and recreating
        it would churn the DB and break the model design.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request):
        with transaction.atomic():
            cart = _get_or_create_user_cart(request.user)

            # Delete all items at the DB level (single query).
            cart.items.all().delete()

            # Reset restaurant since the cart is now empty.
            if cart.restaurant_id is not None:
                cart.restaurant = None
                cart.save(update_fields=['restaurant', 'updated_at'])

        cart = _reload_cart_with_relations(cart.id)
        return Response(
            CartReadSerializer(cart).data,
            status=status.HTTP_200_OK,
        )