from django.urls import path
from .views import index, products, product_detail, watchlist_product, add_to_cart, login_user, cart, remove_from_cart, checkout, complete_order, logout_user, report_product, complete_stripe_payment, orders

urlpatterns = [
    path('', index, name='index'),
    path('products/<str:category>', products, name='products'),
    path('product_detail/<int:id>', product_detail, name='product_detail'),
    path('watchlist_product/<int:id>', watchlist_product, name='watchlist_product'),
    path('add_to_cart/<int:id>', add_to_cart, name='add_to_cart'),
    path('login', login_user, name='login'),
    path('cart', cart, name='cart'),
    path('remove_from_cart/<int:id>', remove_from_cart, name='remove_from_cart'),
    path('checkout', checkout, name='checkout'),
    path('complete_order/<int:id>', complete_order, name='complete_order'),
    path('logout', logout_user, name='logout'),
    path('report_product/<int:id>', report_product, name='report_product'),
    path('complete_stripe_payment/<int:id>', complete_stripe_payment, name='complete_stripe_payment'),
    path('orders', orders, name='my_orders')
]