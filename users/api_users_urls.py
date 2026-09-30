from django.urls import path
from .api_views import ProfileAPIView

urlpatterns = [
    path('profile/', ProfileAPIView.as_view(), name='api_profile'),
]