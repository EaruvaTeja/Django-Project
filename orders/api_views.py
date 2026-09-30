"""
Orders App API Views

This module implements the Orders REST API.

Endpoints:
    GET    /api/orders/                  -> list this user's orders
    POST   /api/orders/                  -> create order from current Cart
    GET    /api/orders/<order_id>/       -> view one order's details

Ownership rule (same as Cart and Restaurants):
    - Orders are always scoped to request.user.
    - Cross-user access returns 404 (never 403), so an attacker cannot
      confirm whether another user's order exists.

Cart -> Order flow (POST /api/orders/):

    NOTE: Order creation does NOT clear the cart.
    The cart is cleared later, after the payment is verified.

    Steps inside POST /api/orders/:
        1. Validate body (delivery_address, notes).
        2. Load request.user.cart.
        3. Validate cart is not empty, has a restaurant, restaurant is
           active, and every menu item is still available.
        4. Inside a single transaction:
            a. Pre-compute delivery_fee from restaurant.distance_km.
            b. Create Order with status='awaiting_payment' + delivery_fee.
            c. Create OrderItems, copying MenuItem.price as a SNAPSHOT.
            d. Call order.recompute_fees() to compute subtotal + GST + total.
        5. Return the created order as JSON (201 Created).

    Why atomic?
        If any step fails (DB error, menu item missing), the entire
        transaction rolls back. We never leave a half-created order.
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import Cart
from .models import Order, OrderItem, calculate_delivery_fee
from .api_serializers import (
    OrderCreateSerializer,
    OrderReadSerializer,
)


# ==================================================================
# LIST / CREATE  (GET + POST /api/orders/)
# ==================================================================

class OrderListCreateAPIView(APIView):
    """
    GET  /api/orders/  -> list the authenticated user's orders.
    POST /api/orders/  -> create a new order from the user's Cart.

    Both methods require JWT authentication.
    """

    permission_classes = [IsAuthenticated]

    # --------------------------------------------------------------
    # Browsable API support: DRF uses this to render the HTML form
    # for POST requests. Response layout uses OrderReadSerializer.
    # --------------------------------------------------------------
    def get_serializer(self, *args, **kwargs):
        return OrderCreateSerializer(*args, **kwargs)

    # --------------------------------------------------------------
    # GET: list this user's orders
    # --------------------------------------------------------------
    def get(self, request):
        """
        Return all orders placed by the authenticated user,
        most recent first (model Meta ordering handles that).

        Uses prefetch_related on items__menu_item and select_related
        on restaurant to avoid N+1 queries when serializing.
        """
        orders = (
            Order.objects
            .filter(user=request.user)
            .select_related('restaurant')
            .prefetch_related('items__menu_item')
        )
        serializer = OrderReadSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # --------------------------------------------------------------
    # POST: create order from the user's Cart
    # --------------------------------------------------------------
    def post(self, request):
        # Step 1: Validate body (delivery_address, notes)
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        delivery_address = serializer.validated_data['delivery_address']
        notes = serializer.validated_data.get('notes', '')

        # Step 2: Load the user's cart with related objects
        try:
            cart = (
                Cart.objects
                .select_related('restaurant')
                .prefetch_related('items__menu_item')
                .get(user=request.user)
            )
        except Cart.DoesNotExist:
            return Response(
                {
                    'error': 'empty_cart',
                    'detail': 'You do not have a cart yet.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 3: Validate cart state
        cart_items = list(cart.items.all())

        if not cart_items:
            return Response(
                {
                    'error': 'empty_cart',
                    'detail': 'Your cart is empty. Add items before placing an order.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if cart.restaurant is None:
            # Defensive: a cart with items should always have a restaurant.
            return Response(
                {
                    'error': 'no_restaurant',
                    'detail': (
                        'Your cart has items but no restaurant assigned. '
                        'This is a data consistency issue; please clear the '
                        'cart and add items again.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not cart.restaurant.is_active:
            return Response(
                {
                    'error': 'restaurant_inactive',
                    'detail': (
                        f"'{cart.restaurant.name}' is no longer accepting "
                        f"orders. Please try another restaurant."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Every menu item must still be available AND belong to this restaurant.
        unavailable_items = []
        for cart_item in cart_items:
            if not cart_item.menu_item.is_available:
                unavailable_items.append({
                    'id': cart_item.menu_item.id,
                    'name': cart_item.menu_item.name,
                })
            elif cart_item.menu_item.restaurant_id != cart.restaurant_id:
                # Defensive: should never happen given our cart rules,
                # but if the DB got out of sync we catch it here.
                unavailable_items.append({
                    'id': cart_item.menu_item.id,
                    'name': cart_item.menu_item.name,
                    'reason': 'belongs to a different restaurant',
                })

        if unavailable_items:
            return Response(
                {
                    'error': 'items_unavailable',
                    'detail': (
                        'Some items in your cart are no longer available. '
                        'Please remove them and try again.'
                    ),
                    'items': unavailable_items,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 4: Atomic creation
        with transaction.atomic():
            # 4a. Pre-compute the delivery fee from the restaurant's distance.
            #     Setting it on create() guarantees it's never zero, even
            #     before recompute_fees() runs.
            delivery_fee = calculate_delivery_fee(
                cart.restaurant.distance_km
            )

            # 4b. Create the Order with status='awaiting_payment'.
            #     The payment verification step will flip this to
            #     'confirmed' after a successful Razorpay payment.
            order = Order.objects.create(
                user=request.user,
                restaurant=cart.restaurant,
                delivery_address=delivery_address,
                notes=notes,
                status='awaiting_payment',
                subtotal=0,
                delivery_fee=delivery_fee,
                gst_amount=0,
                total_amount=0,
            )

            # 4c. Create OrderItems with SNAPSHOT price
            for cart_item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    quantity=cart_item.quantity,
                    price=cart_item.menu_item.price,   # <-- snapshot!
                    special_instructions=cart_item.special_instructions or '',
                )

            # 4d. Recompute subtotal + GST + total (and re-derive delivery_fee).
            order.recompute_fees()

        # Step 5: Return the created order
        # Re-fetch with related data so the serializer has everything.
        order = (
            Order.objects
            .select_related('restaurant')
            .prefetch_related('items__menu_item')
            .get(id=order.id)
        )
        return Response(
            OrderReadSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


# ==================================================================
# DETAIL  (GET /api/orders/<order_id>/)
# ==================================================================

class OrderDetailAPIView(APIView):
    """
    GET /api/orders/<order_id>/

    Return one order's full details.

    Ownership:
        The lookup combines:
            id = order_id
            user = request.user
        So a user can never view another user's order. If the order
        belongs to someone else, get_object_or_404 returns 404 — the
        same response as a truly nonexistent order. An attacker cannot
        probe for other users' order IDs.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, order_id):
        order = get_object_or_404(
            Order.objects
            .select_related('restaurant')
            .prefetch_related('items__menu_item'),
            id=order_id,
            user=request.user,
        )
        serializer = OrderReadSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)