from django import forms
from .models import Meal
from restaurants.models import Restaurant


class MealForm(forms.ModelForm):
    """Form for creating and editing meals"""
    
    class Meta:
        model = Meal
        fields = ['name', 'description', 'price', 'image', 'is_available', 'prep_time_min', 'prep_time_max']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter meal name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter meal description'
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'is_available': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'prep_time_min': forms.NumberInput(attrs={
                'class': 'form-control prep-time-input',
                'min': '1',
                'max': '60',
                'placeholder': '15',
                'id': 'prep_time_min'
            }),
            'prep_time_max': forms.NumberInput(attrs={
                'class': 'form-control prep-time-input',
                'min': '1',
                'max': '60',
                'placeholder': '20',
                'id': 'prep_time_max'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.restaurant = kwargs.pop('restaurant', None)
        super().__init__(*args, **kwargs)
        
        # Make image field optional
        self.fields['image'].required = False
        
        # Add help text
        self.fields['price'].help_text = 'Enter price in dollars (e.g., 12.99)'
        self.fields['image'].help_text = 'Upload an image for your meal (optional)'
        self.fields['is_available'].help_text = 'Check if this meal is currently available for ordering'
        self.fields['prep_time_min'].help_text = 'Minimum preparation time in minutes (1-60)'
        self.fields['prep_time_max'].help_text = 'Maximum preparation time in minutes (1-60)'
        
        # Set labels
        self.fields['prep_time_min'].label = 'Min Prep Time (min)'
        self.fields['prep_time_max'].label = 'Max Prep Time (min)'
    
    def clean(self):
        cleaned_data = super().clean()
        prep_time_min = cleaned_data.get('prep_time_min')
        prep_time_max = cleaned_data.get('prep_time_max')
        
        if prep_time_min and prep_time_max:
            if prep_time_max - prep_time_min > 15:
                raise forms.ValidationError("Preparation time range cannot exceed 15 minutes")
            if prep_time_min >= prep_time_max:
                raise forms.ValidationError("Minimum preparation time must be less than maximum preparation time")
        
        return cleaned_data


class MealSearchForm(forms.Form):
    """Form for searching and filtering meals"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search meals...'
        })
    )
    is_available = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Available'), ('false', 'Unavailable')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )