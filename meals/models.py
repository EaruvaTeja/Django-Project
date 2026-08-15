from django.db import models
from django.urls import reverse


class Meal(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='meals/', blank=True, null=True)
    is_available = models.BooleanField(default=True)
    restaurant = models.ForeignKey('restaurants.Restaurant', on_delete=models.CASCADE)
    
    # Preparation time fields
    prep_time_min = models.PositiveIntegerField(default=15, help_text="Minimum preparation time in minutes")
    prep_time_max = models.PositiveIntegerField(default=20, help_text="Maximum preparation time in minutes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.prep_time_max - self.prep_time_min > 15:
            raise ValidationError("Preparation time range cannot exceed 15 minutes")
        if self.prep_time_min >= self.prep_time_max:
            raise ValidationError("Minimum preparation time must be less than maximum preparation time")
    
    @property
    def prep_time_display(self):
        """Return formatted preparation time range"""
        if self.prep_time_min == self.prep_time_max:
            return f"{self.prep_time_min} min"
        return f"{self.prep_time_min}-{self.prep_time_max} min"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('meals:meal_detail', kwargs={'meal_id': self.pk})
