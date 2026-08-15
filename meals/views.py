from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Meal


def meal_list(request):
    meals = Meal.objects.filter(is_available=True)
    restaurant = None
    
    restaurant_id = request.GET.get('restaurant')
    if restaurant_id:
        try:
            from restaurants.models import Restaurant
            restaurant = Restaurant.objects.get(id=restaurant_id)
            meals = meals.filter(restaurant=restaurant)
        except Restaurant.DoesNotExist:
            pass
    else:
        meals = meals.order_by('?')
    
    for meal in meals:
        meal.is_favorite = False
    
    paginator = Paginator(meals, 6)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'meals': page_obj,
        'restaurant': restaurant,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    }
    return render(request, 'meals/meal_list.html', context)


def meal_detail(request, meal_id):
    """Display meal detail page"""
    meal = get_object_or_404(Meal, id=meal_id)
    meal.is_favorite = False
    
    context = {
        'meal': meal,
    }
    return render(request, 'meals/product_detail.html', context)


def add_to_cart(request, meal_id):
    """Add meal to cart (Currently Disabled due to removed Orders app)"""
    if request.method == 'POST':
        return JsonResponse({
            'success': False, 
            'error': 'The ordering system is currently disabled.'
        })
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def toggle_favorite(request, meal_id):
    """Add or remove meal from user's favorites"""
    return JsonResponse({'success': False, 'error': 'Favorites are currently disabled.'})


def user_favorites(request):
    """Display user's favorite meals"""
    context = {
        'meals': [],
        'page_obj': None,
        'is_paginated': False,
        'title': 'My Favorite Meals'
    }
    return render(request, 'meals/meal_list.html', context)
