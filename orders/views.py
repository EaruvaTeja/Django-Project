"""
Orders App Views

This app handles:
1. Traditional Django views for order-related pages (cart, order history)
2. REST API endpoints using Django REST Framework for placing orders

REST API Explanation:
- DRF (Django REST Framework) allows us to create API endpoints that return JSON
- Serializers convert complex data (like model instances) to/from JSON
- API Views handle HTTP methods (GET, POST, PUT, DELETE) separately

Data Flow for API:
1. Client sends POST request with JSON data to /api/orders/place/
2. Request goes through URL router to PlaceOrderView
3. Serializer validates the incoming data
4. View creates Order and OrderItem objects in the database
5. Response sent back as JSON with order details
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Order, OrderItem
from restaurants.models import MenuItem, Restaurant


@login_required
def cart_view(request):
    """
    Display the user's shopping cart.
    
    For simplicity, we're storing cart data in the session.
    In a production app, you might use a dedicated Cart model.
    
    Session-based cart structure:
    cart = {
        'items': [
            {'menu_item_id': 1, 'quantity': 2, 'special_instructions': 'Extra spicy'},
            ...
        ],
        'restaurant_id': 5
    }
    
    Template: orders/cart.html
    """
    # Get cart from session (or empty dict if not exists)
    cart = request.session.get('cart', {'items': []})
    
    # Fetch menu items for items in cart
    cart_items = []
    total = 0
    
    for item in cart.get('items', []):
        try:
            menu_item = MenuItem.objects.get(id=item['menu_item_id'], is_available=True)
            item_total = float(menu_item.price) * item['quantity']
            total += item_total
            cart_items.append({
                'menu_item': menu_item,
                'quantity': item['quantity'],
                'special_instructions': item.get('special_instructions', ''),
                'item_total': item_total
            })
        except MenuItem.DoesNotExist:
            # Item no longer available, skip it
            continue
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'page_title': 'Your Cart'
    }
    
    return render(request, 'orders/cart.html', context)


@login_required
def add_to_cart(request, menu_item_id):
    """
    Add a menu item to the cart.
    
    This uses Django sessions to persist cart data across requests.
    The session is stored in the database (configured in settings.py).
    
    POST parameters:
    - quantity: Number of items to add
    - special_instructions: Any special requests
    - restaurant_id: ID of the restaurant (to ensure all items are from same restaurant)
    """
    if request.method == 'POST':
        menu_item = get_object_or_404(MenuItem, id=menu_item_id, is_available=True)
        
        # Get or initialize cart from session
        cart = request.session.get('cart', {'items': []})
        
        # Check if cart already has items from a different restaurant
        if cart.get('restaurant_id') and cart['restaurant_id'] != int(request.POST.get('restaurant_id', menu_item.restaurant.id)):
            # Clear cart if adding from different restaurant
            cart = {'items': [], 'restaurant_id': menu_item.restaurant.id}
        
        quantity = int(request.POST.get('quantity', 1))
        special_instructions = request.POST.get('special_instructions', '')
        
        # Check if item already in cart
        found = False
        for item in cart['items']:
            if item['menu_item_id'] == menu_item_id:
                item['quantity'] += quantity
                if special_instructions:
                    item['special_instructions'] = special_instructions
                found = True
                break
        
        if not found:
            cart['items'].append({
                'menu_item_id': menu_item_id,
                'quantity': quantity,
                'special_instructions': special_instructions
            })
        
        cart['restaurant_id'] = menu_item.restaurant.id
        
        # Save cart back to session
        request.session['cart'] = cart
        
        # Redirect to cart page or back to referring page
        next_url = request.GET.get('next', 'orders:cart')
        return redirect(next_url)
    
    return redirect('restaurants:restaurant_list')


@login_required
def clear_cart(request):
    """Clear the entire cart."""
    if request.method == 'POST':
        request.session['cart'] = {'items': []}
    return redirect('orders:cart')


@login_required
def order_history(request):
    """
    Display user's order history.
    
    Shows all past orders with their status and items.
    
    Template: orders/order_history.html
    """
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
        'page_title': 'Order History'
    }
    
    return render(request, 'orders/order_history.html', context)


# =============================================================================
# REST API VIEWS - Django REST Framework
# =============================================================================

class PlaceOrderView(APIView):
    """
    REST API endpoint for placing an order.
    
    This demonstrates how Django REST Framework works:
    1. Receives JSON data via POST request
    2. Validates data using a Serializer
    3. Creates database records (Order and OrderItems)
    4. Returns JSON response with created order details
    
    URL: /api/orders/place/
    Method: POST
    Authentication: Required (IsAuthenticated permission)
    
    Expected JSON payload:
    {
        "items": [
            {"menu_item_id": 1, "quantity": 2, "special_instructions": "Extra spicy"},
            {"menu_item_id": 5, "quantity": 1}
        ],
        "delivery_address": "123 Main St, City",
        "notes": "Please ring the bell"
    }
    
    Response on success:
    {
        "order_id": 1,
        "status": "pending",
        "total_amount": "25.50",
        "message": "Order placed successfully"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Get items and other data from request
        items_data = request.data.get('items', [])
        delivery_address = request.data.get('delivery_address', '')
        notes = request.data.get('notes', '')
        
        # Validate that we have items to order
        if not items_data:
            return Response(
                {'error': 'No items in order'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate that we have a delivery address
        if not delivery_address:
            return Response(
                {'error': 'Delivery address is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the first item to determine the restaurant
        # (All items must be from the same restaurant)
        try:
            first_item = items_data[0]
            menu_item = MenuItem.objects.get(id=first_item['menu_item_id'])
            restaurant = menu_item.restaurant
        except MenuItem.DoesNotExist:
            return Response(
                {'error': f"Menu item with id {first_item['menu_item_id']} not found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create the Order object
        order = Order.objects.create(
            user=request.user,
            restaurant=restaurant,
            delivery_address=delivery_address,
            notes=notes,
            status='pending'
        )
        
        # Create OrderItem objects for each item in the order
        total_amount = 0
        for item_data in items_data:
            try:
                menu_item = MenuItem.objects.get(id=item_data['menu_item_id'])
                
                # Verify all items are from the same restaurant
                if menu_item.restaurant != restaurant:
                    order.delete()  # Clean up the order
                    return Response(
                        {'error': 'All items must be from the same restaurant'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                quantity = item_data.get('quantity', 1)
                special_instructions = item_data.get('special_instructions', '')
                
                # Create the order item
                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=quantity,
                    price=menu_item.price,  # Snapshot of price at time of order
                    special_instructions=special_instructions
                )
                
                total_amount += float(menu_item.price) * quantity
                
            except MenuItem.DoesNotExist:
                order.delete()  # Clean up the order
                return Response(
                    {'error': f"Menu item with id {item_data['menu_item_id']} not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Update order total
        order.total_amount = total_amount
        order.save()
        
        # Return success response with order details
        return Response({
            'order_id': order.id,
            'status': order.status,
            'total_amount': str(order.total_amount),
            'message': 'Order placed successfully',
            'restaurant': restaurant.name
        }, status=status.HTTP_201_CREATED)


@login_required
def checkout_view(request):
    """
    Traditional view-based checkout page (non-API alternative).
    
    This shows a form-based approach alongside the API approach.
    Users can place orders either through the web interface or via API.
    
    Template: orders/checkout.html
    """
    cart = request.session.get('cart', {'items': []})
    
    if not cart.get('items'):
        return redirect('orders:cart')
    
    # Calculate total and get items
    cart_items = []
    total = 0
    
    for item in cart.get('items', []):
        try:
            menu_item = MenuItem.objects.get(id=item['menu_item_id'], is_available=True)
            item_total = float(menu_item.price) * item['quantity']
            total += item_total
            cart_items.append({
                'menu_item': menu_item,
                'quantity': item['quantity'],
                'special_instructions': item.get('special_instructions', ''),
                'item_total': item_total
            })
        except MenuItem.DoesNotExist:
            continue
    
    if request.method == 'POST':
        # Process the order
        delivery_address = request.POST.get('delivery_address', '')
        notes = request.POST.get('notes', '')
        
        if not delivery_address:
            return render(request, 'orders/checkout.html', {
                'cart_items': cart_items,
                'total': total,
                'error': 'Delivery address is required',
                'page_title': 'Checkout'
            })
        
        # Get restaurant from first item
        restaurant = cart_items[0]['menu_item'].restaurant
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            restaurant=restaurant,
            delivery_address=delivery_address,
            notes=notes,
            total_amount=total,
            status='pending'
        )
        
        # Create order items
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                menu_item=item['menu_item'],
                quantity=item['quantity'],
                price=item['menu_item'].price,
                special_instructions=item['special_instructions']
            )
        
        # Clear cart
        request.session['cart'] = {'items': []}
        
        return redirect('orders:order_detail', order_id=order.id)
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'page_title': 'Checkout'
    }
    
    return render(request, 'orders/checkout.html', context)


@login_required
def order_detail(request, order_id):
    """
    Display details of a specific order.
    
    Template: orders/order_detail.html
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
        'page_title': f'Order #{order.id}'
    }
    
    return render(request, 'orders/order_detail.html', context)
