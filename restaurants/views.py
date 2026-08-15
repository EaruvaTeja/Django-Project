from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.utils import timezone
from .models import Restaurant
from .forms import RestaurantForm
from meals.models import Meal
from meals.forms import MealForm, MealSearchForm


def dashboard(request):
    """Basic restaurant dashboard"""
    restaurants = Restaurant.objects.all()
    return render(request, 'restaurants/dashboard.html', {'restaurants': restaurants})


def restaurant_dashboard(request, restaurant_id=None):
    """Detailed restaurant dashboard for owners and admins"""
    restaurants = Restaurant.objects.all()
    
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    else:
        restaurant = restaurants.first() if restaurants.exists() else None
    
    meals = []
    meals_paginator = None
    meals_page_obj = None
    
    if restaurant:
        all_meals = Meal.objects.filter(restaurant=restaurant).order_by('-created_at')
        meals_paginator = Paginator(all_meals, 5)
        page_number = request.GET.get('meals_page', 1)
        meals_page_obj = meals_paginator.get_page(page_number)
        meals = meals_page_obj
    
    recent_orders = []
    
    context = {
        'restaurant': restaurant,
        'restaurants': restaurants,
        'meals': meals,
        'meals_page_obj': meals_page_obj,
        'meals_paginator': meals_paginator,
        'is_meals_paginated': meals_page_obj.has_other_pages() if meals_page_obj else False,
        'recent_orders': recent_orders,
    }
    return render(request, 'restaurants/restaurant_dashboard.html', context)


def manage_meals(request, restaurant_id=None):
    """Manage meals for restaurant"""
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    else:
        restaurants = Restaurant.objects.all()
        restaurant = restaurants.first() if restaurants.exists() else None
    
    if not restaurant:
        messages.error(request, 'No restaurant found.')
        return redirect('restaurants:restaurant_dashboard')
    
    search_form = MealSearchForm(request.GET)
    meals = Meal.objects.filter(restaurant=restaurant)
    
    if search_form.is_valid():
        search = search_form.cleaned_data.get('search')
        is_available = search_form.cleaned_data.get('is_available')
        
        if search:
            meals = meals.filter(name__icontains=search)
        if is_available:
            meals = meals.filter(is_available=(is_available == 'true'))
    
    paginator = Paginator(meals, 10)
    page_number = request.GET.get('page')
    meals = paginator.get_page(page_number)
    
    context = {
        'restaurant': restaurant,
        'meals': meals,
        'search_form': search_form,
    }
    return render(request, 'restaurants/manage_meals.html', context)


def add_meal(request, restaurant_id=None):
    """Add a new meal"""
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    else:
        restaurants = Restaurant.objects.all()
        restaurant = restaurants.first() if restaurants.exists() else None
    
    if not restaurant:
        messages.error(request, 'No restaurant found.')
        return redirect('restaurants:restaurant_dashboard')
    
    if request.method == 'POST':
        form = MealForm(request.POST, request.FILES, restaurant=restaurant)
        if form.is_valid():
            meal = form.save(commit=False)
            meal.restaurant = restaurant
            meal.save()
            messages.success(request, f'Meal "{meal.name}" added successfully!')
            return redirect('restaurants:manage_meals_for_restaurant', restaurant_id=restaurant.id)
    else:
        form = MealForm(restaurant=restaurant)
    
    context = {
        'form': form,
        'restaurant': restaurant,
    }
    return render(request, 'restaurants/access_meal.html', context)


def edit_meal(request, meal_id):
    """Edit an existing meal"""
    meal = get_object_or_404(Meal, id=meal_id)
    
    if request.method == 'POST':
        form = MealForm(request.POST, request.FILES, instance=meal, restaurant=meal.restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, f'Meal "{meal.name}" updated successfully!')
            return redirect('restaurants:manage_meals_for_restaurant', restaurant_id=meal.restaurant.id)
    else:
        form = MealForm(instance=meal, restaurant=meal.restaurant)
    
    context = {
        'form': form,
        'meal': meal,
        'restaurant': meal.restaurant,
    }
    return render(request, 'restaurants/edit_meal.html', context)


def delete_meal(request, meal_id):
    """Delete a meal"""
    meal = get_object_or_404(Meal, id=meal_id)
    
    if request.method == 'POST':
        meal_name = meal.name
        meal.delete()
        messages.success(request, f'Meal "{meal_name}" deleted successfully!')
        return redirect('restaurants:manage_meals_for_restaurant', restaurant_id=meal.restaurant.id)
    
    context = {
        'meal': meal,
    }
    return render(request, 'restaurants/delete_meal.html', context)


def toggle_meal_availability(request, meal_id):
    """Toggle meal availability via AJAX"""
    meal = get_object_or_404(Meal, id=meal_id)
    
    if request.method == 'POST':
        meal.is_available = not meal.is_available
        meal.save()
        return JsonResponse({
            'success': True,
            'is_available': meal.is_available,
            'message': f'Meal is now {"available" if meal.is_available else "unavailable"}'
        })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def restaurant_settings(request, restaurant_id=None):
    """Restaurant settings and profile management"""
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    else:
        restaurants = Restaurant.objects.all()
        restaurant = restaurants.first() if restaurants.exists() else None
    
    if not restaurant:
        messages.error(request, 'No restaurant found.')
        return redirect('restaurants:restaurant_dashboard')
    
    if request.method == 'POST':
        form = RestaurantForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            form.save()
            if 'hero_image' in request.FILES:
                messages.success(request, 'Restaurant settings and hero image updated successfully!')
            else:
                messages.success(request, 'Restaurant settings updated successfully!')
            return redirect('restaurants:restaurant_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RestaurantForm(instance=restaurant)
    
    total_meals = Meal.objects.filter(restaurant=restaurant).count()
    available_meals = Meal.objects.filter(restaurant=restaurant, is_available=True).count()
    
    context = {
        'form': form,
        'restaurant': restaurant,
        'total_meals': total_meals,
        'available_meals': available_meals,
        'total_orders': 0,
        'total_revenue': 0.0,
    }
    return render(request, 'restaurants/restaurant_settings.html', context)


def restaurant_detail(request, restaurant_id):
    """Public restaurant detail page for customers"""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    
    meals = Meal.objects.filter(restaurant=restaurant, is_available=True).order_by('name')
    total_meals = meals.count()
    avg_rating = restaurant.overall_rating or 4.5
    similar_restaurants = Restaurant.objects.exclude(id=restaurant_id)[:3]
    
    context = {
        'restaurant': restaurant,
        'meals': meals,
        'total_meals': total_meals,
        'avg_rating': avg_rating,
        'similar_restaurants': similar_restaurants,
    }
    return render(request, 'restaurants/restaurant_detail.html', context)


def restaurant_orders(request, restaurant_id=None):
    """Restaurant orders page (dummy data for viewing template)"""
    if restaurant_id:
        restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    else:
        restaurants = Restaurant.objects.all()
        restaurant = restaurants.first() if restaurants.exists() else None
    
    class DummyUser:
        def __init__(self):
            self.username = 'demo_user'
            self.email = 'demo@example.com'
        def get_full_name(self):
            return self.username
    
    class DummyItems:
        def all(self):
            return []
    
    class DummyOrder:
        def __init__(self, pk):
            self.id = pk
            self.created_at = timezone.now()
            self.user = DummyUser()
            self.status = 'pending'
            self.total_amount = 0.0
            self.items = DummyItems()
        
        def get_status_display(self):
            return self.status.title()
    
    dummy_orders = [DummyOrder(i) for i in range(1, 4)]
    
    paginator = Paginator(dummy_orders, 10)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)
    
    context = {
        'restaurant': restaurant,
        'orders': orders,
    }
    return render(request, 'restaurants/restaurant_orders.html', context)
