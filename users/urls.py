"""
Users App URL Configuration

This file defines the URL patterns for user authentication views.
These URLs are included in the main project's urls.py.

URL Patterns:
- /users/register/ -> register_view (GET: show form, POST: create user)
- /users/login/ -> login_view (GET: show form, POST: authenticate)
- /users/logout/ -> logout_view (logout current user)
- /users/profile/ -> profile_view (user's profile and order history)
"""

from django.urls import path
from . import views

app_name = 'users'  # Namespace for URL reversing (e.g., 'users:login')

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
]
