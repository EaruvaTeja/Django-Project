"""
URL configuration for swiggy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from restaurants import views

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    
    # This points to your restaurants app
    path("restaurants/", include("restaurants.urls")),
    
    # This points to your meals app
    path("meals/", include("meals.urls")),
    
    # Optional: Make restaurants the default homepage when you visit 127.0.0.1:8000/
    path("", views.dashboard, name='home'),
]

# This allows your browser to display the ImageFields you fixed earlier
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)