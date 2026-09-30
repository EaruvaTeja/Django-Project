"""
Orders App API URLs

Included by the main project's urls.py under the prefix '/api/orders/'.

Final URL map (with prefix):

    GET  /api/orders/              -> OrderListCreateAPIView (list)
    POST /api/orders/              -> OrderListCreateAPIView (create from Cart)
    GET  /api/orders/<order_id>/   -> OrderDetailAPIView (single order)

All endpoints require JWT authentication.
Ownership is always derived from request.user, never from the URL.
"""

from django.urls import path

from . import api_views


app_name = 'orders_api'  # Namespace for reverse URL lookups


urlpatterns = [
    # GET  -> list this user's orders
    # POST -> create a new order from the user's current Cart
    path(
        '',
        api_views.OrderListCreateAPIView.as_view(),
        name='order-list-create',
    ),

    # GET -> one order's details (ownership-scoped: 404 for others)
    # The <int:order_id> capture is ALWAYS combined with
    # user=request.user inside the view.
    path(
        '<int:order_id>/',
        api_views.OrderDetailAPIView.as_view(),
        name='order-detail',
    ),
]