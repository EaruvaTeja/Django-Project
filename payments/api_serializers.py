"""
Payments App API Serializers

Serializers for the Razorpay payments flow.

WRITE serializers (JSON -> validated data):
    PaymentOrderCreateSerializer
        Input for POST /api/payments/create/.
        Only accepts order_id. Amount is read from the Order on
        the server side — never trusted from the client.

    PaymentVerifySerializer
        Input for POST /api/payments/verify/.
        Accepts the three fields Razorpay sends back to the frontend:
        razorpay_order_id, razorpay_payment_id, razorpay_signature.

READ serializers (Model -> JSON):
    PaymentOrderRefSerializer
        Minimal order info shown inside a payment response.

    PaymentReadSerializer
        Full payment record for GET /api/payments/.

Security notes:
- Never expose razorpay_signature (internal verification token).
- Never expose razorpay_key_secret (only the SDK uses it).
- The client never sends or receives amounts — server-side only.
"""

from rest_framework import serializers

from orders.models import Order
from .models import Payment


# ==================================================================
# NESTED READ SERIALIZER
# ==================================================================

class PaymentOrderRefSerializer(serializers.ModelSerializer):
    """
    Minimal order info shown inside a payment record.

    Just enough to identify which order a payment belongs to,
    without exposing delivery_address, notes, or full item list.
    """
    class Meta:
        model = Order
        fields = [
            'id',
            'status',
            'total_amount',
            'created_at',
        ]
        read_only_fields = fields


# ==================================================================
# WRITE: create payment order
# ==================================================================

class PaymentOrderCreateSerializer(serializers.Serializer):
    """
    Input for POST /api/payments/create/.

    Expected JSON:
        { "order_id": 5 }

    Only order_id is accepted. The server reads the amount from
    the Order object — the client cannot influence the price.

    Validation:
    - order_id must be a positive integer.
    - The Order must exist.
    - The Order must belong to request.user (checked in the view,
      because the serializer does not know request.user).

    We intentionally do NOT validate the Order's status here. The
    view handles status checks (awaiting_payment, already paid, etc.)
    because those decisions need request context.
    """

    order_id = serializers.IntegerField(min_value=1)


# ==================================================================
# WRITE: verify payment
# ==================================================================

class PaymentVerifySerializer(serializers.Serializer):
    """
    Input for POST /api/payments/verify/.

    Expected JSON (sent by the frontend after Razorpay Checkout):

        {
            "razorpay_order_id": "order_xxxxxxxxxxxx",
            "razorpay_payment_id": "pay_xxxxxxxxxxxx",
            "razorpay_signature": "long_hex_signature_string"
        }

    All three fields are required and must not be blank.
    The Razorpay SDK uses them together to verify authenticity.
    """

    razorpay_order_id = serializers.CharField(
        max_length=200,
        allow_blank=False,
    )
    razorpay_payment_id = serializers.CharField(
        max_length=200,
        allow_blank=False,
    )
    razorpay_signature = serializers.CharField(
        max_length=500,
        allow_blank=False,
    )


# ==================================================================
# READ: payment record
# ==================================================================

class PaymentReadSerializer(serializers.ModelSerializer):
    """
    Serialize ONE Payment record for reading.

    Includes:
    - Nested order reference (minimal)
    - razorpay_order_id and razorpay_payment_id (public identifiers)
    - amount, currency, status, method
    - timestamps

    Excludes (security):
    - razorpay_signature  (internal token, never sent to frontend)
    - razorpay_key_secret (never stored on the model anyway)
    """
    order = PaymentOrderRefSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id',
            'order',
            'razorpay_order_id',
            'razorpay_payment_id',
            'amount',
            'currency',
            'status',
            'method',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields