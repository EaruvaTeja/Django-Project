"""
Payments App API URLs

Included by the main project's urls.py under the prefix '/api/payments/'.

Final URL map (with prefix):

    GET  /api/payments/           -> PaymentListAPIView (this user's payments)
    POST /api/payments/create/    -> PaymentCreateAPIView (create Razorpay order)
    POST /api/payments/verify/    -> PaymentVerifyAPIView (verify + confirm order)

All endpoints require JWT authentication.
Ownership is always derived from request.user, never from the URL.
"""

from django.urls import path

from . import api_views


app_name = 'payments_api'  # Namespace for reverse URL lookups


urlpatterns = [
    # GET: list this user's payment history
    path(
        '',
        api_views.PaymentListAPIView.as_view(),
        name='payment-list',
    ),

    # POST: create a Razorpay order + Payment row (status='initiated')
    path(
        'create/',
        api_views.PaymentCreateAPIView.as_view(),
        name='payment-create',
    ),

    # POST: verify signature, confirm/fail order, clear cart on success
    path(
        'verify/',
        api_views.PaymentVerifyAPIView.as_view(),
        name='payment-verify',
    ),

    # POST: cancel an initiated payment (abandoned / declined)
    path(
        '<int:pk>/cancel/',
        api_views.PaymentCancelAPIView.as_view(),
        name='payment-cancel',
    ),

    # TEMPORARY test checkout page --- DELETE AFTER TESTING ---
    # path(
    #     'test-checkout/<int:order_id>/',
    #     api_views.razorpay_test_checkout,
    #     name='razorpay-test-checkout',
    # ),
]