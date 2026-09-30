"""
Payments App API Views

Razorpay payment flow for orders.

Endpoints:
    POST /api/payments/create/          -> create Razorpay order + Payment row
    POST /api/payments/verify/          -> verify signature, confirm/fail order, clear cart
    POST /api/payments/<pk>/cancel/     -> mark abandoned/declined payment as failed
    GET  /api/payments/                 -> list this user's payment history

Lifecycle:
    awaiting_payment order
        ↓
    POST /create/  -> Payment(initiated) + Razorpay order
        ↓
    user pays on Razorpay Checkout
        ↓
    POST /verify/  -> signature check + fulfillability re-check
        ↓
        ┌───────────────┴───────────────┐
        ▼                               ▼
    success                       failure / unfulfillable
        ▼                               ▼
    Payment(success)              Payment(failed)
    Order(confirmed)              Order(payment_failed)
    Cart cleared*                 Cart preserved

    * Cart is only cleared if:
        - This is a fresh checkout, OR
        - This is a retry AND the cart still matches the order exactly.

Security rules:
- Ownership via request.user only. Client-supplied IDs never trusted alone.
- Cross-user access -> 404 (never 403).
- Amount is read from the Order on the server, never from the client.
- Every state-changing write in a single transaction.
- Payment re-validation prevents confirming unfulfillable orders.
"""

import razorpay
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import Cart
from orders.models import Order
from .models import Payment
from .api_serializers import (
    PaymentOrderCreateSerializer,
    PaymentVerifySerializer,
    PaymentReadSerializer,
)


# ==================================================================
# HELPERS
# ==================================================================

def _cart_matches_order(cart, order) -> bool:
    """
    True if the cart's items are an EXACT match to the order's items.

    Match criteria:
      - Same number of distinct menu items
      - Same menu_item_id per row
      - Same quantity per row
      - Same special_instructions (whitespace-insensitive)

    Ordering doesn't matter — we sort both sides by menu_item_id.
    """
    cart_items = list(cart.items.all().order_by('menu_item_id'))
    order_items = list(order.items.all().order_by('menu_item_id'))

    if len(cart_items) != len(order_items):
        return False

    for ci, oi in zip(cart_items, order_items):
        if ci.menu_item_id != oi.menu_item_id:
            return False
        if ci.quantity != oi.quantity:
            return False
        ci_note = (ci.special_instructions or '').strip()
        oi_note = (oi.special_instructions or '').strip()
        if ci_note != oi_note:
            return False

    return True


def _validate_order_fulfillable(order) -> list[str]:
    """
    Re-check business rules before confirming an order.

    Called from the verify endpoint AFTER signature verification passes
    (i.e., the payment is genuinely from Razorpay).

    Returns a list of human-readable problems. Empty list means the
    order can be fulfilled.
    """
    problems: list[str] = []

    # Restaurant still active?
    if not order.restaurant.is_active:
        problems.append(
            f"'{order.restaurant.name}' is no longer accepting orders."
        )

    # Every item still available + still belongs to this restaurant?
    for item in order.items.all():
        menu_item = item.menu_item
        if not menu_item.is_available:
            problems.append(f"'{menu_item.name}' is currently unavailable.")
        elif menu_item.restaurant_id != order.restaurant_id:
            problems.append(
                f"'{menu_item.name}' is no longer on this restaurant's menu."
            )

    return problems


def _razorpay_client():
    """
    Build a Razorpay client using the keys in settings.

    Called per request instead of at module import so a missing key
    surfaces as a clear runtime error instead of an import-time crash.
    """
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


# ==================================================================
# CREATE  (POST /api/payments/create/)
# ==================================================================

class PaymentCreateAPIView(APIView):
    """
    POST /api/payments/create/

    Request body:
        { "order_id": 5 }

    Behavior:
        1. Validate order_id.
        2. Load the order, scoped to request.user.
        3. Reject if order is not awaiting_payment or payment_failed.
        4. Reject if a successful payment already exists.
        5. Create a Razorpay order via SDK (amount in paise).
        6. Create a Payment row with status='initiated'.
        7. Return the data the frontend needs to open Razorpay Checkout.
    """

    permission_classes = [IsAuthenticated]

    def get_serializer(self, *args, **kwargs):
        # Enables the HTML form in the DRF browsable API.
        return PaymentOrderCreateSerializer(*args, **kwargs)

    def post(self, request):
        # Step 1: validate input
        serializer = PaymentOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_id = serializer.validated_data['order_id']

        # Step 2: load order (ownership enforced)
        order = get_object_or_404(
            Order,
            id=order_id,
            user=request.user,
        )

        # Step 3: order status must allow payment
        allowed_statuses = ('awaiting_payment', 'payment_failed')
        if order.status not in allowed_statuses:
            return Response(
                {
                    'error': 'invalid_order_status',
                    'detail': (
                        f"Cannot initiate payment. Order status is "
                        f"'{order.status}'."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 4: reject if a successful payment already exists
        if order.payments.filter(status=Payment.STATUS_SUCCESS).exists():
            return Response(
                {
                    'error': 'already_paid',
                    'detail': (
                        'This order has already been paid successfully.'
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 5: create the Razorpay order
        # amount must be in paise (smallest unit). total_amount is a
        # Decimal, so * 100 gives an exact Decimal, then int() -> paise.
        amount_in_paise = int(order.total_amount * 100)

        client = _razorpay_client()
        try:
            razorpay_order = client.order.create({
                'amount': amount_in_paise,
                'currency': 'INR',
                'receipt': f'swiggy_order_{order.id}',
                'payment_capture': 1,   # auto-capture
            })
        except razorpay.errors.BadRequestError as e:
            return Response(
                {'error': 'razorpay_error', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except razorpay.errors.AuthenticationError:
            return Response(
                {
                    'error': 'razorpay_auth_error',
                    'detail': (
                        'Razorpay authentication failed. '
                        'Check API keys in settings.py.'
                    ),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except razorpay.errors.ServerError as e:
            return Response(
                {
                    'error': 'razorpay_server_error',
                    'detail': f'Razorpay returned a server error: {e}',
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Step 6: persist a Payment row
        payment = Payment.objects.create(
            order=order,
            razorpay_order_id=razorpay_order['id'],
            amount=order.total_amount,
            currency='INR',
            status=Payment.STATUS_INITIATED,
        )

        # Step 7: respond with what the frontend needs
        return Response(
            {
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'amount': razorpay_order['amount'],   # in paise
                'amount_display': str(order.total_amount),  # in INR
                'currency': 'INR',
                'payment_id': payment.id,
            },
            status=status.HTTP_200_OK,
        )


# ==================================================================
# VERIFY  (POST /api/payments/verify/)
# ==================================================================

class PaymentVerifyAPIView(APIView):
    """
    POST /api/payments/verify/

    Request body (sent by frontend after Razorpay Checkout):
        {
            "razorpay_order_id": "order_xxx",
            "razorpay_payment_id": "pay_xxx",
            "razorpay_signature": "hex_signature"
        }

    Behavior:
        1. Validate input.
        2. Look up Payment by razorpay_order_id (ownership via order.user).
        3. Reject if Payment is already resolved (not 'initiated').
        4. Verify signature using SDK. Signature errors raise.
        5. Re-validate that the order is fulfillable (restaurant active,
           items available).
        6. Success: Payment='success', Order='confirmed', maybe cart cleared.
           Failure / unfulfillable: Payment='failed', Order='payment_failed'.
        7. Return success/failure JSON.
    """

    permission_classes = [IsAuthenticated]

    def get_serializer(self, *args, **kwargs):
        # Enables the HTML form in the DRF browsable API.
        return PaymentVerifySerializer(*args, **kwargs)

    def post(self, request):
        # Step 1: validate input
        serializer = PaymentVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        razorpay_order_id = serializer.validated_data['razorpay_order_id']
        razorpay_payment_id = serializer.validated_data['razorpay_payment_id']
        razorpay_signature = serializer.validated_data['razorpay_signature']

        # Step 2: load the Payment, scoped to the authenticated user's order
        payment = get_object_or_404(
            Payment.objects.select_related('order'),
            razorpay_order_id=razorpay_order_id,
            order__user=request.user,
        )

        # Step 3: reject replays
        if payment.status != Payment.STATUS_INITIATED:
            return Response(
                {
                    'error': 'payment_already_processed',
                    'detail': (
                        f"This payment is already '{payment.status}'."
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 4: verify the signature with the SDK
        client = _razorpay_client()

        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            })
        except razorpay.errors.SignatureVerificationError:
            # ---- FAILURE BRANCH ----
            with transaction.atomic():
                payment.status = Payment.STATUS_FAILED
                payment.razorpay_payment_id = razorpay_payment_id
                payment.razorpay_signature = razorpay_signature
                payment.save(update_fields=[
                    'status',
                    'razorpay_payment_id',
                    'razorpay_signature',
                    'updated_at',
                ])

                order = payment.order
                order.status = 'payment_failed'
                order.save(update_fields=['status', 'updated_at'])

            return Response(
                {
                    'success': False,
                    'error': 'signature_invalid',
                    'detail': 'Payment signature verification failed.',
                    'order_id': payment.order_id,
                    'order_status': 'payment_failed',
                    'payment_id': payment.id,
                    'payment_status': payment.status,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 5: best-effort fetch of payment method (card/upi/etc.)
        method = None
        try:
            payment_details = client.payment.fetch(razorpay_payment_id)
            method = payment_details.get('method')
        except Exception:
            # Non-critical. We can still confirm the order.
            pass

        # ------------------------------------------------------------------
        # Step 5a.5: RE-VALIDATE order is fulfillable
        # ------------------------------------------------------------------
        # Signature is valid (payment is genuine). But between the user
        # opening the modal and paying, the restaurant or items may have
        # changed. Refuse to confirm unfulfillable orders.
        #
        # The user's money WAS captured. Staff processes a manual refund
        # via Razorpay Dashboard. We mark status='payment_failed' so it's
        # visible in admin.
        order = payment.order
        problems = _validate_order_fulfillable(order)

        if problems:
            with transaction.atomic():
                payment.status = Payment.STATUS_FAILED
                payment.razorpay_payment_id = razorpay_payment_id
                payment.razorpay_signature = razorpay_signature
                payment.save(update_fields=[
                    'status',
                    'razorpay_payment_id',
                    'razorpay_signature',
                    'updated_at',
                ])
                order.status = 'payment_failed'
                order.save(update_fields=['status', 'updated_at'])

            return Response(
                {
                    'success': False,
                    'error': 'order_unfulfillable',
                    'detail': (
                        'Order not confirmed.\n'
                        'If payment was deducted, a refund will be processed.\n'
                        'Within 3–5 business days.'
                    ),
                    'order_id': order.id,
                    'order_status': 'payment_failed',
                    'payment_id': payment.id,
                    'payment_status': 'failed',
                    'problems': problems,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Step 6: SUCCESS BRANCH (atomic)
        with transaction.atomic():
            # Mark the Payment successful
            payment.status = Payment.STATUS_SUCCESS
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.method = method
            payment.save(update_fields=[
                'status',
                'razorpay_payment_id',
                'razorpay_signature',
                'method',
                'updated_at',
            ])

            # Confirm the Order
            order.status = 'confirmed'
            order.save(update_fields=['status', 'updated_at'])

            # Clear the Cart ONLY IF:
            #   - This is a FRESH checkout (no prior payment attempts), OR
            #   - This is a RETRY and the cart EXACTLY matches the order
            #
            # Never clear a cart that has diverged from the order.
            is_retry = (
                Payment.objects
                .filter(order=order)
                .exclude(pk=payment.pk)
                .exists()
            )

            cart = Cart.objects.filter(user=request.user).first()

            should_clear = False
            if cart is not None:
                if not is_retry:
                    should_clear = True
                elif _cart_matches_order(cart, order):
                    should_clear = True

            if should_clear and cart is not None:
                cart.items.all().delete()
                if cart.restaurant_id is not None:
                    cart.restaurant = None
                    cart.save(update_fields=['restaurant', 'updated_at'])

        # Step 7: respond
        return Response(
            {
                'success': True,
                'message': 'Payment verified. Your order is confirmed.',
                'order_id': order.id,
                'order_status': order.status,
                'payment_id': payment.id,
                'payment_status': payment.status,
            },
            status=status.HTTP_200_OK,
        )


# ==================================================================
# LIST  (GET /api/payments/)
# ==================================================================

class PaymentListAPIView(APIView):
    """
    GET /api/payments/

    Return this user's payment history, newest first.
    Ownership is enforced via order__user=request.user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        payments = (
            Payment.objects
            .filter(order__user=request.user)
            .select_related('order')
        )
        serializer = PaymentReadSerializer(payments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==================================================================
# CANCEL  (POST /api/payments/<pk>/cancel/)
# ==================================================================

class PaymentCancelAPIView(APIView):
    """
    POST /api/payments/<pk>/cancel/

    Marks a payment as failed and its order as payment_failed.

    Called by the frontend when:
      - User closes the Razorpay modal (abandoned)
      - Razorpay fires 'payment.failed' (card declined)

    Idempotent: calling twice is safe. If the payment is already
    success/failed, we return the current state instead of erroring.

    Cart is NOT cleared — the user can retry from /orders.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        payment = get_object_or_404(
            Payment.objects.select_related('order'),
            pk=pk,
            order__user=request.user,
        )

        # If already resolved, no-op (return current state)
        if payment.status != Payment.STATUS_INITIATED:
            return Response(
                {
                    'success': False,
                    'message': f"Payment is already '{payment.status}'.",
                    'payment_status': payment.status,
                    'order_status': payment.order.status,
                },
                status=status.HTTP_200_OK,
            )

        with transaction.atomic():
            payment.status = Payment.STATUS_FAILED
            payment.save(update_fields=['status', 'updated_at'])

            order = payment.order
            if order.status == 'awaiting_payment':
                order.status = 'payment_failed'
                order.save(update_fields=['status', 'updated_at'])

        return Response(
            {
                'success': True,
                'message': 'Payment cancelled.',
                'payment_status': payment.status,
                'order_status': order.status,
            },
            status=status.HTTP_200_OK,
        )