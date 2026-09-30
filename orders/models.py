"""
Orders App Models

This app handles:
- Order management (placing orders, order status)
- Order items (individual items in an order)
- Cart functionality (stored in session for simplicity)
"""
from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from restaurants.models import MenuItem


# ============================================================================
# DELIVERY FEE CALCULATION
# ============================================================================
# Tiered by distance. First matching tier wins.
#
# Keep in sync with the frontend at lib/bill.ts.
# ============================================================================

DELIVERY_FEE_TIERS = [
    (Decimal('2'), Decimal('25')),
    (Decimal('5'), Decimal('43')),
    (Decimal('8'), Decimal('65')),
    (Decimal('12'), Decimal('80')),
    (Decimal('16'), Decimal('100')),
    (Decimal('20'), Decimal('130')),
    (Decimal('25'), Decimal('170')),
    (Decimal('30'), Decimal('240')),
]


def calculate_delivery_fee(distance_km: Decimal) -> Decimal:
    """
    Return the delivery fee for a given distance.

    Distances above the last tier are charged the highest tier's fee.
    """
    distance = Decimal(str(distance_km))
    for max_km, fee in DELIVERY_FEE_TIERS:
        if distance <= max_km:
            return fee
    return DELIVERY_FEE_TIERS[-1][1]


GST_RATE = Decimal('0.18')  # 18%

# Two-places rounding — used for subtotal and total.
TWO_PLACES = Decimal('0.01')
# Whole-rupee rounding — used for GST only.
WHOLE_RUPEE = Decimal('1')


# ============================================================================
# ORDER
# ============================================================================

class Order(models.Model):
    """
    Order model - represents a customer's order.

    Money fields (all snapshotted at order creation):
    - subtotal      : sum of item subtotals (before tax / delivery)
    - delivery_fee  : frozen delivery charge (based on restaurant distance)
    - gst_amount    : frozen 18% GST on the subtotal, ROUNDED TO WHOLE ₹
    - total_amount  : subtotal + delivery_fee + gst_amount (final payable amount)
    """

    STATUS_CHOICES = [
        ('awaiting_payment', 'Awaiting Payment'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('payment_failed', 'Payment Failed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        help_text="User who placed the order"
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='orders',
        help_text="Restaurant where the order was placed"
    )

    # --- Money breakdown (all frozen at creation) ---
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        help_text="Sum of item subtotals (before tax / delivery)"
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        help_text="Delivery charge at time of order"
    )
    gst_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        help_text="GST charged at time of order (rounded to whole ₹)"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        help_text="Grand total (subtotal + delivery_fee + gst_amount)"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the order"
    )
    delivery_address = models.TextField(
        help_text="Delivery address for the order"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Special instructions or notes for the order"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} by {self.user.username} - ₹{self.total_amount}"

    # ------------------------------------------------------------------
    # Money recalculation
    # ------------------------------------------------------------------

    def calculate_total(self):
        """
        Recompute subtotal, gst_amount, and total_amount from OrderItems.

        GST ROUNDING RULE
        -----------------
        GST is rounded to the nearest WHOLE RUPEE, ignoring paise:

            12.10 to 12.49  ->  12
            12.50 to 12.99  ->  13

        Subtotal and total keep 2 decimal places.

        Does NOT touch delivery_fee.
        """
        # Subtotal: keep 2 decimals (matches item prices)
        subtotal = sum(
            (item.subtotal or Decimal("0.00") for item in self.items.all()),
            Decimal("0.00"),
        ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

        # GST: compute from subtotal, then round to whole rupee
        gst = (subtotal * GST_RATE).quantize(
            WHOLE_RUPEE, rounding=ROUND_HALF_UP
        )

        delivery_fee = self.delivery_fee or Decimal("0.00")
        total = (subtotal + delivery_fee + gst).quantize(
            TWO_PLACES, rounding=ROUND_HALF_UP
        )

        self.subtotal = subtotal
        self.gst_amount = gst
        self.total_amount = total
        self.save(update_fields=["subtotal", "gst_amount", "total_amount"])
        return total

    def recompute_fees(self):
        """
        Recalculate EVERYTHING, including delivery_fee.

        Use this when the authoritative source of delivery_fee is the
        restaurant's CURRENT distance — e.g. when an admin edits an
        order, or when placing an order via the API.
        """
        if self.restaurant_id:
            self.delivery_fee = calculate_delivery_fee(
                self.restaurant.distance_km
            )

        # Recompute totals (this saves subtotal/gst/total to DB)
        self.calculate_total()

        # Persist the delivery_fee too — calculate_total only saves
        # its own three fields.
        self.save(update_fields=["delivery_fee"])
        return self.total_amount


# ============================================================================
# ORDER ITEM
# ============================================================================

class OrderItem(models.Model):
    """
    OrderItem model - represents individual items within an order.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="The order this item belongs to"
    )
    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.CASCADE,
        related_name='order_items',
        help_text="The menu item that was ordered"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Quantity of this item ordered"
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price at the time of order (snapshot)"
    )
    special_instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Special instructions for this item"
    )

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} for Order #{self.order.id}"

    @property
    def subtotal(self):
        """
        Calculate subtotal for this order item (price * quantity).
        """
        if self.price is None or self.quantity is None:
            return Decimal('0')
        return self.price * self.quantity