"""
Payments App Admin Configuration

This file registers the Payment model with Django's admin panel
so payments can be reviewed at http://127.0.0.1:8000/admin/.

Design philosophy:
    Payment records are AUDIT LOGS. They reflect what Razorpay
    actually reported. Admins should REVIEW them, never EDIT them.
    Therefore almost every field is read-only.

    If a payment needs to be corrected, the correct action is to
    trigger a new payment attempt via the API — not to hand-edit
    this record.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Payment model.

    Useful for:
    - Debugging failed payments (find by razorpay_order_id)
    - Reconciling against the Razorpay dashboard
    - Auditing user payment history
    """

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------
    list_display = [
        'id',
        'order',
        'amount_display',
        'status_badge',
        'method',
        'created_at',
    ]

    list_filter = [
        'status',
        'method',
        'currency',
        'created_at',
    ]

    search_fields = [
        'razorpay_order_id',
        'razorpay_payment_id',
        'order__id',
        'order__user__username',
        'order__user__email',
    ]

    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 50

    # ------------------------------------------------------------------
    # Form view
    # ------------------------------------------------------------------
    # The order FK is set by the API. Use raw_id to avoid a huge dropdown.
    raw_id_fields = ['order']

    # Everything the SDK or Razorpay writes is locked down.
    # These are audit fields — never edited by hand.
    readonly_fields = [
        'order',
        'razorpay_order_id',
        'razorpay_payment_id',
        'razorpay_signature',
        'amount',
        'currency',
        'status',
        'method',
        'created_at',
        'updated_at',
    ]

    fieldsets = [
        (
            'Order',
            {
                'fields': ['order'],
            },
        ),
        (
            'Razorpay Identifiers',
            {
                'fields': [
                    'razorpay_order_id',
                    'razorpay_payment_id',
                    'razorpay_signature',
                ],
            },
        ),
        (
            'Amount & Status',
            {
                'fields': [
                    'amount',
                    'currency',
                    'status',
                    'method',
                ],
            },
        ),
        (
            'Timestamps',
            {
                'fields': [
                    'created_at',
                    'updated_at',
                ],
            },
        ),
    ]

    # ------------------------------------------------------------------
    # Custom columns
    # ------------------------------------------------------------------

    @admin.display(description='Amount')
    def amount_display(self, obj):
        """Show amount with currency, e.g. '1200.00 INR'."""
        return f"{obj.amount} {obj.currency}"

    @admin.display(description='Status')
    def status_badge(self, obj):
        """
        Colored status indicator for quick visual scanning.

        Green  = success
        Red    = failed
        Orange = initiated (pending)
        """
        colors = {
            Payment.STATUS_SUCCESS: '#28a745',   # green
            Payment.STATUS_FAILED: '#dc3545',    # red
            Payment.STATUS_INITIATED: '#fd7e14', # orange
        }
        color = colors.get(obj.status, '#6c757d')  # gray fallback

        return format_html(
            '<span style="'
            'display:inline-block;'
            'padding:3px 8px;'
            'border-radius:4px;'
            'background-color:{};'
            'color:white;'
            'font-size:11px;'
            'font-weight:bold;'
            'text-transform:uppercase;'
            '">{}</span>',
            color,
            obj.get_status_display(),
        )

    # ------------------------------------------------------------------
    # Permissions: block manual creation & deletion from admin
    # ------------------------------------------------------------------
    def has_add_permission(self, request):
        """
        Payments must only be created via the API (which talks to Razorpay).
        Creating them manually in admin would produce records with no
        matching Razorpay order — a data integrity hazard.
        """
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Payment records are audit logs. Deleting them destroys the trail
        needed for reconciliation. Set to False to preserve history.
        (Superusers can still delete via the shell if absolutely needed.)
        """
        return False