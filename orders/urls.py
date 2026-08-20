"""
Orders App URL Configuration

This file defines the URL patterns for order-related views and API endpoints.
These URLs are included in the main project's urls.py.

URL Patterns:
Traditional Views (HTML pages):
- /orders/cart/ -> cart_view (display shopping cart)
- /orders/add-to-cart/<id>/ -> add_to_cart (add item to cart)
- /orders/checkout/ -> checkout_view (checkout page)
- /orders/history/ -> order_history (user's past orders)
- /orders/<id>/ -> order_detail (specific order details)

REST API Endpoints (JSON):
- /api/orders/place/ -> PlaceOrderView (POST: place order via API)

Note: API endpoints are under /api/ prefix to distinguish them from regular views.
"""

from django.urls import path
from . import views

app_name = 'orders'  # Namespace for URL reversing (e.g., 'orders:cart')

urlpatterns = [
    # Traditional view-based URLs (return HTML templates)
    
    # View cart
    # Example: /orders/cart/
    path('cart/', views.cart_view, name='cart'),
    
    # Add item to cart (requires POST)
    # Example: /orders/add-to-cart/5/
    path('add-to-cart/<int:menu_item_id>/', views.add_to_cart, name='add_to_cart'),
    
    # Clear cart (requires POST)
    # Example: /orders/clear-cart/
    path('clear-cart/', views.clear_cart, name='clear_cart'),
    
    # Checkout page
    # Example: /orders/checkout/
    path('checkout/', views.checkout_view, name='checkout'),
    
    # Order history
    # Example: /orders/history/
    path('history/', views.order_history, name='order_history'),
    
    # Specific order detail
    # Example: /orders/1/
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    
    # =============================================================================
    # REST API ENDPOINTS
    # These return JSON responses instead of HTML templates
    # =============================================================================
    
    # Place order via API
    # Example: POST /api/orders/place/ with JSON body
    # This is the main DRF endpoint for learning how APIs work in Django
    path('api/orders/place/', views.PlaceOrderView.as_view(), name='api_place_order'),
]
