from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from .models import Restaurant
from meals.models import Meal


# Inline admin for meals
class MealInline(admin.TabularInline):
    model = Meal
    extra = 0
    fields = ('name', 'price', 'is_available', 'created_at')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

# Register your models here.
@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'meal_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'location', 'description')
    ordering = ('-created_at',)
    list_per_page = 25
    inlines = [MealInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'location')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def meal_count(self, obj):
        """Display number of meals for this restaurant"""
        count = obj.meal_set.count()
        if count > 0:
            url = reverse('admin:meals_meal_changelist') + f'?restaurant__id__exact={obj.id}'
            return format_html('<a href="{}">{} meal(s)</a>', url, count)
        return '0'
    meal_count.short_description = 'Meals'
    
    actions = ['activate_restaurant', 'deactivate_restaurant']
    
    def activate_restaurant(self, request, queryset):
        """Bulk action to activate all meals in selected restaurants"""
        for restaurant in queryset:
            restaurant.meal_set.update(is_available=True)
        self.message_user(request, f'All meals in {queryset.count()} restaurants were activated.')
    activate_restaurant.short_description = "Activate all meals in selected restaurants"
    
    def deactivate_restaurant(self, request, queryset):
        """Bulk action to deactivate all meals in selected restaurants"""
        for restaurant in queryset:
            restaurant.meal_set.update(is_available=False)
        self.message_user(request, f'All meals in {queryset.count()} restaurants were deactivated.')
    deactivate_restaurant.short_description = "Deactivate all meals in selected restaurants"
