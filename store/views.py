from django.shortcuts import render, redirect
from .models import Product, ProductSize
from .forms import ProductForm, ProductSizeForm
from django.shortcuts import get_object_or_404
from django.forms import modelformset_factory
from django.contrib import messages
import stripe
from django.conf import settings
from django.db.models import Q, Min, Max, Count
from django.db.models.functions import Lower
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from decimal import Decimal
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

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

    shoes = Product.objects.filter(product_type='shoes')
    clothing = Product.objects.filter(product_type='clothing')
    accessories = Product.objects.filter(product_type='accessories')

    context = {
        'page_obj': page_obj,
        'brands': brands,
        'shoes': shoes,
        'clothing': clothing,
        'accessories': accessories,
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

def clothing_view(request):
    clothing_products = Product.objects.filter(product_type='clothing')

    # Filter by brand
    brand = request.GET.get('brand')
    if brand and brand != 'all':
        clothing_products = clothing_products.filter(brand=brand)

    # Filter by size
    sizes = request.GET.getlist('size')
    if sizes:
        clothing_products = clothing_products.filter(sizes__size__in=sizes).distinct()

    # Sorting logic
    sort_option = request.GET.get('sort', 'best')  # Default to "best"

    if sort_option == 'low-to-high':
        clothing_products = clothing_products.annotate(min_price=Min('sizes__price')).order_by('min_price')
    elif sort_option == 'high-to-low':
        clothing_products = clothing_products.annotate(max_price=Max('sizes__price')).order_by('-max_price')

    # Filter by price
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and max_price:
        clothing_products = clothing_products.filter(
            sizes__price__gte=min_price,
            sizes__price__lte=max_price
        ).distinct()

    # Populate filters for the sidebar
    brands = Product.objects.filter(product_type='clothing').values_list('brand', flat=True).distinct()
    sizes = ProductSize.objects.filter(product__product_type='clothing').values_list('size', flat=True).distinct()
    price_range = ProductSize.objects.filter(product__product_type='clothing').aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )

    context = {
        'products': clothing_products.distinct(),  # Ensure distinct products
        'brands': brands,
        'sizes': sizes,
        'price_range': price_range,
    }

    return render(request, 'store/clothing.html', context)

def accessories_view(request):
    accessories_products = Product.objects.filter(product_type='accessories')
    return render(request, 'store/accessories.html', {'products': accessories_products})


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

def accessories_view(request):
    accessories_products = Product.objects.filter(product_type='accessories')

    # Filter by brand
    brand = request.GET.get('brand')
    if brand and brand != 'all':
        accessories_products = accessories_products.filter(brand=brand)

    # Filter by size
    sizes = request.GET.getlist('size')
    if sizes:
        accessories_products = accessories_products.filter(sizes__size__in=sizes).distinct()

    # Sorting logic
    sort_option = request.GET.get('sort', 'best')  # Default to "best"

    if sort_option == 'low-to-high':
        accessories_products = accessories_products.annotate(min_price=Min('sizes__price')).order_by('min_price')
    elif sort_option == 'high-to-low':
        accessories_products = accessories_products.annotate(max_price=Max('sizes__price')).order_by('-max_price')
    
    # Filter by price
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and max_price:
        accessories_products = accessories_products.filter(
            sizes__price__gte=min_price,
            sizes__price__lte=max_price
        ).distinct()

    # Populate filters for the sidebar
    brands = Product.objects.filter(product_type='accessories').values_list('brand', flat=True).distinct()
    sizes = ProductSize.objects.filter(product__product_type='accessories').values_list('size', flat=True).distinct()
    price_range = ProductSize.objects.filter(product__product_type='accessories').aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )

    context = {
        'products': accessories_products.distinct(),  # Ensure distinct products
        'brands': brands,
        'sizes': sizes,
        'price_range': price_range,
    }

    return render(request, 'store/accessories.html', context)


### Owner ###
def owner_required(user):
    return user.groups.filter(name='Owner').exists()


@login_required
@user_passes_test(owner_required, login_url='index')
def owner_dashboard(request):
    # Query products by type
    shoes = Product.objects.filter(product_type='shoes')
    clothing = Product.objects.filter(product_type='clothing')
    accessories = Product.objects.filter(product_type='accessories')

    # Total products count
    total_products = Product.objects.count()

    # Get the filter option from the request
    filter_option = request.GET.get('filter', 'current_day')  # Default to current day

    # Define time ranges
    now = datetime.now()
    if filter_option == 'current_day':
        start_time = now - timedelta(days=1)
    elif filter_option == 'last_7_days':
        start_time = now - timedelta(days=7)
    elif filter_option == 'last_month':
        start_time = now - timedelta(days=30)
    else:
        start_time = None  # Default to show all records if no filter matches

    # Fetch total sales from Stripe
    try:
        payment_intents = stripe.PaymentIntent.list(limit=100)  # Adjust limit if needed
        filtered_payment_intents = [
            intent for intent in payment_intents['data']
            if intent['status'] == 'succeeded' and
               (start_time is None or datetime.fromtimestamp(intent['created']) >= start_time)
        ]

        total_sales = sum(
            Decimal(intent['amount_received'] / 100)  # Stripe stores amounts in cents
            for intent in filtered_payment_intents
        )

        total_orders = len(filtered_payment_intents)

        # Extract customer details for the dropdown
        orders = [
    {
        'id': intent['id'],
        'name': intent['shipping']['name'] if intent.get('shipping') else 'N/A',
        'address': ", ".join(
            filter(None, [
                intent['shipping']['address']['line1'] if intent.get('shipping') else '',
                intent['shipping']['address']['line2'] if intent.get('shipping') else '',
                intent['shipping']['address']['city'] if intent.get('shipping') else '',
                intent['shipping']['address']['state'] if intent.get('shipping') else '',
                intent['shipping']['address']['postal_code'] if intent.get('shipping') else '',
                intent['shipping']['address']['country'] if intent.get('shipping') else '',
            ])
        ) if intent.get('shipping') else 'N/A',
        'email': intent['receipt_email'] or 'N/A',
        'amount': Decimal(intent['amount_received'] / 100),
'date': datetime.fromtimestamp(intent['created']).strftime('%B %d, %Y at %I:%M %p'),    }
    for intent in filtered_payment_intents
]
    except Exception as e:
        print(f"Error fetching Stripe data: {e}")
        total_sales = 0
        total_orders = 0
        orders = []

    return render(request, 'store/owner_dashboard.html', {
        'shoes': shoes,
        'clothing': clothing,
        'accessories': accessories,
        'total_sales': total_sales,
        'total_products': total_products,
        'total_orders': total_orders,
        'filter_option': filter_option,
        'orders': orders,
    })

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
    product_total = Decimal(0)  # Keep track of the product total for tax calculation

    for key, item in cart.items():
        product = Product.objects.get(id=item['product_id'])
        image_url = request.build_absolute_uri(product.image.url)
        product_price = Decimal(item['price'])
        product_total += product_price * item['quantity']

        # Ensure product price is valid
        if int(product_price * 100) < 1:
            product_price = Decimal("0.01")  # Minimum 1 cent

        line_items.append({
            'price_data': {
                'currency': 'usd',
                'product_data': {
                    'name': f"{product.name} | Size: {item['size']}",
                    'images': [image_url],
                },
                'unit_amount': int(product_price * 100),
            },
            'quantity': item['quantity'],
        })

    # Calculate tax (11.5%)
    tax_amount = product_total * Decimal(0.115)
    if int(tax_amount * 100) < 1:
        tax_amount = Decimal("0.01")  # Minimum 1 cent

    line_items.append({
        'price_data': {
            'currency': 'usd',
            'product_data': {
                'name': 'Estimated Taxes',
            },
            'unit_amount': int(tax_amount * 100),
        },
        'quantity': 1,
    })

    shipping_options = [
    {
        'shipping_rate_data': {
            'type': 'fixed_amount',
            'fixed_amount': {'amount': 1200, 'currency': 'usd'},  # Puerto Rico: $12
            'display_name': 'Puerto Rico Standard (Only for Puerto Rico addresses)',
            'delivery_estimate': {
                'minimum': {'unit': 'business_day', 'value': 3},
                'maximum': {'unit': 'business_day', 'value': 5},
            },
            'metadata': {'region': 'PR'},  # Metadata for backend validation
        },
    },
    {
        'shipping_rate_data': {
            'type': 'fixed_amount',
            'fixed_amount': {'amount': 2000, 'currency': 'usd'},  # US: $20
            'display_name': 'US Standard (Only for US addresses)',
            'delivery_estimate': {
                'minimum': {'unit': 'business_day', 'value': 5},
                'maximum': {'unit': 'business_day', 'value': 7},
            },
            'metadata': {'region': 'US'},  # Metadata for backend validation
        },
    },
]

    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card', 'link', 'klarna', 'affirm', 'afterpay_clearpay'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri('/checkout/success/') + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.build_absolute_uri('/cart/'),
            shipping_address_collection={'allowed_countries': ['US', 'PR']},
            shipping_options=shipping_options,  # Add shipping options to the session
            metadata={
        'shipping_instructions': 'Puerto Rico Standard is only for Puerto Rico addresses. US Standard is only for US addresses.'
    },
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        print(f"Error in create_checkout_session: {e}")
        messages.error(request, "Unable to create checkout session. Try again later.")
        return redirect('cart_view')
    
def validate_shipping_option(shipping_address, shipping_option_id):
    if not shipping_option_id:
        raise ValueError("Shipping option ID is missing.")

    try:
        shipping_rate = stripe.ShippingRate.retrieve(shipping_option_id)

        # Extract region and validate
        region = shipping_rate.metadata.get('region', '').strip().upper()
        customer_country = shipping_address.get('country', '').strip().upper()

        if not region or not customer_country:
            logger.error(f"Incomplete shipping data - Region: {region}, Country: {customer_country}")
            raise ValueError("Shipping data is incomplete.")

        if region == 'PR' and customer_country != 'PR':
            raise ValueError("Puerto Rico Standard shipping is only for Puerto Rico addresses.")
        elif region == 'US' and customer_country != 'US':
            raise ValueError("US Standard shipping is only for US addresses.")

    except stripe.error.InvalidRequestError as e:
        logger.error(f"Stripe API error while retrieving shipping rate: {e.user_message}")
        raise ValueError(f"Invalid shipping rate: {e.user_message}")

    logger.info("Shipping validation passed.")
    return True

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


### Webhook ###
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.headers.get('Stripe-Signature', '')

    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        logger.error("Invalid payload.")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature.")
        return JsonResponse({'error': 'Invalid signature'}, status=400)

    logger.info(f"Webhook event received: {event['type']}")

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        # Extract shipping details and shipping option ID
        shipping_address = session.get('shipping_details', {}).get('address', {})
        shipping_option_id = session.get('shipping_cost', {}).get('shipping_rate')

        # Debugging: log extracted data
        logger.info(f"Extracted Shipping Address: {shipping_address}")
        logger.info(f"Extracted Shipping Option ID: {shipping_option_id}")

        # Ensure both are available
        if not shipping_address or not shipping_option_id:
            logger.error("Incomplete shipping data. Address or option ID is missing.")
            return JsonResponse({'error': 'Shipping data is incomplete.'}, status=400)

        # Validate the shipping option
        try:
            validate_shipping_option(shipping_address, shipping_option_id)
        except ValueError as e:
            logger.error(f"Shipping validation error: {e}")
            return JsonResponse({'error': str(e)}, status=400)

        logger.info("Checkout session completed successfully.")

    return JsonResponse({'status': 'success'})