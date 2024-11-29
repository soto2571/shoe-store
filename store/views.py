from django.shortcuts import render, redirect
from .models import Product
from .forms import ProductForm

def index(request):
    products = Product.objects.all()
    return render(request, 'store/index.html', {'products': products})

def owner_dashboard(request):
    products = Product.objects.all()
    return render(request, 'store/owner_dashboard.html', {'products': products})

def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('owner_dashboard')
    else:
        form = ProductForm()
    return render(request, 'store/add_product.html', {'form': form})

def edit_product(request, pk):
    product = Product.objects.get(pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect('owner_dashboard')
        else:
            form = ProductForm(instance=product)
        return render(request, 'store/edit_product.html', {'form': form})
    
def delete_product(request, pk):
    product = Product.objects.get(pk=pk)
    product.delete()
    return redirect('owner_dashboard')
