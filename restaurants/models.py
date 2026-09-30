"""
Restaurants App Models

This app handles:
- Restaurant information (name, address, cuisine type, rating, etc.)
- Menu items/meals associated with each restaurant
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Restaurant(models.Model):
    """
    Restaurant model - stores information about food establishments.

    Fields:
    - name: Restaurant name
    - description: Brief description of the restaurant
    - address: Full address
    - cuisine_type: Type of cuisine (e.g., Italian, Chinese, Indian)
    - rating: Average customer rating (1-5)
    - delivery_time: Estimated delivery time in minutes
    - distance_km: Approximate delivery distance from customer (in km)    
    - image: Optional cover image of the restaurant
    - is_active: Whether the restaurant is currently accepting orders
    - created_at: When the restaurant was added
    """
    name = models.CharField(max_length=200, help_text="Name of the restaurant")
    description = models.TextField(help_text="Brief description of the restaurant")
    address = models.CharField(max_length=500, help_text="Full address of the restaurant")
    cuisine_type = models.CharField(
        max_length=100,
        help_text="Type of cuisine (e.g., Italian, Chinese, Indian)"
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0,
        help_text="Average customer rating (0-5)"
    )
    delivery_time = models.IntegerField(
        default=30,
        help_text="Estimated delivery time in minutes"
    )

    distance_km = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=5.00,
        validators=[MinValueValidator(0)],
        help_text="Approximate delivery distance from customer (in km)"
    )

    image = models.ImageField(
        upload_to='restaurants/',
        blank=True,
        null=True,
        help_text="Cover image of the restaurant (optional)"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the restaurant is currently accepting orders"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-rating', 'name']  # Sort by rating (highest first), then by name

    def __str__(self):
        return f"{self.name} ({self.cuisine_type})"

    def get_menu_items(self):
        """Helper method to get all menu items for this restaurant"""
        return self.menu_items.filter(is_available=True)


class MenuItem(models.Model):
    """
    MenuItem model - represents individual dishes/meals on a restaurant's menu.

    Fields:
    - restaurant: ForeignKey to Restaurant (one restaurant has many menu items)
    - name: Name of the dish
    - description: Description of the dish
    - price: Price of the dish
    - image: Optional image of the dish
    - is_vegetarian: Whether the dish is vegetarian
    - is_available: Whether the dish is currently available
    - category: Category of the dish (e.g., Appetizer, Main Course, Dessert)
    """
    CATEGORY_CHOICES = [
        ('appetizer', 'Appetizer'),
        ('main_course', 'Main Course'),
        ('dessert', 'Dessert'),
        ('beverage', 'Beverage'),
        ('side', 'Side Dish'),
    ]

    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='menu_items',
        help_text="The restaurant this menu item belongs to"
    )
    name = models.CharField(max_length=200, help_text="Name of the dish")
    description = models.TextField(help_text="Description of the dish")
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price of the dish"
    )
    image = models.ImageField(
        upload_to='menu_items/',
        blank=True,
        null=True,
        help_text="Image of the dish (optional)"
    )
    is_vegetarian = models.BooleanField(
        default=False,
        help_text="Whether the dish is vegetarian"
    )
    is_available = models.BooleanField(
        default=True,
        help_text="Whether the dish is currently available"
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='main_course',
        help_text="Category of the dish"
    )
        # ─────────── ADD THESE TWO FIELDS ───────────
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0,
        help_text="Average rating for this dish (0-5)"
    )
    rating_count = models.PositiveIntegerField(
        default=0,
        help_text="How many customers rated this dish (e.g., 1200 for 1.2K+)"
    )
    # ─────────── END ADD ───────────
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} - ₹{self.price}"