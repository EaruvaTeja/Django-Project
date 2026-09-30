"""
Users App Models

Currently uses Django's built-in User model.
We add a custom Address model to store up to 10 delivery addresses per user.
"""

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


class Address(models.Model):
    """
    A saved delivery address belonging to a user.

    Rules (enforced in serializer):
      - Max 10 addresses per user
      - Max 3 of type 'home', 3 'office', 4 'other'
      - Exactly one is_default per user (enforced in save())
      - First address for a new user becomes the default automatically

    Deleting the default address promotes the next oldest to default.
    """

    ADDRESS_TYPE_CHOICES = [
        ('home', 'Home'),
        ('office', 'Office'),
        ('other', 'Other'),
    ]

    # Limits (used by AddressSerializer for validation)
    MAX_ADDRESSES_PER_USER = 10
    MAX_HOME = 3
    MAX_OFFICE = 3
    MAX_OTHER = 4

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses',
        help_text="Owner of this address",
    )

    # ------------------------------------------------------------------
    # Type & label
    # ------------------------------------------------------------------
    address_type = models.CharField(
        max_length=10,
        choices=ADDRESS_TYPE_CHOICES,
        default='home',
        help_text="Home / Office / Other",
    )
    label = models.CharField(
        max_length=50,
        help_text="Short user-given name, e.g. 'Mom's place'",
    )

    # ------------------------------------------------------------------
    # Contact info
    # ------------------------------------------------------------------
    full_name = models.CharField(
        max_length=100,
        help_text="Name of the recipient at this address",
    )
    phone = models.CharField(
        max_length=15,
        validators=[
            RegexValidator(
                regex=r'^\d{10}$',
                message='Phone must be exactly 10 digits.',
            )
        ],
    )

    # ------------------------------------------------------------------
    # Address lines
    # ------------------------------------------------------------------
    line1 = models.CharField(
        max_length=200,
        help_text="Flat / building / street",
    )
    line2 = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Area / locality (optional)",
    )
    landmark = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Nearby landmark (optional)",
    )
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(
        max_length=6,
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message='Pincode must be exactly 6 digits.',
            )
        ],
    )

    # ------------------------------------------------------------------
    # Default flag
    # ------------------------------------------------------------------
    is_default = models.BooleanField(
        default=False,
        help_text="If true, this is the user's preferred delivery address.",
    )

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_default', '-updated_at']
        verbose_name = 'Address'
        verbose_name_plural = 'Addresses'

    def __str__(self):
        return f"{self.label} · {self.full_name} · {self.city}"

    # ------------------------------------------------------------------
    # Custom save — enforces single default per user
    # ------------------------------------------------------------------
    def save(self, *args, **kwargs):
        # First address for a user is auto-default
        if not self.pk and not Address.objects.filter(user=self.user).exists():
            self.is_default = True

        # If this one is becoming default, unset all others for this user
        if self.is_default:
            Address.objects.filter(
                user=self.user,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)

        super().save(*args, **kwargs)

    # ------------------------------------------------------------------
    # Custom delete — promotes another address if the default is removed
    # ------------------------------------------------------------------
    def delete(self, *args, **kwargs):
        was_default = self.is_default
        owner = self.user
        super().delete(*args, **kwargs)

        if was_default:
            next_addr = Address.objects.filter(user=owner).first()
            if next_addr:
                next_addr.is_default = True
                next_addr.save(update_fields=['is_default'])