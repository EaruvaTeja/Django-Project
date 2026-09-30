"""
Cart App API URLs

These routes are included by the main project's urls.py under the
prefix '/api/cart/'.

Final URL map (with prefix):

    GET    /api/cart/                    -> CartDetailAPIView
    POST   /api/cart/add/                -> CartAddItemAPIView
    PATCH  /api/cart/items/<item_id>/    -> CartItemUpdateDeleteAPIView
    DELETE /api/cart/items/<item_id>/    -> CartItemUpdateDeleteAPIView
    DELETE /api/cart/clear/              -> CartClearAPIView

All endpoints require JWT authentication.
Ownership is always derived from request.user, never from the URL.
"""

from django.urls import path

from . import api_views


app_name = 'cart_api'  # Namespace for reverse URL lookups


urlpatterns = [
    # GET: return the authenticated user's full cart
    path(
        '',
        api_views.CartDetailAPIView.as_view(),
        name='cart-detail',
    ),

    # POST: add a menu item (or increment an existing one)
    path(
        'add/',
        api_views.CartAddItemAPIView.as_view(),
        name='cart-add-item',
    ),

    # PATCH / DELETE: update or remove a single cart item
    # The integer capture (cart_item_id) is ALWAYS combined with
    # cart__user=request.user inside the view, so cross-user access
    # returns 404.
    path(
        'items/<int:cart_item_id>/',
        api_views.CartItemUpdateDeleteAPIView.as_view(),
        name='cart-item-detail',
    ),

    # DELETE: wipe all items from the cart and reset its restaurant
    path(
        'clear/',
        api_views.CartClearAPIView.as_view(),
        name='cart-clear',
    ),
]