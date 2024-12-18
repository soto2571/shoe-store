from django.urls import path
from . import views
from django.contrib.auth.views import LoginView 

urlpatterns = [
    path('', views.index, name='index'),
    path('owner-login/', LoginView.as_view(template_name='store/owner_login.html'), name='login'),
    path('owner-dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('add-product/', views.add_product, name='add_product'),
    path('add-sizes/<int:product_id>/', views.add_sizes, name='add_sizes'),
    path('edit-product/<int:pk>/', views.edit_product, name='edit_product'),
    path('delete-product/<int:pk>/', views.delete_product, name='delete_product'),
    path('cart/', views.cart_view, name='cart_view'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:product_id>/', views.update_cart, name='update_cart'),
    path('clear-cart/', views.clear_cart, name='clear_cart'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('checkout/success/', views.checkout_success, name='checkout_success'),
    path('checkout/', views.create_checkout_session, name='checkout'),
    path('brand/<str:brand_name>/', views.product_by_brand, name='products_by_brand'),
    path('search/', views.search_products, name='search_products'),
    path('clothing/', views.clothing_view, name='clothing_page'),
    path('accessories/', views.accessories_view, name='accessories_page'),
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),
]
