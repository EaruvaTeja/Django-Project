"""
Restaurants App Views

This app handles displaying restaurants and their menu items.

Data Flow (MVT Pattern - Model View Template):
1. User visits a URL like /restaurants/ or /restaurants/5/
2. Django's URL router matches the URL to a view function
3. The view queries the database (Model) to get restaurant/menu data
4. The view passes this data to a template (Template)
5. The template renders HTML with the data and sends it back to the user

Key Views:
- restaurant_list: Shows all restaurants
- restaurant_detail: Shows a specific restaurant with its menu
"""

from django.shortcuts import render, get_object_or_404
from .models import Restaurant, MenuItem


def restaurant_list(request):
    """
    Display a list of all active restaurants.
    
    This view demonstrates:
    - Querying the database using Django ORM
    - Filtering data (only active restaurants)
    - Passing context data to templates
    
    Database Query: SELECT * FROM restaurants_restaurant WHERE is_active=True
    Template: restaurants/restaurant_list.html
    """
    # Query all active restaurants from the database
    # Order by rating (highest first) for better user experience
    restaurants = Restaurant.objects.filter(is_active=True).order_by('-rating')
    
    # Context dictionary passes data from view to template
    # In the template, you can access {{ restaurants }} to iterate over them
    context = {
        'restaurants': restaurants,
        'page_title': 'All Restaurants'
    }
    
    # render() combines the template with context data and returns an HttpResponse
    return render(request, 'restaurants/restaurant_list.html', context)


def restaurant_detail(request, restaurant_id):
    """
    Display details of a specific restaurant and its menu.
    
    This view demonstrates:
    - Getting a single object by ID (or 404 if not found)
    - URL parameters (restaurant_id comes from the URL)
    - Related object queries (menu items belong to a restaurant)
    
    Database Queries:
    1. SELECT * FROM restaurants_restaurant WHERE id = restaurant_id
    2. SELECT * FROM restaurants_menuitem WHERE restaurant_id = restaurant_id AND is_available=True
    
    Template: restaurants/restaurant_detail.html
    """
    # get_object_or_404 fetches the object or returns a 404 error page if not found
    # This is safer than Restaurant.objects.get(id=restaurant_id) which would raise an exception
    restaurant = get_object_or_404(Restaurant, id=restaurant_id, is_active=True)
    
    # Get all available menu items for this restaurant
    # Uses the related_name='menu_items' defined in the ForeignKey
    menu_items = restaurant.menu_items.filter(is_available=True)
    
    # Group menu items by category for better display
    categories = {}
    for item in menu_items:
        if item.category not in categories:
            categories[item.category] = []
        categories[item.category].append(item)
    
    context = {
        'restaurant': restaurant,
        'menu_items': menu_items,
        'categories': categories,
        'page_title': restaurant.name
    }
    
    return render(request, 'restaurants/restaurant_detail.html', context)


def menu_item_detail(request, item_id):
    """
    Display details of a specific menu item.
    
    This is useful for showing a modal or dedicated page for a menu item.
    
    Template: restaurants/menu_item_detail.html
    """
    menu_item = get_object_or_404(MenuItem, id=item_id, is_available=True)
    
    context = {
        'menu_item': menu_item,
        'restaurant': menu_item.restaurant,
        'page_title': menu_item.name
    }
    
    return render(request, 'restaurants/menu_item_detail.html', context)
