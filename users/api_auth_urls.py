# Import the 'path' function to define URL patterns
from django.urls import path

# Import our API Views from the users app
from .api_views import RegisterAPIView, LogoutAPIView #LoginAPIView


# This list defines the API endpoints inside the 'auth' URL group.
# The '/api/auth/' prefix is already added in swiggy/urls.py.
urlpatterns = [

    # User registration API
    # Full URL: POST /api/auth/register/
    path(
        'register/',RegisterAPIView.as_view(),name='api_register'),
        path(
        'logout/',LogoutAPIView.as_view(),name='api_logout'),

    # NOTE:
    # The JWT login endpoint is handled directly by
    # TokenObtainPairView in swiggy/urls.py.
    #
    # Therefore, we DO NOT put a login path here.
]