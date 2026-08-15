from django.db import models
from django.urls import reverse


class Restaurant(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default='')
    location = models.CharField(max_length=255, blank=True, default='')
    logo = models.ImageField(upload_to='restaurant_logos/', blank=True, null=True, help_text='Restaurant logo or image')
    
    # New fields for dynamic content
    hero_image = models.ImageField(upload_to='restaurant_heroes/', blank=True, null=True, help_text='Hero image for meal list page')
    hero_title = models.CharField(max_length=200, blank=True, default='Delicious Meals', help_text='Hero title for meal list page')
    hero_description = models.TextField(blank=True, default='Discover amazing food from top restaurants in your area. Fresh ingredients, great taste, and fast delivery.', help_text='Hero description for meal list page')
    
    # Restaurant settings
    delivery_time = models.CharField(max_length=50, blank=True, default='30-45 minutes', help_text='Estimated delivery time')
    phone_number = models.CharField(max_length=20, blank=True, default='', help_text='Restaurant phone number')
    email = models.EmailField(blank=True, default='', help_text='Restaurant email')
    opening_hours = models.CharField(max_length=100, blank=True, default='Mon-Sun: 9:00 AM - 10:00 PM', help_text='Restaurant opening hours')
    
    # Admin-managed overall rating (0.0 – 5.0)
    overall_rating = models.FloatField(default=0.0, help_text='Overall star rating (0.0 to 5.0)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('restaurants:restaurant_detail', kwargs={'restaurant_id': self.pk})
