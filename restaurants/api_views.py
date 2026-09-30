from rest_framework import generics
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Restaurant, MenuItem
from .api_serializers import RestaurantSerializer, MenuItemSerializer
# for search results imported Q
from django.db.models import Q

# menu items for home page
from .api_serializers import (
    RestaurantSerializer,
    MenuItemSerializer,
    MenuItemWithRestaurantSerializer,
)
from rest_framework.permissions import AllowAny


class IsAdminOrReadOnly(BasePermission):
    """
    Anyone can read.
    Only staff/admin users can create, update, or delete.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return request.user.is_authenticated and request.user.is_staff


# ============================================================
# RESTAURANT APIs
# ============================================================


class RestaurantListAPIView(generics.ListCreateAPIView):
    """
    GET  /api/restaurants/
        Returns restaurants.

    POST /api/restaurants/
        Creates a restaurant.
        Staff/admin only.
    """

    serializer_class = RestaurantSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        # Base queryset
        if self.request.user.is_authenticated and self.request.user.is_staff:
            queryset = Restaurant.objects.all()
        else:
            queryset = Restaurant.objects.filter(is_active=True)

        # ------------------------------------------------------------------
        # Search filter (?q=...)
        # ------------------------------------------------------------------
        # Matches restaurant name, cuisine_type, OR any menu item name.
        # Distinct because the menu_items join can duplicate rows.
        q = self.request.query_params.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q)
                | Q(cuisine_type__icontains=q)
                | Q(menu_items__name__icontains=q)
            ).distinct()

        return queryset


class RestaurantDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/restaurants/<id>/
        Returns one restaurant.

    PUT    /api/restaurants/<id>/
        Updates the complete restaurant.
        Staff/admin only.

    PATCH  /api/restaurants/<id>/
        Updates selected restaurant fields.
        Staff/admin only.

    DELETE /api/restaurants/<id>/
        Deletes the restaurant.
        Staff/admin only.
    """

    serializer_class = RestaurantSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_authenticated and self.request.user.is_staff:
            return Restaurant.objects.all()

        return Restaurant.objects.filter(is_active=True)


# ============================================================
# MENU APIs
# ============================================================


class RestaurantMenuListAPIView(generics.ListCreateAPIView):
    """
    GET  /api/restaurants/<restaurant_id>/menu/
        Returns available menu items for a restaurant.

    POST /api/restaurants/<restaurant_id>/menu/
        Creates a menu item for the restaurant.
        Staff/admin only.
    """

    serializer_class = MenuItemSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        restaurant_id = self.kwargs['restaurant_id']

        queryset = MenuItem.objects.filter(
            restaurant_id=restaurant_id
        )

        if self.request.user.is_authenticated and self.request.user.is_staff:
            return queryset

        return queryset.filter(
            restaurant__is_active=True,
            is_available=True
        )

    def perform_create(self, serializer):
        restaurant_id = self.kwargs['restaurant_id']

        restaurant = Restaurant.objects.get(
            id=restaurant_id
        )

        serializer.save(restaurant=restaurant)


class MenuItemDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/restaurants/<restaurant_id>/menu/<pk>/
        Returns one menu item belonging to that restaurant.

    PUT    /api/restaurants/<restaurant_id>/menu/<pk>/
        Updates the complete menu item.
        Staff/admin only.

    PATCH  /api/restaurants/<restaurant_id>/menu/<pk>/
        Updates selected menu item fields.
        Staff/admin only.

    DELETE /api/restaurants/<restaurant_id>/menu/<pk>/
        Deletes the menu item.
        Staff/admin only.
    """

    serializer_class = MenuItemSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        restaurant_id = self.kwargs['restaurant_id']

        queryset = MenuItem.objects.filter(
            restaurant_id=restaurant_id
        ).select_related('restaurant')

        if self.request.user.is_authenticated and self.request.user.is_staff:
            return queryset

        return queryset.filter(
            restaurant__is_active=True,
            is_available=True
        )

# ============================================================
# ALL MENU ITEMS (home showcase)
# ============================================================


class AllMenuItemsAPIView(generics.ListAPIView):
    """
    GET /api/menu-items/

    Returns all available menu items across all active restaurants.
    Used by the home page showcase. Random pick happens on the client.

    Filters:
      - MenuItem.is_available = True
      - Restaurant.is_active = True
    """

    serializer_class = MenuItemWithRestaurantSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return (
            MenuItem.objects
            .filter(is_available=True, restaurant__is_active=True)
            .select_related('restaurant')
            .order_by('-rating_count', '-rating')
        )