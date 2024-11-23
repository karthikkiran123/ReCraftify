from django.shortcuts import render, redirect
from vendor.models import Product
from datetime import date, datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from store.models import Order
from scrapify import settings
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.
def index(request):
    # del request.session['cart_products']
    featured_products = Product.objects.filter(featured=True, is_active=True)[:5]
    best_seller = Product.objects.filter(is_active=True).order_by('-views')[:8]
    new_arrivals = Product.objects.filter(is_active=True).order_by('-created_at')[:8]
    most_viewed = Product.objects.filter(is_active=True).order_by('-views')[:8]
    discounts = Product.objects.filter(discount__gt=0, is_active=True)[:8]
    cart_items = str(len(request.session.get('cart_products', [])))

    return render(request, 'index.html' , {'featured_products': featured_products, 'current_date': date.today().strftime("%Y-%m-%d"), 'best_seller': best_seller, 'new_arrivals': new_arrivals, 'most_viewed': most_viewed, 'discounts': discounts, 'cart_items': cart_items, 'login': request.user.is_authenticated})

def products(request, category):
    products = Product.objects.filter(type=Product.get_id_by_category(category), is_active=True)
    if request.method == 'GET':
        if 'q' in request.GET:
            q = request.GET['q']
            products = products.filter(name__icontains=q)

    if request.method == 'POST':
        if 'price' in request.POST:
            prices = request.POST['price']
            prices = prices.split(' - ')
            cleaned_prices = [price.replace('₹', '') for price in prices]
            min_price = cleaned_prices[0]
            max_price = cleaned_prices[1]
            products = products.filter(price__range=(min_price, max_price))
    product_count = products.count()
    cart_items = str(len(request.session.get('cart_products', [])))
    return render(request, 'shop.html', {'products': products, 'category': category, 'product_count': product_count, 'cart_items': cart_items})

def product_detail(request, id):
    cart_items = str(len(request.session.get('cart_products', [])))
    product = Product.objects.get(id=id)
    return render(request, 'product.html', {'cart_items': cart_items, 'product': product})

def watchlist_product(request, id):
    is_logged_in = request.user.is_authenticated
    if not is_logged_in:
        return redirect('login')
    return render(request, 'index.html')

def cart(request):
    cart_items = str(len(request.session.get('cart_products', [])))
    cart_products = request.session.get('cart_products', [])
    products = Product.objects.filter(id__in=cart_products, is_active=True)
    cart_pricing = {}
    total_amount = 0
    for product in products:
        total_amount += int(product.final_price())
    shipping = 0
    if total_amount < 5000 and total_amount > 0:
        shipping = 100
    cart_pricing["total"] = float(round(total_amount, 2))
    # cart_pricing["shipping"] = float(round(shipping, 2))
    # cart_pricing["gst"] = float(round((total_amount * 0.18), 2))
    cart_pricing["commission"] = float(round((total_amount * 0.03), 2))
    cart_pricing["total_amount"] = float(round((total_amount + cart_pricing["commission"]), 2))
    return render(request, 'cart.html', {'products': products, 'cart_items': cart_items, 'cart_pricing': cart_pricing})

def checkout(request):
    is_logged_in = request.user.is_authenticated
    if not is_logged_in:
        return redirect('login')
    if len(request.session.get('cart_products', [])) == 0:
        return redirect('index')
    cart_items = str(len(request.session.get('cart_products', [])))
    cart_products = request.session.get('cart_products', [])
    products = Product.objects.filter(id__in=cart_products, is_active=True)     
    cart_pricing = {}
    total_amount = 0
    for product in products:
        total_amount += int(product.final_price())
    shipping = 0
    if total_amount < 5000 and total_amount > 0:
        shipping = 100
    cart_pricing["total"] = float(round(total_amount, 2))
    # cart_pricing["shipping"] = float(round(shipping, 2))
    # cart_pricing["gst"] = float(round((total_amount * 0.18), 2))
    cart_pricing["commission"] = float(round((total_amount * 0.03), 2))
    cart_pricing["total_amount"] = float(round((total_amount + cart_pricing["commission"]), 2))
    curr_dt = datetime.now()
    timestamp = int(round(curr_dt.timestamp()))
    order_number = 'OD{}{}'.format(request.user.id, timestamp)
    if request.method == 'POST':
        payment_mode = request.POST.get('payment_mode')
        shipping_address = request.POST.get('shipping_address')
        billing_address = request.POST.get('billing_address')
        place_order = False
        if payment_mode == 'cod':
            place_order = True
        elif payment_mode == 'stripe':
            if request.method == 'POST':
                # charge = stripe.Charge.create(
                #     amount=int(cart_pricing["total_amount"]),
                #     currency="usd",
                #     description="Scrapify payment",
                #     source=request.POST['stripeToken'],
                #     metadata={'order_number': order_number},
                # )
                place_order = True
        if place_order:
            order = Order.objects.create(
                user = request.user,
                payment_mode = payment_mode,
                shipping_address = shipping_address,
                billing_address = billing_address,
                total_amount = cart_pricing["total_amount"],
                is_paid = False,
                is_completed = False,
                order_number = order_number
            )
            if payment_mode == 'cod':
                order.is_paid = True
            order.products.set(products)
            order.save()
            for product in products:
                product.views += 1
                product.is_active = False
                product.save()
                payment = order.payments.create(vendor=product.vendor, amount=product.final_price())
                # if payment_mode == 'stripe':
                #     payment.is_approved = True
                payment.save()
            del request.session['cart_products']
            if payment_mode == 'cod':
                return redirect('complete_order', id=order.id)
            else:
                return redirect('complete_stripe_payment', id=order.id)

    return render(request, 'checkout.html', {'cart_items': cart_items, 'cart_pricing': cart_pricing, 'products': products, 'key': settings.STRIPE_PUB_KEY}) 

def complete_stripe_payment(request, id):
    order = Order.objects.get(id=id)
    if request.method == 'POST':
        order.is_paid = True
        order.payments.update(is_approved=True)
        order.save()
        return redirect('complete_order', id=order.id)
    return render(request, 'complete_stripe_payment.html', {'order': order, 'key': settings.STRIPE_PUB_KEY})

def complete_order(request, id):
    is_logged_in = request.user.is_authenticated
    if not is_logged_in:
        return redirect('login')
    order = Order.objects.get(id=id)
    cart_items = str(len(request.session.get('cart_products', [])))
    return render(request, 'order_complete.html', {'cart_items': cart_items, 'order': order})

def report_product(request, id):
    product = Product.objects.get(id=id)
    product.reported += 1
    product.save()
    return redirect('index')

def add_to_cart(request, id):
    if 'cart_products' not in request.session:
        request.session['cart_products'] = []
    if id not in request.session['cart_products']:
        request.session['cart_products'] = request.session['cart_products'] + [id]
    return redirect('index')

def remove_from_cart(request, id):
    cart_products = request.session['cart_products']
    if id in cart_products:
        cart_products.remove(id)
        request.session['cart_products'] = cart_products
    if 'cart_products' not in request.session:
        request.session['cart_products'] = []
    elif request.session['cart_products'] == None:
        request.session['cart_products'] = []
    return redirect('cart')

def login_user(request):
    is_logged_in = request.user.is_authenticated
    if is_logged_in:
        return redirect('index')
    if request.method == 'POST':
        if request.POST.get('auth_action') == 'login':
            email = request.POST.get('email')
            password = request.POST.get('password')
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, 'Welcome to ReCraftify')
                return redirect('index')
            else:
                messages.error(request, 'Invalid username or password.')
        elif request.POST.get('auth_action') == 'register':
            fname = request.POST.get('fname')
            lname = request.POST.get('lname')
            email = request.POST.get('email')
            password = request.POST.get('password')
            cpassword = request.POST.get('cpassword')
            if password == cpassword:
                user = User.objects.create(first_name=fname, last_name=lname, email=email, username=email)
                user.set_password(password)
                user.save()
                user.profiles.create(user=user, role='customer')
                # login(request, user)
                messages.success(request, 'Your account has been created! You are now able to log in.')
                return redirect('index')
            else:
                messages.error(request, 'Passwords do not match.')
    cart_items = str(len(request.session.get('cart_products', [])))
    return render(request, 'login.html', {'cart_items': cart_items})

def logout_user(request):
    if not request.user.is_authenticated:
        return redirect('index')
    logout(request)
    system_messages = messages.get_messages(request)
    for message in system_messages:
        # This iteration is necessary
        pass
    return redirect('index')

def orders(request):
    if not request.user.is_authenticated:
        return redirect('index')
    orders = Order.objects.filter(user=request.user)
    products = Product.objects.filter(orders__in=orders)
    return render(request, 'my_orders.html', {'orders': orders, 'products': products})
