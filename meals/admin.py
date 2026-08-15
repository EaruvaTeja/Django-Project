from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Meal

# Register your models here.
@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ('name', 'restaurant', 'price', 'is_available', 'created_at')
    list_filter = ('is_available', 'restaurant', 'created_at')
    search_fields = ('name', 'restaurant__name', 'description')
    ordering = ('-created_at',)
    list_per_page = 25
    
    fieldsets = (
        ('Meal Information', {
            'fields': ('name', 'description', 'price', 'image', 'is_available')
        }),
        ('Restaurant Information', {
            'fields': ('restaurant',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    actions = ['make_available', 'make_unavailable', 'duplicate_meal']
    
    def make_available(self, request, queryset):
        """Bulk action to make meals available"""
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} meals were successfully made available.')
    make_available.short_description = "Make selected meals available"
    
    def make_unavailable(self, request, queryset):
        """Bulk action to make meals unavailable"""
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} meals were successfully made unavailable.')
    make_unavailable.short_description = "Make selected meals unavailable"
    
    def duplicate_meal(self, request, queryset):
        """Bulk action to duplicate meals"""
        for meal in queryset:
            meal.pk = None
            meal.name = f"{meal.name} (Copy)"
            meal.save()
        self.message_user(request, f'{queryset.count()} meals were successfully duplicated.')
    duplicate_meal.short_description = "Duplicate selected meals"
