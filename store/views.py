from django.shortcuts import render, redirect
from .models import Product, ProductSize, NewsletterSubscriber
from .forms import ProductForm, ProductSizeForm, NewsletterForm
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
from django.core.mail import send_mail, send_mass_mail
from decimal import Decimal, ROUND_HALF_UP
from django.core.mail import send_mail, EmailMessage
from django.http import JsonResponse
from math import ceil
from random import sample

stripe.api_key = settings.STRIPE_SECRET_KEY


def index(request):
    if 'cart' not in request.session:
        request.session['cart'] = {}  # Initialize an empty cart

    # Order the products to ensure consistent pagination
    products = Product.objects.all().order_by('id')  # Adjust the field to your preference
    newest_items = Product.objects.order_by('-created_at')[:3]
    


    brands = Product.objects.values('brand').exclude(brand__isnull=True).exclude(brand__exact='').distinct()

    for product in products:
        product.lowest_price = (
            product.sizes.order_by('price').first().price
            if product.sizes.exists()
            else product.price
        )

    shoes = Product.objects.filter(product_type='shoes')[:10]
    clothing = Product.objects.filter(product_type='clothing')
    accessories = Product.objects.filter(product_type='accessories')

    context = {
        'brands': brands,
        'shoes': shoes,
        'clothing': clothing,
        'accessories': accessories,
        'newest_items': newest_items,
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

def all_shoes(request):
    # Filter products by product type "shoes"
    shoe_products = Product.objects.filter(product_type='shoes')

    # Filter by brand
    brand = request.GET.get('brand')
    if brand and brand != 'all':
        shoe_products = shoe_products.filter(brand=brand)

    # Filter by size
    sizes = request.GET.getlist('size')
    if sizes:
        shoe_products = shoe_products.filter(sizes__size__in=sizes).distinct()

    # Sorting logic
    sort_option = request.GET.get('sort', 'best')  # Default to "best"

    if sort_option == 'low-to-high':
        shoe_products = shoe_products.annotate(min_price=Min('sizes__price')).order_by('min_price')
    elif sort_option == 'high-to-low':
        shoe_products = shoe_products.annotate(max_price=Max('sizes__price')).order_by('-max_price')

    # Filter by price
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price and max_price:
        shoe_products = shoe_products.filter(
            sizes__price__gte=min_price,
            sizes__price__lte=max_price
        ).distinct()

    # Populate filters for the sidebar
    brands = Product.objects.filter(product_type='shoes').values_list('brand', flat=True).distinct()
    sizes = ProductSize.objects.filter(product__product_type='shoes').values_list('size', flat=True).distinct()
    price_range = ProductSize.objects.filter(product__product_type='shoes').aggregate(
        min_price=Min('price'),
        max_price=Max('price')
    )

    context = {
        'products': shoe_products.distinct(),  # Ensure distinct products
        'brands': brands,
        'sizes': sizes,
        'price_range': price_range,
    }

    return render(request, 'store/all_shoes.html', context)


def subscribe_newsletter(request):
    if request.method == "POST":
        email = request.POST.get('email')
        if email:
            # Check if the email is already subscribed
            if not NewsletterSubscriber.objects.filter(email=email).exists():
                NewsletterSubscriber.objects.create(email=email)
                # Send a confirmation email
                send_mail(
                    subject="Thank you for subscribing!",
                    message="You are now subscribed to our newsletter. Stay tuned for updates!",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                )
                messages.success(request, "You have successfully subscribed to our newsletter!")
            else:
                messages.error(request, "This email is already subscribed!")
        else:
            messages.error(request, "Please provide a valid email!")
    
    # Redirect back to the same page
    return redirect(request.META.get('HTTP_REFERER', 'index'))


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

    try:
        # Fetch Stripe payment intents
        payment_intents = stripe.PaymentIntent.list(limit=100)
        filtered_payment_intents = [
            intent for intent in payment_intents['data']
            if intent['status'] == 'succeeded' and
               (start_time is None or datetime.fromtimestamp(intent['created']) >= start_time)
        ]

        total_sales = format_price(sum(
            Decimal(intent['amount_received']) / 100  # Stripe stores amounts in cents
            for intent in filtered_payment_intents
        ))

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
                'amount': format_price(Decimal(intent['amount_received']) / 100),
                'date': datetime.fromtimestamp(intent['created']).strftime('%B %d, %Y at %I:%M %p'),
            }
            for intent in filtered_payment_intents
        ]


        # Fetch invalid orders
        invalid_orders = fetch_invalid_orders()

    except Exception as e:
        print(f"Error fetching Stripe data: {e}")
        total_sales = format_price(0)
        total_orders = 0
        orders = []
        invalid_orders = []

    form = NewsletterForm()

    if request.method == 'POST':  # Corrected check for POST request
        form = NewsletterForm(request.POST, request.FILES)
        if form.is_valid():
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']
            recipient_count = int(request.POST.get('recipient_count', 0))
            subscribers = list(NewsletterSubscriber.objects.all())
            
            # If the recipient count exceeds the number of subscribers, send to all
            if recipient_count > len(subscribers):
                selected_subscribers = subscribers
            else:
                selected_subscribers = sample(subscribers, recipient_count)

            recipient_list = [subscriber.email for subscriber in selected_subscribers]

            # Get the uploaded image
            image = request.FILES.get('image')

            try:
                email = EmailMessage(
                    subject=subject,
                    body=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    bcc=recipient_list,
                )
                if image:
                    email.attach(image.name, image.read(), image.content_type)

                email.send()
                messages.success(request, "Newsletter sent successfully!")
            except Exception as e:
                messages.error(request, f"Error sending newsletter: {e}")
        else:
            messages.error(request, "Please correct the errors in the form.")

    return render(request, 'store/owner_dashboard.html', {
        'shoes': shoes,
        'clothing': clothing,
        'accessories': accessories,
        'total_sales': total_sales,
        'total_products': total_products,
        'total_orders': total_orders,
        'filter_option': filter_option,
        'orders': orders,
        'invalid_orders': invalid_orders,  # Pass invalid orders to the template
        'newsletter_form': form,
    })


def format_price(amount):
    """
    Helper function to format a price to 2 decimal places.
    """
    return Decimal(amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


from datetime import datetime
from decimal import Decimal

def fetch_invalid_orders():
    """
    Fetches invalid orders flagged in Stripe metadata.
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    invalid_orders = []

    try:
        # Fetch Stripe checkout sessions
        checkout_sessions = stripe.checkout.Session.list(limit=100)

        # Filter invalid sessions
        invalid_sessions = [
            session for session in checkout_sessions['data']
            if session['metadata'].get('status') == 'invalid'
        ]

        # Map invalid sessions to payment intents for consistent IDs
        for session in invalid_sessions:
            invalid_orders.append({
                'name': session.get('customer_details', {}).get('name', 'N/A'),
                'address': ", ".join(
                    filter(None, [
                        session.get('shipping_details', {}).get('address', {}).get('line1', ''),
                        session.get('shipping_details', {}).get('address', {}).get('line2', ''),
                        session.get('shipping_details', {}).get('address', {}).get('city', ''),
                        session.get('shipping_details', {}).get('address', {}).get('state', ''),
                        session.get('shipping_details', {}).get('address', {}).get('postal_code', ''),
                        session.get('shipping_details', {}).get('address', {}).get('country', ''),
                    ])
                ) or 'N/A',
                'email': session.get('customer_details', {}).get('email', 'N/A'),
                'amount': format_price(Decimal(session.get('amount_total', 0)) / 100),  # Stripe uses cents
                'date': datetime.fromtimestamp(session.get('created', 0)).strftime('%B %d, %Y at %I:%M %p'),
                'error_message': session['metadata'].get('error', 'Unknown Error'),
            })
    except Exception as e:
        print(f"Error fetching invalid Stripe orders: {e}")
        invalid_orders = []

    return invalid_orders

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

    expanded_cart_items = []  # For shipping calculation
    for key, item in cart.items():
        product = Product.objects.get(id=item['product_id'])
        
        # Precompute total price for each item
        total_price = item['price'] * item['quantity']

        cart_items.append({
            'product': product,
            'size': item['size'],
            'quantity': item['quantity'],
            'price': item['price'],
            'total_price': total_price,  # Pass the precomputed value
        })

        # Add items for box calculation
        expanded_cart_items.append({
            'quantity': item['quantity'],
            'weight': product.weight,
            'length': product.length,
            'width': product.width,
            'height': product.height,
        })

    # Calculate shipping cost and boxes
    shipping_info = calculate_shipping_boxes(expanded_cart_items)
    shipping_cost = shipping_info['total_cost']
    shipping_boxes = shipping_info['boxes']

    cart_total = sum(item['total_price'] for item in cart_items)
    total_with_shipping = cart_total + shipping_cost

    # Save shipping cost for Stripe checkout
    request.session['shipping_cost'] = float(shipping_cost)

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'shipping_cost': shipping_cost,
        'shipping_boxes': shipping_boxes,
        'total_with_shipping': total_with_shipping,
    })

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
    
from random import sample

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # Fetch products excluding the current product
    related_products = Product.objects.exclude(id=product_id)

    # Calculate the lowest price for each product
    for item in related_products:
        item.lowest_price = (
            item.sizes.order_by('price').first().price if item.sizes.exists() else item.price
        )

    # Separate products by category
    recommended_shoes = list(related_products.filter(product_type='shoes'))[:4]
    recommended_clothing = list(related_products.filter(product_type='clothing'))[:4]
    recommended_accessories = list(related_products.filter(product_type='accessories'))[:4]

    # Combine recommendations, randomly shuffle, and limit to 12 items
    combined_recommendations = recommended_shoes + recommended_clothing + recommended_accessories
    random_recommendations = sample(combined_recommendations, min(len(combined_recommendations), 12))

    # Debugging logs
    print("Recommended Products:", random_recommendations)

    context = {
        'product': product,
        'recommended_products': random_recommendations,
    }

    return render(request, 'store/product_detail.html', context)

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
        size = request.POST.get('size')  # Get the size of the product
        new_quantity = int(request.POST.get('quantity', 0))  # New quantity from the form
        
        cart = request.session.get('cart', {})
        key = f"{product_id}-{size}"

        # Check if the product exists in the cart
        if key in cart:
            try:
                # Get the product size object to check the stock
                product_size = ProductSize.objects.get(product_id=product_id, size=size)
                if new_quantity > product_size.stock:
                    messages.error(request, f"Only {product_size.stock} items are available in stock.")
                elif new_quantity > 0:
                    cart[key]['quantity'] = new_quantity
                    messages.success(request, "Cart updated successfully.")
                else:
                    del cart[key]
                    messages.success(request, "Item removed from cart.")
                request.session['cart'] = cart
            except ProductSize.DoesNotExist:
                messages.error(request, "The selected size does not exist.")
        else:
            messages.error(request, "Item not found in cart.")

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



### Checkout ###

def create_checkout_session(request):
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Your cart is empty!")
        return redirect('cart_view')

    line_items = []
    product_total = Decimal(0)  # Keep track of the product total for tax calculation
    cart_items = []

    for key, item in cart.items():
        product = Product.objects.get(id=item['product_id'])
        image_url = request.build_absolute_uri(product.image.url)
        product_price = Decimal(item['price'])
        product_total += product_price * item['quantity']

        cart_items.append({
            "quantity": item['quantity'],
            "weight": product.weight,
            "length": product.length,
            "width": product.width,
            "height": product.height,
        })

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
            payment_method_types=['card', 'link', 'klarna', 'afterpay_clearpay'],
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
    

SHIPPING_BOXES = [
    {"name": "Small Box", "max_weight": 6, "max_volume": 432, "price": 12.00},  # 6 lbs, 12x12x3
    {"name": "Medium Box", "max_weight": 12, "max_volume": 1728, "price": 20.00},  # 12 lbs, 12x12x12
    {"name": "Large Box", "max_weight": 20, "max_volume": 4096, "price": 30.00},  # 20 lbs, 16x16x16
    {"name": "Extra Large Box", "max_weight": 40, "max_volume": 8000, "price": 50.00},  # 40 lbs, 20x20x20
]


def calculate_shipping_boxes(cart_items):
    """
    Improved function to efficiently group items and pack them into the smallest number of boxes.
    """
    total_cost = 0
    boxes_used = []

    # Step 1: Expand cart items with weight, volume, and quantity
    items_to_pack = []
    for item in cart_items:
        volume = item['length'] * item['width'] * item['height']
        if volume <= 0:
            print(f"Warning: Item has invalid dimensions: {item}. Assigning default volume.")
            volume = 1  # Assign a small default volume

        items_to_pack.append({
            "weight": item['weight'],
            "volume": volume,
            "quantity": item['quantity'],
        })

    print(f"Items to Pack: {items_to_pack}")

    # Step 2: Pack items iteratively
    while items_to_pack:
        total_weight = sum(item['weight'] * item['quantity'] for item in items_to_pack)
        total_volume = sum(item['volume'] * item['quantity'] for item in items_to_pack)

        print(f"Total Weight: {total_weight}, Total Volume: {total_volume}")

        packed = False
        for box in SHIPPING_BOXES:
            if total_weight <= box['max_weight'] and total_volume <= box['max_volume']:
                # Items fit in the current box
                total_cost += box['price']
                boxes_used.append(box['name'])
                items_to_pack.clear()  # All items packed
                packed = True
                break

        if not packed:
            # If items don't fit in any single box, use the largest available box
            largest_box = SHIPPING_BOXES[-1]
            total_cost += largest_box['price']
            boxes_used.append(largest_box['name'])

            # Pack as many items as possible in the largest box
            remaining_items = []
            for item in items_to_pack:
                max_fit_quantity_by_weight = largest_box['max_weight'] // item['weight']
                max_fit_quantity_by_volume = largest_box['max_volume'] // item['volume']
                fit_quantity = min(item['quantity'], max_fit_quantity_by_weight, max_fit_quantity_by_volume)

                if fit_quantity > 0:
                    item['quantity'] -= fit_quantity

                if item['quantity'] > 0:
                    remaining_items.append(item)

            items_to_pack = remaining_items  # Restart with remaining items

    print(f"\nFinal Total Cost: {total_cost}")
    print(f"Boxes Used: {boxes_used}")
    return {"total_cost": total_cost, "boxes": boxes_used}

    
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
            handle_invalid_order(session, "Shipping data is incomplete.")
            return JsonResponse({'error': 'Shipping data is incomplete.'}, status=400)

        # Validate the shipping option
        try:
            validate_shipping_option(shipping_address, shipping_option_id)
        except ValueError as e:
            error_message = str(e)
            logger.error(f"Shipping validation error: {e}")

            # Handle invalid order
            handle_invalid_order(session, error_message)

            return JsonResponse({'error': str(e)}, status=400)

        logger.info("Checkout session completed successfully.")

    return JsonResponse({'status': 'success'})

def handle_invalid_order(session, error_message):
    """
    Handle invalid orders by notifying the customer about the refund and
    logging it in the dashboard for the owner.
    """
    # Notify the customer via email
    notify_customer_of_invalid_order(session, error_message)

    # Optionally, refund the order
    refund_invalid_order(session)

    logger.info(f"Invalid order handled: {session['id']}. Customer notified and refund issued.")


def notify_customer_of_invalid_order(session, error_message):
    """
    Notify the customer about the invalid order and provide resolution steps.
    """
    customer_email = session.get('customer_details', {}).get('email', None)
    if not customer_email:
        logger.warning("No email address found for the customer. Skipping notification.")
        return

    customer_name = session.get('customer_details', {}).get('name', 'Customer')
    order_id = session.get('payment_intent', 'Unknown')

    subject = "Issue with Your Order"
    message = (
        f"Dear {customer_name},\n\n"
        f"We noticed an issue with your order \n(ID: {order_id}):\n"
        f"{error_message}\n\n"
        f"Your order cannot proceed with the selected shipping option. "
        f"We will refund your purchase shortly, or you can contact us to resolve this.\n\n"
        f"Thank you,\nYour Store Team"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[customer_email],
    )

def refund_invalid_order(session):
    """
    Refund the order automatically if it is invalid.
    """
    payment_intent_id = session.get('payment_intent', None)
    if not payment_intent_id:
        logger.error("No payment intent ID found for the invalid order. Cannot process refund.")
        return

    try:
        stripe.Refund.create(payment_intent=payment_intent_id)
        logger.info(f"Refund issued for payment intent {payment_intent_id}.")
    except Exception as e:
        logger.error(f"Failed to refund payment intent {payment_intent_id}: {e}")


