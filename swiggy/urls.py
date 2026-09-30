"""
URL configuration for swiggy project.

This is the main URL routing file for the entire Django project.
It includes URLs from all our apps and sets up the homepage.

How URL Routing Works in Django:
1. User requests a URL like http://127.0.0.1:8000/restaurants/
2. Django checks this file (swiggy/urls.py) first
3. It matches the 'restaurants/' prefix and delegates to restaurants/urls.py
4. The restaurants app then handles the rest of the URL

URL Structure:
- / -> Homepage (core view)
- /admin/ -> Django admin panel (built-in)
- /users/ -> User authentication (login, register, logout, profile)
- /restaurants/ -> Restaurant listings and menus
- /orders/ -> Cart, checkout, order history
- /api/ -> REST API endpoints
- /media/ -> User-uploaded files (during development)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from restaurants.api_views import AllMenuItemsAPIView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


def home_view(request):
    """
    Homepage view - the first page users see.
    
    This demonstrates a simple function-based view that:
    1. Receives an HTTP request
    2. Optionally queries the database
    3. Returns a rendered template
    
    Template: home.html
    """
    from restaurants.models import Restaurant
    
    # Get featured restaurants (top rated) for the homepage
    featured_restaurants = Restaurant.objects.filter(is_active=True).order_by('-rating')[:6]
    
    context = {
        'featured_restaurants': featured_restaurants,
        'page_title': 'Swiggy Clone - Food Delivery'
    }
    
    return render(request, 'home.html', context)


urlpatterns = [
    # Admin panel - built-in Django feature for managing data
    # Access at: http://127.0.0.1:8000/admin/
    # Admin
    path('admin/', admin.site.urls),

    # Homepage
    path('', home_view, name='home'),

    # Django template URLs
    path('users/', include('users.urls')),

    # Restaurant URLs
    path('restaurants/', include('restaurants.urls')),

    # Order and cart URLs
    path('orders/', include('orders.urls')),

    # JWT login
    path('api/auth/login/',TokenObtainPairView.as_view(),name='token_obtain_pair'),

    # JWT refresh
    path('api/auth/refresh/',TokenRefreshView.as_view(),name='token_refresh'),

    # JWT verify
    path('api/auth/verify/',TokenVerifyView.as_view(),name='token_verify'),

    # API registration
    path('api/auth/',include('users.api_auth_urls')),

    # Users Profile Api
    path('api/users/',include('users.api_users_urls')),

    # Restaurants API urls
    path('api/restaurants/', include('restaurants.api_urls')),

    # Home showcase — all available menu items across restaurants
    path('api/menu-items/', AllMenuItemsAPIView.as_view(), name='all-menu-items'),

    # Cart API urls
    path('api/cart/', include('cart.api_urls')),

    # Orders API urls
    path('api/orders/', include('orders.api_urls')),

    # Payments API urls
    path('api/payments/', include('payments.api_urls')),

    # Address API urls
    path('api/addresses/', include('users.api_address_urls')),
]

# Serve media files during development (user-uploaded images)
# In production, you'd use a CDN or web server like Nginx
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Optional: Custom error pages
# You can add these later for 404 and 500 error pages
# handler404 = 'swiggy.views.custom_404'
# handler500 = 'swiggy.views.custom_500'
