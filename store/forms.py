from django import forms
from .models import Product, ProductSize

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['brand', 'name', 'price', 'image', 'category']

class ProductSizeForm(forms.ModelForm):
    class Meta:
        model = ProductSize
        fields = ['size', 'price', 'stock']