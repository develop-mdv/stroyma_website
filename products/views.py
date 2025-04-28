from django.shortcuts import render, get_object_or_404, redirect
from .models import Product


def product_list(request):
    products = Product.objects.all()
    return render(request, 'products/product_list.html', {'products': products})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'products/product_detail.html', {'product': product})


def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # Получаем или создаем корзину из сессии
    cart = request.session.get('cart', {})

    # Добавляем товар в корзину
    if str(product.pk) in cart:
        cart[str(product.pk)] += 1  # Увеличиваем количество товара
    else:
        cart[str(product.pk)] = 1  # Добавляем новый товар

    # Сохраняем корзину в сессию
    request.session['cart'] = cart

    return redirect('product_list')


def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []

    # Получаем все товары из корзины
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, pk=product_id)
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'total_price': product.price * quantity,
        })

    context = {
        'cart_items': cart_items,
    }
    return render(request, 'products/cart.html', context)