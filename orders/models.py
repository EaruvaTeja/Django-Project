"""
Orders App Models

This app handles:
- Order management (placing orders, order status)
- Order items (individual items in an order)
- Cart functionality (stored in session for simplicity)
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from restaurants.models import MenuItem


class Order(models.Model):
    """
    Order model - represents a customer's order.
    
    Fields:
    - user: ForeignKey to User (who placed the order)
    - restaurant: ForeignKey to Restaurant (where the order was placed)
    - total_amount: Total cost of the order
    - status: Current status of the order (pending, confirmed, preparing, out_for_delivery, delivered, cancelled)
    - delivery_address: Address where the order should be delivered
    - created_at: When the order was placed
    - updated_at: Last update time
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('preparing', 'Preparing'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
        help_text="User who placed the order"
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='orders',
        help_text="Restaurant where the order was placed"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        help_text="Total cost of the order"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current status of the order"
    )
    delivery_address = models.TextField(
        help_text="Delivery address for the order"
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Special instructions or notes for the order"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']  # Most recent orders first
    
    def __str__(self):
        return f"Order #{self.id} by {self.user.username} - ${self.total_amount}"
    
    def calculate_total(self):
        """Calculate and update the total amount based on order items"""
        total = sum(item.subtotal for item in self.items.all())
        self.total_amount = total
        self.save()
        return total


class OrderItem(models.Model):
    """
    OrderItem model - represents individual items within an order.
    
    This creates a many-to-many relationship between Order and MenuItem
    with additional fields like quantity and special instructions.
    
    Fields:
    - order: ForeignKey to Order
    - menu_item: ForeignKey to MenuItem (what was ordered)
    - quantity: Number of this item ordered
    - price: Price at the time of order (snapshot, won't change if menu price changes)
    - special_instructions: Any special requests for this item
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="The order this item belongs to"
    )
    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.CASCADE,
        related_name='order_items',
        help_text="The menu item that was ordered"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Quantity of this item ordered"
    )
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price at the time of order (snapshot)"
    )
    special_instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Special instructions for this item"
    )
    
    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name} for Order #{self.order.id}"
    
    @property
    def subtotal(self):
        """Calculate subtotal for this order item (price * quantity)"""
        return self.price * self.quantity
