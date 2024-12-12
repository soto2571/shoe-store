from django.db import models
import os
from django.dispatch import receiver
from django.db.models.signals import post_delete
from django.core.exceptions import ValidationError

class Product(models.Model):
    brand = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='products/')
    product_type = models.CharField(max_length=100, choices=[
        ('shoes', 'Shoes'),
        ('clothing', 'Clothing'),
        ('accessories', 'Accessories'),
    ])

    @property
    def total_stock(self):
        return sum(size.stock for size in self.sizes.all())
    
    def lowest_price(self):
        sizes = self.sizes.all()
        if sizes:
            return min(size.price for size in sizes)
        return None

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        if self.image:
            if os.path.isfile(self.image.path):
                os.remove(self.image.path)
        super().delete(*args, **kwargs)

class ProductSize(models.Model):
    product = models.ForeignKey(Product, related_name='sizes', on_delete=models.CASCADE)
    size = models.CharField(max_length=10)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)

    def clean(self):
        if self.stock < 0:
            raise ValidationError("Stock cannot be negative.")

    def __str__(self):
        return f"{self.product.name} - {self.size}"

@receiver(post_delete, sender=Product)
def delete_image_on_product_delete(sender, instance, **kwargs):
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)