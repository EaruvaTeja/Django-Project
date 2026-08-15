from django import forms
from .models import Restaurant


class RestaurantForm(forms.ModelForm):
    """Form for editing restaurant details"""
    
    class Meta:
        model = Restaurant
        fields = ['name', 'description', 'location', 'logo', 'hero_image', 'hero_title', 'hero_description', 
                 'delivery_time', 'phone_number', 'email', 'opening_hours']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter restaurant name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter restaurant description'
            }),
            'hero_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter hero title (e.g., Delicious Meals)'
            }),
            'hero_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter hero description'
            }),
            'delivery_time': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 30-45 minutes'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            }),
            'opening_hours': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Mon-Sun: 9:00 AM - 10:00 PM'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter restaurant address'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help text
        self.fields['name'].help_text = 'The name of your restaurant'
        self.fields['description'].help_text = 'Describe your restaurant, cuisine type, and specialties'
        self.fields['location'].help_text = 'Full address where your restaurant is located'
        self.fields['logo'].help_text = 'Upload your restaurant logo (optional)'