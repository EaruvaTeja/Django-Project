"""
Cart App Models

This app owns the DATABASE-BACKED shopping cart for the REST API.

Architecture:
    User
     │ OneToOne
     ▼
    Cart
     │ ForeignKey
     ▼
    CartItem
     │ ForeignKey
     ▼
    MenuItem
     │ ForeignKey
     ▼
    Restaurant

Key rules:
- One cart per user (OneToOne).
- A cart can contain items from only ONE restaurant at a time.
- An empty cart has restaurant = NULL.
- No duplicate menu_item within the same cart (UniqueConstraint).
- quantity must be at least 1 (enforced at DB level via CheckConstraint).
- CartItem uses the CURRENT MenuItem.price (no snapshot here).
  Price snapshots happen later, on OrderItem, when the order is placed.
"""

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Cart(models.Model):
    """
    Shopping cart belonging to one authenticated user.

    Rules:
    - One user can have only one cart (enforced by OneToOneField).
    - A cart can contain items from only one restaurant at a time.
    - An empty cart can have restaurant=None.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart',
        help_text='The user who owns this cart'
    )

    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='carts',
        help_text=(
            'The restaurant currently associated with this cart. '
            'NULL means the cart is empty.'
        )
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Cart'
        verbose_name_plural = 'Carts'

    def __str__(self):
        if self.restaurant:
            return f"Cart #{self.id} - {self.user} - {self.restaurant.name}"
        return f"Cart #{self.id} - {self.user} - Empty"

    # ------------------------------------------------------------------
    # Helper properties
    # ------------------------------------------------------------------

    @property
    def is_empty(self):
        """
        Return True if the cart has no items.

        Useful in views/validation to quickly check state without
        writing `cart.items.exists()` all over the codebase.
        """
        return not self.items.exists()

    @property
    def total(self):
        """
        Calculate the current cart total from its items.

        Uses the CURRENT MenuItem.price for each item (no snapshot).
        Optimized with select_related to avoid N+1 queries.
        """
        return sum(
            item.subtotal
            for item in self.items.select_related('menu_item').all()
        )

    @property
    def item_count(self):
        """
        Return the total number of products in the cart,
        including quantities.

        Example:
            Biryani × 2, Coke × 1  →  item_count = 3
        """
        return sum(
            item.quantity
            for item in self.items.all()
        )


class CartItem(models.Model):
    """
    Individual menu item stored inside a user's cart.

    Example:

    Cart #1
        ├── Chicken Biryani × 2
        └── Coke × 1

    Rules:
    - Belongs to exactly one Cart.
    - References exactly one MenuItem.
    - quantity >= 1 (enforced at DB level).
    - No duplicate (cart, menu_item) pairs — adding an existing item
      should increment its quantity instead of creating a new row.
    - Uses CURRENT menu price for subtotal (no snapshot).
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='The cart this item belongs to'
    )

    menu_item = models.ForeignKey(
        'restaurants.MenuItem',
        on_delete=models.CASCADE,
        related_name='cart_items',
        help_text='The menu item added to the cart'
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1)
        ],
        help_text='Quantity of this menu item in the cart'
    )

    special_instructions = models.TextField(
        blank=True,
        default='',
        help_text='Optional instructions for this menu item'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Cart Item'
        verbose_name_plural = 'Cart Items'

        constraints = [
            # 1. Prevent duplicate MenuItem entries within the same cart.
            #    Adding an existing item should increment quantity instead.
            models.UniqueConstraint(
                fields=['cart', 'menu_item'],
                name='unique_menu_item_per_cart'
            ),

            # 2. Database-level guarantee that quantity is never less than 1.
            #    PositiveIntegerField allows 0, so this is the safety net
            #    for data coming from raw SQL or admin misuse.
            #
            # NOTE: Django 5.1+ renamed the `check` kwarg to `condition`.
            #       Django 6.x removed the old `check` kwarg entirely.
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name='cart_item_quantity_gte_1'
            ),
        ]

    def __str__(self):
        return (
            f"{self.quantity}x "
            f"{self.menu_item.name} "
            f"in Cart #{self.cart.id}"
        )

    @property
    def subtotal(self):
        """
        Calculate the current subtotal:

            current MenuItem.price × quantity

        Note: Uses the LIVE menu price. A snapshot is only taken
        later when an OrderItem is created from this cart item.
        """
        return self.menu_item.price * self.quantity
