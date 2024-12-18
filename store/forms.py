from django import forms
from .models import Product, ProductSize

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['brand', 'name', 'image', 'product_type', 'weight', 'length', 'width', 'height']
        widgets = {
            'weight': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': 'Weight in lbs'}),
            'length': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': 'Length in inches'}),
            'width': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': 'Width in inches'}),
            'height': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': 'Height in inches'}),
        }

class ProductSizeForm(forms.ModelForm):
    class Meta:
        model = ProductSize
        fields = ['size', 'price', 'stock']