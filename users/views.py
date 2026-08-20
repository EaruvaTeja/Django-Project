"""
Users App Views

This app handles user authentication using Django's built-in auth views.
We're using Django's class-based generic views for common authentication tasks.

Data Flow:
1. User visits a URL (e.g., /users/login/)
2. URL router directs to the appropriate view function/class
3. View processes the request (validates form, authenticates user)
4. View returns a response (renders template or redirects)
"""

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.models import User


def register_view(request):
    """
    Handle user registration.
    
    GET: Display empty registration form
    POST: Validate and create new user, then log them in
    
    Template: users/register.html
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            # Save the new user to the database
            user = form.save()
            # Log the user in automatically after registration
            login(request, user)
            # Redirect to homepage after successful registration
            return redirect('home')
    else:
        form = UserCreationForm()
    
    context = {
        'form': form,
        'page_title': 'Register'
    }
    return render(request, 'users/register.html', context)


def login_view(request):
    """
    Handle user login.
    
    GET: Display empty login form
    POST: Authenticate credentials and log user in
    
    Template: users/login.html
    
    How authentication works:
    1. authenticate() checks if username/password are valid
    2. If valid, returns a User object; if not, returns None
    3. login() creates a session for the authenticated user
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Get the validated credentials
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Verify the credentials against the database
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # Create a session for the user
                login(request, user)
                
                # Redirect to next page if specified, otherwise homepage
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
    else:
        form = AuthenticationForm()
    
    context = {
        'form': form,
        'page_title': 'Login'
    }
    return render(request, 'users/login.html', context)


def logout_view(request):
    """
    Handle user logout.
    
    Clears the user's session and redirects to homepage.
    
    Note: This can be accessed via GET or POST for simplicity.
    In production, you might want to require POST for security.
    """
    logout(request)
    return redirect('home')


@login_required
def profile_view(request):
    """
    Display user's profile page with their order history.
    
    The @login_required decorator ensures only logged-in users can access this.
    If not logged in, redirects to login page.
    
    Template: users/profile.html
    """
    from orders.models import Order
    
    # Get all orders for this user
    user_orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'user': request.user,
        'orders': user_orders,
        'page_title': f'{request.user.username}\'s Profile'
    }
    return render(request, 'users/profile.html', context)
