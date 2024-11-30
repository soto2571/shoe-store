from django.shortcuts import render, redirect
from .models import Product, ProductSize
from .forms import ProductForm, ProductSizeForm
from django.shortcuts import get_object_or_404
from django.forms import modelformset_factory
from django.contrib import messages

def index(request):
    if 'cart' not in request.session:
        request.session['cart'] = {}  # Initialize an empty cart
    products = Product.objects.all()

    for product in products:
        product.lowest_price = (
            product.sizes.order_by('price').first().price
            if product.sizes.exists()
            else product.price
        )
    return render(request, 'store/index.html', {'products': products})


### Owner ###

def owner_dashboard(request):
    products = Product.objects.all()
    return render(request, 'store/owner_dashboard.html', {'products': products})

def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            return redirect('add_sizes', product_id=product.id)
    else:
        form = ProductForm()
    return render(request, 'store/add_product.html', {'form': form})

def add_sizes(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductSizeForm(request.POST)
        if form.is_valid():
            size_instance = form.save(commit=False)  # Create the size object but don't save yet
            size_instance.product = product  # Associate the size with the correct product
            size_instance.save()  # Save the size object
            return redirect('add_sizes', product_id=product.id)
    else:
        form = ProductSizeForm()
    
    sizes = product.sizes.all()  # Fetch all sizes for this product
    return render(request, 'store/add_sizes.html', {'form': form, 'product': product, 'sizes': sizes})


def edit_product(request, pk):
    product = get_object_or_404(Product, id=pk)
    ProductSizeFormSet = modelformset_factory(
        ProductSize,
        form=ProductSizeForm,
        fields=['size', 'price', 'stock'],
        extra=0,
        can_delete=True,
    )

    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES, instance=product)
        size_formset = ProductSizeFormSet(request.POST, queryset=product.sizes.all())

        if product_form.is_valid() and size_formset.is_valid():
            product = product_form.save()
           
            # Update sizes and stock
            instances = size_formset.save(commit=False)

            for instance in instances:
                instance.product = product
                instance.save()


            # Handle deleted sizes
            for deleted in size_formset.deleted_objects:
                deleted.delete()
            return redirect('owner_dashboard')
        
    else:
        product_form = ProductForm(instance=product)
        size_formset = ProductSizeFormSet(queryset=product.sizes.all())

    return render(request, 'store/edit_product.html', {
        'product_form': product_form,
        'size_formset': size_formset,
        'product': product,
    })
    
def delete_product(request, pk):
    product = Product.objects.get(pk=pk)
    product.delete()
    return redirect('owner_dashboard')

### Cart ###

def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []

    for key, item in cart.items():
        product = Product.objects.get(id=item['product_id'])
        cart_items.append({
            'product': product,
            'size': item['size'],
            'quantity': item['quantity'],
            'total_price': item['price'] * item['quantity']
        })

    cart_total = sum(item['total_price'] for item in cart_items)

    return render(request, 'store/cart.html', {'cart_items': cart_items, 'cart_total': cart_total})

def add_to_cart(request, product_id):
    size = request.POST.get('size')  # Get the selected size
    quantity = int(request.POST.get('quantity', 1))  # Get the quantity, default to 1 if not provided

    # Debugging the submitted data
    print(f"Product ID: {product_id}, Size: {size}, Quantity: {quantity}")

    # Validate size and ensure it matches an existing ProductSize
    if not size:
        messages.error(request, "Please select a size before adding to the cart.")
        return redirect('product_detail', product_id=product_id)

    try:
        product_size = get_object_or_404(ProductSize, product_id=product_id, size=size)

        if product_size.stock < quantity:
            messages.error(request, "This size is out of stock!")
            return redirect('product_detail', product_id=product_id)

        # Update the cart session
        cart = request.session.get('cart', {})
        key = f"{product_id}-{size}"

        if key in cart:
            cart[key]['quantity'] += quantity
        else:
            cart[key] = {
                'product_id': product_id,
                'size': size,
                'price': float(product_size.price),
                'quantity': quantity,
            }

        # Reduce stock
        product_size.stock -= quantity
        product_size.save()

        request.session['cart'] = cart
        messages.success(request, "Product added to cart!")
        return redirect('cart_view')

    except Exception as e:
        print(f"Error in add_to_cart: {e}")
        messages.error(request, "Something went wrong. Please try again.")
        return redirect('product_detail', product_id=product_id)

def remove_from_cart(request, product_id):
    size = request.GET.get('size')  # Ensure size is passed to identify the product size
    cart = request.session.get('cart', {})
    key = f"{product_id}-{size}"

    if key in cart:
        # Restore the stock for the removed item
        product_size = get_object_or_404(ProductSize, product_id=product_id, size=size)
        product_size.stock += cart[key]['quantity']
        product_size.save()

        # Remove the item from the cart
        del cart[key]
        request.session['cart'] = cart

    return redirect('cart_view')

def update_cart(request, product_id):
    if request.method == 'POST':
        new_quantity = int(request.POST.get('quantity', 0))
        cart = request.session.get('cart', {})
        if str(product_id) in cart:
            if new_quantity > 0:
                cart[str(product_id)] = new_quantity
            else:
                del cart[str(product_id)]
            request.session['cart'] = cart
        
        return redirect('cart_view')
    
def clean_cart(cart):
    valid_ids = set(Product.objects.values_list('id', flat=True))
    print("DEBUG - Valid product IDs:", valid_ids)  # Debugging
    cleaned_cart = {key: value for key, value in cart.items() if int(key) in valid_ids}
    print("DEBUG - Cleaned cart:", cleaned_cart)  # Debugging
    return cleaned_cart

def clear_cart(request):
    request.session.flush()
    return redirect('index')

### Product Detail ###

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'store/product_detail.html', {'product': product})
