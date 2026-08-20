"""
Restaurants App URL Configuration

This file defines the URL patterns for restaurant-related views.
These URLs are included in the main project's urls.py.

URL Patterns:
- /restaurants/ -> restaurant_list (shows all restaurants)
- /restaurants/<id>/ -> restaurant_detail (shows specific restaurant and menu)
- /menu-items/<id>/ -> menu_item_detail (shows specific menu item details)

Note: The <int:restaurant_id> syntax captures an integer from the URL
and passes it as a parameter to the view function.
"""

from django.urls import path
from . import views

app_name = 'restaurants'  # Namespace for URL reversing (e.g., 'restaurants:list')

urlpatterns = [
    # List all restaurants
    # Example: /restaurants/
    path('', views.restaurant_list, name='restaurant_list'),
    
    # Display a specific restaurant with its menu
    # Example: /restaurants/5/ (where 5 is the restaurant ID)
    path('<int:restaurant_id>/', views.restaurant_detail, name='restaurant_detail'),
    
    # Display details of a specific menu item
    # Example: /menu-items/10/
    path('menu-items/<int:item_id>/', views.menu_item_detail, name='menu_item_detail'),
]
