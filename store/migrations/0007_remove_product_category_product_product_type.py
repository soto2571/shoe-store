# Generated by Django 5.1.3 on 2024-12-09 23:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0006_remove_product_price'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='product',
            name='category',
        ),
        migrations.AddField(
            model_name='product',
            name='product_type',
            field=models.CharField(choices=[('shoes', 'Shoes'), ('clothing', 'Clothing'), ('accessories', 'Accessories')], default='shoes', max_length=100),
            preserve_default=False,
        ),
    ]
