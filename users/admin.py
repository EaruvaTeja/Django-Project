"""
Users App Admin Configuration

Registers the Address model so we can inspect addresses from /admin/.
"""

from django.contrib import admin

from .models import Address


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'address_type',
        'label',
        'full_name',
        'city',
        'pincode',
        'is_default',
        'updated_at',
    ]
    list_filter = ['address_type', 'is_default', 'city', 'state']
    search_fields = ['user__username', 'user__email', 'full_name', 'pincode']
    raw_id_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-is_default', '-updated_at']
    list_per_page = 50