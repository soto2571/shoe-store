from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('owner-dashboard/', views.owner_dashboard, name='owner_dashboard'),
    path('add-product/', views.add_product, name='add_product'),
    path('edit-product/<int:pk>/', views.edit_product, name='edit_product'),
    path('delete-product/<int:pk>/', views.delete_product, name='delete_product'),
]