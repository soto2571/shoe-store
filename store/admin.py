from django.contrib import admin
from .models import Product, ProductSize

class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 1  # Number of empty forms to display for adding sizes in the admin

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductSizeInline]  # Add sizes inline in the product admin page
    list_display = ['brand', 'name', 'total_stock', 'product_type']
    search_fields = ['brand', 'name', 'product_type']
    list_filter = ['product_type']
    ordering = ['name']

# Register ProductSize separately if needed
@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ['product', 'size', 'price', 'stock']
    search_fields = ['product__brand', 'product__name', 'size']
    list_filter = ['product']

    def save_model(self, request, obj, form, change):
        if obj.stock < 0:
            raise ValueError("Stock cannot be negative.")
        super().save_model(request, obj, form, change)