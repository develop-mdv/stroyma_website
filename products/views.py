from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Order, OrderItem
from .forms import OrderForm, SearchForm, ContactForm
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q, Max, Min
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)
EMAIL_TO_SEND = 'ivanverovitch@yandex.ru'

def product_list(request):
    form = SearchForm(request.GET)
    products = Product.objects.all()

    # Получаем минимальную и максимальную цены
    min_price = products.aggregate(Min('price'))['price__min'] or 0
    max_price = products.aggregate(Max('price'))['price__max'] or 0

    # Поиск
    if form.is_valid():
        query = form.cleaned_data['query']
        if query:
            products = products.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )

    # Фильтрация по цене
    price_min = request.GET.get('price_min', min_price)
    price_max = request.GET.get('price_max', max_price)

    if price_min and str(price_min).isdigit():
        products = products.filter(price__gte=int(price_min))
    if price_max and str(price_max).isdigit():
        products = products.filter(price__lte=int(price_max))

    # Сортировка
    sort_by = request.GET.get('sort_by', 'name')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')

    # Пагинация
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'products/product_list.html', {
        'page_obj': page_obj,
        'search_form': form,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
    })

def search_ajax(request):
    query = request.GET.get('query', '').lower()  # Преобразуем запрос в нижний регистр
    price_min = request.GET.get('price_min', None)
    price_max = request.GET.get('price_max', None)
    sort_by = request.GET.get('sort_by', 'name')  # Сортировка по умолчанию
    page_number = request.GET.get('page', 1)
    autocomplete = request.GET.get('autocomplete', False)

    products = Product.objects.all()

    # Фильтрация по запросу
    if query:
        products = products.filter(
            Q(name__icontains=query) |  # Поиск по части названия товара
            Q(description__icontains=query)  # Поиск по описанию
        )

    # Если это запрос автодополнения, возвращаем только названия товаров
    if autocomplete:
        products = products[:5]  # Ограничим 5 подсказками
        return JsonResponse({'products': [{'name': product.name} for product in products]})

    # Фильтрация по цене
    if price_min and price_min.isdigit():
        products = products.filter(price__gte=price_min)
    if price_max and price_max.isdigit():
        products = products.filter(price__lte=price_max)

    # Применяем сортировку
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')

    # Пагинация
    paginator = Paginator(products, 12)
    page = paginator.get_page(page_number)

    context = {
        'products': page,
        'sort_by': sort_by,
    }

    results_html = render_to_string('products/search_results.html', context)
    return JsonResponse({
        'results': results_html,
        'has_next': page.has_next(),
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'products/product_detail.html', {'product': product})

def quick_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'products/quick_view.html', {'product': product})

def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # Получаем или создаем корзину из сессии
    cart = request.session.get('cart', {})

    # Обработка количества из формы
    quantity = int(request.POST.get('quantity', 1))  # По умолчанию добавляем 1 товар
    if str(product.pk) in cart:
        cart[str(product.pk)] += quantity  # Увеличиваем количество товара
    else:
        cart[str(product.pk)] = quantity   # Добавляем новый товар

    # Сохраняем корзину в сессию
    request.session['cart'] = cart

    return redirect('view_cart')

def view_cart(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0

    # Получаем все товары из корзины
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, pk=product_id)
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'total_price': product.price * quantity,
        })
        total_price += product.price * quantity  # Рассчитываем общую сумму

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
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

def merge_session_cart_to_user_cart(request):
    """Перенос корзины из сессии в заказ пользователя после входа."""
    session_cart = request.session.get('cart', {})
    if request.user.is_authenticated and session_cart:
        # Проверяем, есть ли незавершенный заказ у пользователя
        order = Order.objects.filter(user=request.user, status='pending').last()
        if not order:
            order = Order.objects.create(user=request.user, status='pending')

        for product_id, quantity in session_cart.items():
            product = get_object_or_404(Product, pk=product_id)
            # Проверяем, есть ли уже этот товар в заказе
            order_item, created = OrderItem.objects.get_or_create(
                order=order,
                product=product,
                defaults={'quantity': quantity}
            )
            if not created:
                order_item.quantity += quantity
                order_item.save()

        # Очищаем корзину в сессии после переноса
        request.session['cart'] = {}

def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('view_cart')  # Если корзина пустая — уходим

    cart_items = []
    total_price = 0

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, pk=product_id)
        item_total = product.price * quantity
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'total_price': item_total,
        })
        total_price += item_total

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            user_name = form.cleaned_data['first_name']
            user_lastname = form.cleaned_data['last_name']
            user_email = form.cleaned_data['email']
            user_phone = form.cleaned_data['phone']
            delivery_address = form.cleaned_data['address']

            # Создаем заказ в БД
            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                status='pending'
            )

            # Сохраняем товары в заказ
            for product_id, quantity in cart.items():
                product = get_object_or_404(Product, pk=product_id)
                OrderItem.objects.create(order=order, product=product, quantity=quantity)

            # Формируем текст письма
            html_order_summary = render_to_string('products/order_email_template.html', {
                'items': cart_items,
                'total_price': total_price,
                'user_name': user_name,
                'user_lastname': user_lastname,
                'user_email': user_email,
                'user_phone': user_phone,
                'delivery_address': delivery_address,
            })

            plain_text = strip_tags(html_order_summary)
            try:
                send_mail(
                    f'Новый заказ от {user_name} {user_lastname}',
                    plain_text,
                    EMAIL_TO_SEND,
                    [EMAIL_TO_SEND],
                    html_message=html_order_summary,
                    fail_silently=False
                )
                request.session['cart'] = {}  # Очищаем корзину после оформления
                messages.success(request, 'Спасибо! Заказ отправлен менеджеру. С вами свяжутся.')
                return redirect('checkout_success')
            except Exception as e:
                logger.error(f'Ошибка при отправке email: {e}')
                messages.error(request, f'Произошла ошибка при отправке заказа: {e}')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = OrderForm()

    context = {
        'form': form,
        'cart_items': cart_items,
        'total_price': total_price,
    }

    return render(request, 'products/checkout.html', context)

def checkout_success(request):
    return render(request, 'products/checkout_success.html')

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            name += f'|email:{email}'

            message = form.cleaned_data['message']

            try:
                send_mail(
                    f'Новое сообщение от {name}',
                    message,
                    EMAIL_TO_SEND,
                    [EMAIL_TO_SEND],
                    fail_silently=False
                )
                messages.success(request, 'Ваше сообщение успешно отправлено!')
            except Exception as e:
                logger.error(f'Ошибка при отправке email: {str(e)}')
                messages.error(request, f'Произошла ошибка при отправке сообщения: {str(e)}')
            return redirect('contact')
    else:
        form = ContactForm()

    context = {
        'form': form,
    }
    return render(request, 'products/contact.html', context)