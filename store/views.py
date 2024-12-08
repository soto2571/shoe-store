from django.shortcuts import render, redirect
from .models import Product, ProductSize
from .forms import ProductForm, ProductSizeForm
from django.shortcuts import get_object_or_404
from django.forms import modelformset_factory
from django.contrib import messages
import stripe
from django.conf import settings
from django.db.models import Q
from django.db.models.functions import Lower
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator

stripe.api_key = settings.STRIPE_SECRET_KEY


def index(request):
    if 'cart' not in request.session:
        request.session['cart'] = {}  # Initialize an empty cart

    # Order the products to ensure consistent pagination
    products = Product.objects.all().order_by('id')  # Adjust the field to your preference

    brands = Product.objects.values('brand').exclude(brand__isnull=True).exclude(brand__exact='').distinct()

    for product in products:
        product.lowest_price = (
            product.sizes.order_by('price').first().price
            if product.sizes.exists()
            else product.price
        )

    # Set up pagination
    paginator = Paginator(products, 5)  # Show 5 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'brands': brands,
    }
    return render(request, 'store/index.html', context)

### Customer ###
def product_by_brand(request, brand_name):
    products = Product.objects.filter(brand__iexact=brand_name)  # Case-insensitive filter
    context = {
        'products': products,
        'brand_name': brand_name.capitalize(),  # Capitalize brand name for display
    }
    return render(request, 'store/products_by_brand.html', context)


def search_products(request):
    query = request.GET.get('q', '')
    query = request.GET.get('q', '').strip()
    print(f"Search Query: {query}")  # Debug query

    if query:
        products = Product.objects.annotate(
            lower_name=Lower('name'),
            lower_brand=Lower('brand')
        ).filter(
            Q(lower_name__icontains=query) | Q(lower_brand__icontains=query)
        )
        print(f"Products Found: {products}")  # Debug results
    else:
        products = Product.objects.none()

    context = {
        'products': products,
        'query': query,
    }
    return render(request, 'store/search_results.html', context)

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)  # Fetch the product by ID
    return render(request, 'store/product_detail.html', {'product': product})



### Owner ###
def owner_required(user):
    return user.groups.filter(name='Owner').exists()

@login_required
@user_passes_test(owner_required, login_url='index')
def owner_dashboard(request):
    products = Product.objects.all()
    return render(request, 'store/owner_dashboard.html', {'products': products})

def add_product(request):
    ProductSizeFormSet = modelformset_factory(
        ProductSize,
        form=ProductSizeForm,
        extra=3,  # Allows 3 empty forms for new sizes
        can_delete=True,
    )

    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES)
        size_formset = ProductSizeFormSet(request.POST)

        if product_form.is_valid() and size_formset.is_valid():
            product = product_form.save()

            # Save each size with the product reference
            sizes = size_formset.save(commit=False)
            for size in sizes:
                size.product = product
                size.save()

            # Handle deleted sizes
            for deleted in size_formset.deleted_objects:
                deleted.delete()

            return redirect('owner_dashboard')
    else:
        product_form = ProductForm()
        size_formset = ProductSizeFormSet(queryset=ProductSize.objects.none())  # Start with no sizes

    return render(request, 'store/add_product.html', {
        'product_form': product_form,
        'size_formset': size_formset,
    })


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
        extra=1,  # Allow one extra blank form for adding new sizes
        can_delete=True,  # Allow sizes to be deleted
    )

    if request.method == 'POST':
        product_form = ProductForm(request.POST, request.FILES, instance=product)
        size_formset = ProductSizeFormSet(request.POST, queryset=product.sizes.all())

        if product_form.is_valid() and size_formset.is_valid():
            product = product_form.save()
           
            # Update sizes and stock
            instances = size_formset.save(commit=False)

            for instance in instances:
                instance.product = product  # Associate size with the product
                instance.save()

            # Handle deleted sizes
            for deleted in size_formset.deleted_objects:
                deleted.delete()

            return redirect('owner_dashboard')
        
        # Debugging for errors
        else:
            print(f"Product Form Errors: {product_form.errors}")
            print(f"Size Formset Errors: {size_formset.errors}")
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
            product = product_size.product
            cart[key] = {
                'product_id': product_id,
                'size': size,
                'price': float(product_size.price),
                'quantity': quantity,
                'image_url': product_size.product.image.url, 
            }

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


### Checkout ###

def create_checkout_session(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty!")
        return redirect('cart_view')

    line_items = []
    for key, item in cart.items():
        # Get the product
        product = Product.objects.get(id=item['product_id'])
        
        # Generate the absolute image URL
        image_url = request.build_absolute_uri(product.image.url)
        print(f"Image URL: {image_url}")

        line_items.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f"Product: {product.name} | Size: {item['size']}",
                    'images': [image_url],  # Add the image URL here
                },
                'unit_amount': int(item['price'] * 100),  # Stripe requires the price in cents
            },
            'quantity': item['quantity'],
        })

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=[
                'card',
                'klarna',
                'affirm',
                'afterpay_clearpay',
                'link',
                ],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri('/checkout/success/') + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri('/cart/'),
            shipping_address_collection={
                'allowed_countries': ['US', 'PR'],
            }
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        print(f"Error in create_checkout_session: {e}")
        messages.error(request, "Unable to create checkout session. Try again later.")
        return redirect('cart_view')
        

def checkout_success(request):
    # Retrieve the session ID from the request
    session_id = request.GET.get('session_id')
    if not session_id:
        print("Missing session_id in request.GET")
        messages.error(request, "Missing session ID.")
        return redirect('cart_view')

    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        print(f"Retrieved checkout session: {checkout_session}")
        payment_intent_id = checkout_session.payment_intent
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        confirmation_number = payment_intent.id
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e.user_message}")
        messages.error(request, "Failed to retrieve payment details.")
        return redirect('cart_view')

    # Process the purchased items
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty. Nothing to process.")
        return redirect('cart_view')

    purchased_items = []  # List to hold purchased item details

    for key, item in cart.items():
        try:
            product_size = ProductSize.objects.get(product_id=item['product_id'], size=item['size'])
        except ProductSize.DoesNotExist:
            messages.error(request, "An item in your cart could not be found.")
            return redirect('cart_view')

        if product_size.stock < item['quantity']:
            messages.error(request, f"Insufficient stock for {product_size.product.name} (Size: {product_size.size}).")
            return redirect('cart_view')

        product_size.stock -= item['quantity']
        product_size.save()

        # Add item details to purchased_items
        purchased_items.append({
            'name': product_size.product.name,
            'size': product_size.size,
            'price': item['price'],
            'quantity': item['quantity'],
            'image_url': product_size.product.image.url,  # Add image URL
        })

    # Clear the cart
    request.session['cart'] = {}

    # Pass purchased items and confirmation number to the template
    context = {
        'purchased_items': purchased_items,
        'confirmation_number': confirmation_number,
    }

    return render(request, 'store/checkout_success.html', context)