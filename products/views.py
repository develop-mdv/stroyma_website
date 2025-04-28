from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Order, OrderItem
from .forms import OrderForm, SearchForm
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q


def product_list(request):
    form = SearchForm(request.GET)
    products = Product.objects.all()

    # Обработка поиска
    if form.is_valid():
        query = form.cleaned_data['query']
        if query:
            products = products.filter(name__icontains=query)  # iexact также игнорирует регистр

    # Обработка фильтрации по цене
    price_max = request.GET.get('price_max')
    if price_max:
        products = products.filter(price__lte=price_max)

    return render(request, 'products/product_list.html', {'products': products, 'search_form': form})

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


def remove_from_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # Получаем корзину из сессии
    cart = request.session.get('cart', {})

    # Удаляем товар из корзины
    if str(product.pk) in cart:
        del cart[str(product.pk)]

    # Сохраняем обновленную корзину в сессию
    request.session['cart'] = cart

    return redirect('view_cart')


def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('view_cart')  # Если корзина пуста, перенаправляем на страницу корзины

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Создаем новый заказ
            order = Order.objects.create()

            # Добавляем товары из корзины в заказ
            for product_id, quantity in cart.items():
                product = Product.objects.get(pk=product_id)
                OrderItem.objects.create(order=order, product=product, quantity=quantity)

            # Очищаем корзину после оформления заказа
            request.session['cart'] = {}

            return redirect('checkout_success')  # Перенаправляем на страницу успеха
    else:
        form = OrderForm()

    context = {
        'form': form,
        'cart_items': cart,
    }
    return render(request, 'products/checkout.html', context)

def checkout_success(request):
    return render(request, 'products/checkout_success.html')

def contact(request):
    return render(request, 'products/contact.html')

def search_ajax(request):
    query = request.GET.get('query', '').lower()  # Преобразуем запрос в нижний регистр
    price_max = request.GET.get('price_max', None)

    products = Product.objects.all()

    if query:
        # Явно преобразуем поле name в нижний регистр и сравниваем
        products = products.filter(
            Q(name__icontains=query) |  # Поиск по части слова (игнорирует регистр)
            Q(description__icontains=query)  # Опционально: поиск по описанию
        )

    if price_max:
        products = products.filter(price__lte=price_max)

    context = {
        'products': products,
    }

    # Возвращаем HTML-код с результатами поиска
    results_html = render_to_string('products/search_results.html', context)
    return JsonResponse({'results': results_html})
