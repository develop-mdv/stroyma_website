import json
import logging
import re
import threading
from decimal import Decimal
from math import ceil
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Max, Min
from django.db.models.functions import Round
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.views.generic import DetailView, TemplateView
from django_ratelimit.decorators import ratelimit

from .forms import ColorSelectionRequestForm, ContactForm, OrderForm, SearchForm
from .models import (
    Cart,
    CartItem,
    Category,
    Order,
    OrderContact,
    OrderItem,
    Product,
)

logger = logging.getLogger(__name__)


def cart_total_quantity(request):
    """Подсчитывает суммарное количество товаров в корзине (сумма quantity, а не позиций)."""
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if not cart:
            return 0
        return sum(item.quantity for item in cart.items.all())
    session_cart = request.session.get('cart', {}) or {}
    try:
        return sum(int(q) for q in session_cart.values())
    except (TypeError, ValueError):
        return 0

def _order_notify_recipient():
    return getattr(settings, 'ORDER_NOTIFY_EMAIL', None) or settings.EMAIL_HOST_USER


def _sanitize_mail_subject_line(value: str, max_len: int = 200) -> str:
    return ''.join(value.splitlines()).strip()[:max_len]

def _mask_email_for_log(value: str) -> str:
    if not value:
        return ''
    s = str(value).strip()
    if '@' not in s:
        return s[:2] + '***'
    local, domain = s.split('@', 1)
    safe_local = (local[:2] + '***') if local else '***'
    safe_domain = (domain[:1] + '***') if domain else '***'
    return f'{safe_local}@{safe_domain}'


def get_or_create_cart(request):
    if not request.user.is_authenticated:
        return None
    cart, _created = Cart.objects.get_or_create(user=request.user)
    session_cart = request.session.get('cart', {}) or {}
    for product_id, quantity in list(session_cart.items()):
        product = Product.objects.filter(pk=product_id).first()
        if not product:
            continue
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            continue
        if qty < 1:
            continue
        cart_item, _c = CartItem.objects.get_or_create(cart=cart, product=product)
        cart_item.quantity = qty
        cart_item.save()
    if session_cart:
        request.session['cart'] = {}
    return cart

def _home_cart_context(request):
    """Compact cart data for the home page and its live preview."""
    if request.user.is_authenticated:
        cart = get_or_create_cart(request)
        entries = (
            CartItem.objects.filter(cart=cart).select_related('product')
            if cart else []
        )
        rows = [
            {'product': item.product, 'quantity': item.quantity,
             'total_price': item.product.price * item.quantity}
            for item in entries
        ]
    else:
        quantities = {}
        for product_id, raw_quantity in (request.session.get('cart', {}) or {}).items():
            try:
                quantity = int(raw_quantity)
                if quantity > 0:
                    quantities[int(product_id)] = quantity
            except (TypeError, ValueError):
                continue
        products = Product.objects.filter(pk__in=quantities).in_bulk()
        rows = [
            {'product': products[product_id], 'quantity': quantity,
             'total_price': products[product_id].price * quantity}
            for product_id, quantity in quantities.items() if product_id in products
        ]
    return {
        'cart_preview_items': rows,
        'cart_preview_count': sum(row['quantity'] for row in rows),
        'cart_preview_total': sum((row['total_price'] for row in rows), Decimal('0')),
    }


def _catalog_price_range(products, request):
    """Get available prices before applying the price filter itself."""
    bounds = products.aggregate(low=Min('display_price'), high=Max('display_price'))
    minimum = int(bounds['low']) if bounds['low'] is not None else 0
    maximum = ceil(bounds['high']) if bounds['high'] is not None else 0

    raw_minimum = str(request.GET.get('price_min', minimum))
    raw_maximum = str(request.GET.get('price_max', maximum))
    selected_minimum = int(raw_minimum) if raw_minimum.isdigit() else minimum
    selected_maximum = int(raw_maximum) if raw_maximum.isdigit() else maximum
    if selected_minimum > maximum or selected_maximum < minimum or selected_minimum > selected_maximum:
        selected_minimum, selected_maximum = minimum, maximum
    else:
        selected_minimum = max(minimum, selected_minimum)
        selected_maximum = min(maximum, selected_maximum)
    return minimum, maximum, selected_minimum, selected_maximum, bounds['low'] is not None


def _browser_candidates(request, scope=None):
    """Products matching search and categories, before the price facet."""
    products = Product.objects.all()
    if scope is not None:
        products = products.filter(categories__in=scope.get_descendants(include_self=True))

    query = (request.GET.get('query') or request.GET.get('name') or '').strip()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    selected_ids = [int(value) for value in request.GET.getlist('category') if value.isdigit()]
    categories = Category.objects.filter(pk__in=selected_ids)
    if scope is not None:
        categories = categories.filter(pk__in=scope.get_descendants().values('pk'))
    selected_categories = []
    category_ids = set()
    for category in categories:
        selected_categories.append(str(category.pk))
        category_ids.update(category.get_descendants(include_self=True).values_list('pk', flat=True))
    if category_ids:
        products = products.filter(categories__pk__in=category_ids)
    return products.distinct(), query, selected_categories


def _browser_page_context(request, scope=None, page_size=12):
    products, query, selected_categories = _browser_candidates(request, scope)
    products = products.annotate(display_price=Round('price'))
    minimum, maximum, selected_minimum, selected_maximum, available = _catalog_price_range(products, request)
    products = products.filter(display_price__gte=selected_minimum, display_price__lte=selected_maximum)

    sort_by = request.GET.get('sort_by', 'name')
    if sort_by == 'price_asc':
        products = products.order_by('price', 'pk')
    elif sort_by == 'price_desc':
        products = products.order_by('-price', 'pk')
    else:
        sort_by = 'name'
        products = products.order_by('name', 'pk')

    paginator = Paginator(products, page_size)
    page = paginator.get_page(request.GET.get('page'))
    page_path = scope.get_absolute_url() if scope is not None else reverse('catalog')

    def page_url(number):
        params = request.GET.copy()
        for key in ('view', 'scope', 'autocomplete', 'name', 'page'):
            params.pop(key, None)
        if query:
            params['query'] = query
        if number > 1:
            params['page'] = number
        encoded = params.urlencode()
        return f'{page_path}?{encoded}' if encoded else page_path

    pagination_pages = [
        {'number': number, 'url': page_url(number) if isinstance(number, int) else None,
         'current': number == page.number}
        for number in paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)
    ]
    categories_tree = Category.objects.filter(parent=scope).order_by('tree_id', 'lft')
    return {
        'products': page,
        'search_query': query,
        'selected_categories': selected_categories,
        'sort_by': sort_by,
        'min_price': minimum,
        'max_price': maximum,
        'selected_price_min': selected_minimum,
        'selected_price_max': selected_maximum,
        'has_price_candidates': available,
        'categories_tree': categories_tree,
        'scope_category_id': scope.pk if scope is not None else '',
        'browser_path': page_path,
        'pagination_pages': pagination_pages,
        'pagination_previous_url': page_url(page.previous_page_number()) if page.has_previous() else None,
        'pagination_next_url': page_url(page.next_page_number()) if page.has_next() else None,
    }


def product_list(request):
    form = SearchForm(request.GET)
    products = Product.objects.all()

    # Получаем корневые категории и их потомков
    root_categories = Category.objects.filter(parent=None)
    categories_tree = []
    for category in root_categories:
        categories_tree.append({
            'category': category,
            'children': category.get_children()
        })

    if form.is_valid():
        query = form.cleaned_data['query']
        if query:
            products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    # Фильтрация по категориям
    selected_categories = request.GET.getlist('category')
    if selected_categories:
        # Получаем только выбранные категории
        categories_to_filter = []
        for category_id in selected_categories:
            try:
                category = Category.objects.get(id=category_id)
                categories_to_filter.append(category)
            except Category.DoesNotExist:
                continue
        
        # Создаем Q-объект для каждой категории
        category_filters = Q()
        for category in categories_to_filter:
            category_filters |= Q(categories=category)
        
        # Применяем фильтр с использованием OR
        products = products.filter(category_filters).distinct()

    products = products.annotate(display_price=Round('price'))
    min_price, max_price, price_min, price_max, has_price_candidates = _catalog_price_range(products, request)
    products = products.filter(display_price__gte=price_min, display_price__lte=price_max)

    sort_by = request.GET.get('sort_by', 'name')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    else:
        products = products.order_by('name')

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'products/product_list.html', {
        'page_obj': page_obj,
        'search_form': form,
        'min_price': min_price,
        'max_price': max_price,
        'selected_price_min': price_min,
        'selected_price_max': price_max,
        'has_price_candidates': has_price_candidates,
        'sort_by': sort_by,
        'categories_tree': categories_tree,
        'selected_categories': selected_categories,
        **_home_cart_context(request),
    })


def cart_preview(request):
    context = _home_cart_context(request)
    return JsonResponse({
        'html': render_to_string('products/home_cart_preview.html', context, request=request),
        'count': context['cart_preview_count'],
    })


@ratelimit(key='ip', rate='30/m', block=True)
def search_ajax(request):
    if request.GET.get('view') == 'grid':
        scope_id = request.GET.get('scope', '')
        scope = get_object_or_404(Category, pk=scope_id) if scope_id.isdigit() else None
        if request.GET.get('autocomplete'):
            candidates, query, _ = _browser_candidates(request, scope)
            matching_categories = Category.objects.filter(name__icontains=query).select_related('parent')
            if scope is not None:
                matching_categories = matching_categories.filter(
                    pk__in=scope.get_descendants().values('pk')
                )
            return JsonResponse({'categories': [
                {
                    'name': match.name,
                    'url': match.get_absolute_url(),
                    'parent_name': match.parent.name if match.parent else '',
                }
                for match in matching_categories.order_by('level', 'name')[:6]
            ], 'products': [
                {
                    'name': product.name,
                    'price': f'{product.price:,.0f}'.replace(',', ' '),
                    'image': product.image.url if product.image else '',
                    'url': product.get_absolute_url(),
                }
                for product in candidates.order_by('name')[:6]
            ]})

        context = _browser_page_context(request, scope)
        return JsonResponse({
            'results': render_to_string('products/search_results.html', context, request=request),
            'pagination': render_to_string('products/catalog_pagination.html', context, request=request),
            'count': context['products'].paginator.count,
            'price_bounds': {
                'min': context['min_price'], 'max': context['max_price'],
                'available': context['has_price_candidates'],
            },
            'selected_price': {
                'min': context['selected_price_min'], 'max': context['selected_price_max'],
            },
        })

    query = request.GET.get('query', '').lower()
    sort_by = request.GET.get('sort_by', 'name')
    page_number = request.GET.get('page', 1)
    autocomplete = request.GET.get('autocomplete', False)
    
    selected_categories = request.GET.getlist('category')

    products = Product.objects.all()

    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    if selected_categories:
        categories_to_filter = []
        for category_id in selected_categories:
            try:
                category = Category.objects.get(id=category_id)
                categories_to_filter.append(category)
            except Category.DoesNotExist:
                continue

        category_filters = Q()
        for category in categories_to_filter:
            category_filters |= Q(categories=category)

        products = products.filter(category_filters).distinct()

    if autocomplete:
        products = products.order_by('name')[:6]
        return JsonResponse({'products': [
            {
                'name': product.name,
                'price': f'{product.price:,.0f}'.replace(',', ' '),
                'image': product.image.url if product.image else '',
                'url': product.get_absolute_url(),
            }
            for product in products
        ]})

    products = products.annotate(display_price=Round('price'))
    min_price, max_price, price_min, price_max, has_price_candidates = _catalog_price_range(products, request)
    products = products.filter(display_price__gte=price_min, display_price__lte=price_max)

    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')
    else:
        products = products.order_by('name')

    paginator = Paginator(products, 12)
    page = paginator.get_page(page_number)

    context = {
        'products': page,
        'sort_by': sort_by,
    }

    results_template = (
        'products/home_search_results.html'
        if request.GET.get('view') == 'home'
        else 'products/search_results.html'
    )
    results_html = render_to_string(results_template, context, request=request)
    return JsonResponse({
        'results': results_html,
        'has_next': page.has_next(),
        'count': paginator.count,
        'price_bounds': {'min': min_price, 'max': max_price, 'available': has_price_candidates},
        'selected_price': {'min': price_min, 'max': price_max},
    })

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    # Передаем метаданные в контекст
    context = {
        'product': product,
        'meta_title': product.meta_title,
        'meta_description': product.meta_description,
        'keywords': product.keywords,
    }
    return render(request, 'products/product_detail.html', context)

def product_detail_legacy(request, pk):
    """Обработчик для поддержки старых URL с использованием pk"""
    product = get_object_or_404(Product, pk=pk)
    return redirect(product.get_absolute_url(), permanent=True)

def quick_view(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'products/quick_view.html', {'product': product})

@ratelimit(key='ip', rate='30/m', method='POST', block=True)
def add_to_cart(request, pk):
    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest'
        or 'application/json' in request.headers.get('Accept', '')
    )
    if request.method != 'POST':
        product = get_object_or_404(Product, pk=pk)
        if is_ajax:
            return JsonResponse({'success': False, 'message': 'Метод не разрешён.'}, status=405)
        return redirect(product.get_absolute_url())

    try:
        quantity = int(request.POST.get('quantity') or 1)
    except (TypeError, ValueError):
        quantity = 1
    if quantity < 1:
        quantity = 1

    with transaction.atomic():
        product = Product.objects.select_for_update().get(pk=pk)
        if request.user.is_authenticated:
            cart = get_or_create_cart(request)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            desired_quantity = quantity if created else cart_item.quantity + quantity
        else:
            session_cart = request.session.get('cart', {}) or {}
            key = str(product.pk)
            desired_quantity = int(session_cart.get(key, 0) or 0) + quantity

        if request.user.is_authenticated:
            cart_item.quantity = desired_quantity
            cart_item.save()
        else:
            session_cart[key] = desired_quantity
            request.session['cart'] = session_cart
            request.session.modified = True

    cart_item_count = cart_total_quantity(request)
    if is_ajax:
        return JsonResponse({
            'success': True,
            'message': f'{product.name} успешно добавлен в корзину',
            'cart_item_count': cart_item_count,
        })
    messages.success(request, f'{product.name} добавлен в корзину')
    return redirect('view_cart')

@ratelimit(key='ip', rate='30/m', method='POST', block=True)
def update_cart(request, pk):
    if request.method != 'POST':
        return redirect('view_cart')
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        return JsonResponse({
            'success': False,
            'message': 'Недопустимое количество.',
            'current_quantity': 1
        })
    if quantity <= 0:
        return JsonResponse({
            'success': False,
            'message': 'Количество должно быть больше 0.',
            'current_quantity': 1
        })
    with transaction.atomic():
        product = Product.objects.select_for_update().get(pk=pk)
        if request.user.is_authenticated:
            cart = get_or_create_cart(request)
            cart_item, _ = CartItem.objects.get_or_create(cart=cart, product=product)
            cart_item.quantity = quantity
            cart_item.save()
            total_price = sum(
                item.product.price * item.quantity
                for item in CartItem.objects.filter(cart=cart)
            )
        else:
            sc = request.session.get('cart', {}) or {}
            sc[str(product.pk)] = quantity
            request.session['cart'] = sc
            request.session.modified = True
            total_price = 0
            for spid, qty in sc.items():
                p = Product.objects.filter(pk=spid).first()
                if p:
                    total_price += p.price * int(qty)
    item_total_price = product.price * quantity
    cart_item_count = cart_total_quantity(request)
    return JsonResponse({
        'success': True,
        'item_total_price': float(item_total_price),
        'total_price': float(total_price),
        'cart_item_count': cart_item_count,
    })

def view_cart(request):
    cart_items = []
    total_price = 0
    if request.user.is_authenticated:
        cart = get_or_create_cart(request)
        cart_items = CartItem.objects.filter(cart=cart) if cart else []
        total_price = sum(item.total_price for item in cart_items)
    else:
        sc = request.session.get('cart', {}) or {}
        cleaned = {}
        for product_id, quantity in sc.items():
            product = Product.objects.filter(pk=product_id).first()
            if not product:
                continue
            try:
                qty = int(quantity)
            except (TypeError, ValueError):
                continue
            if qty < 1:
                continue
            cleaned[str(product_id)] = qty
            total_item_price = product.price * qty
            cart_items.append({
                'product': product,
                'quantity': qty,
                'total_price': total_item_price,
            })
            total_price += total_item_price
        if cleaned != sc:
            request.session['cart'] = cleaned
            request.session.modified = True
    context = {
        'cart_items': cart_items,
        'total_price': float(total_price),
    }
    return render(request, 'products/cart.html', context)

def remove_from_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.user.is_authenticated:
        cart = get_or_create_cart(request)
        CartItem.objects.filter(cart=cart, product=product).delete()
    else:
        cart = request.session.get('cart', {})
        if str(product.pk) in cart:
            del cart[str(product.pk)]
        request.session['cart'] = cart

    return redirect('view_cart')

def merge_session_cart_to_user_cart(request):
    session_cart = request.session.get('cart', {}) or {}
    if not request.user.is_authenticated or not session_cart:
        return
    cart, _ = Cart.objects.get_or_create(user=request.user)
    for product_id, quantity in list(session_cart.items()):
        product = Product.objects.filter(pk=product_id).first()
        if not product:
            continue
        try:
            qty = int(quantity)
        except (TypeError, ValueError):
            continue
        if qty < 1:
            continue
        cart_item, _c = CartItem.objects.get_or_create(cart=cart, product=product)
        cart_item.quantity = qty
        cart_item.save()
    request.session['cart'] = {}

def _build_checkout_lines_for_post(request):
    """Возвращает список (product_id, quantity) для оформления или None, если корзина пуста/некорректна."""
    if request.user.is_authenticated:
        cart = get_or_create_cart(request)
        if not cart:
            return None
        rows = list(
            CartItem.objects.filter(cart=cart).values_list('product_id', 'quantity')
        )
        return rows if rows else None
    sc = request.session.get('cart', {}) or {}
    out = []
    for product_id, quantity in sc.items():
        try:
            pid = int(product_id)
            q = int(quantity)
        except (TypeError, ValueError):
            continue
        if q < 1:
            continue
        if Product.objects.filter(pk=pid).exists():
            out.append((pid, q))
    return out if out else None


def _queue_order_notification_email(
    subject, plain_text, html_message, from_email, notify, order_id
):
    def _run():
        try:
            send_mail(
                subject,
                plain_text,
                from_email,
                [notify],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            logger.error('Ошибка при отправке email о заказе #%s: %s', order_id, e)

    threading.Thread(target=_run, daemon=True).start()


@ratelimit(key='ip', rate='20/m', method='POST', block=True)
def checkout(request):
    if request.user.is_authenticated:
        cart = get_or_create_cart(request)
        items_qs = (
            CartItem.objects.filter(cart=cart).select_related('product')
            if cart
            else CartItem.objects.none()
        )
        if not items_qs.exists():
            if request.method == 'GET':
                if request.session.get('last_order_id'):
                    return redirect('checkout_success')
                return redirect('view_cart')
            cart_items = []
            total_price = 0
        else:
            cart_items = [
                {
                    'product': item.product,
                    'quantity': item.quantity,
                    'total_price': item.total_price,
                }
                for item in items_qs
            ]
            total_price = sum(x['total_price'] for x in cart_items)
    else:
        sc = request.session.get('cart', {}) or {}
        if not sc:
            if request.method == 'GET':
                if request.session.get('last_order_id'):
                    return redirect('checkout_success')
                return redirect('view_cart')
            cart_items = []
            total_price = 0
        else:
            cart_items = []
            total_price = 0
            for product_id, quantity in sc.items():
                product = Product.objects.filter(pk=product_id).first()
                if not product:
                    continue
                try:
                    q = int(quantity)
                except (TypeError, ValueError):
                    continue
                if q < 1:
                    continue
                line_total = product.price * q
                cart_items.append(
                    {
                        'product': product,
                        'quantity': q,
                        'total_price': line_total,
                    }
                )
                total_price += line_total
        if not cart_items:
            if request.method == 'GET':
                if request.session.get('last_order_id'):
                    return redirect('checkout_success')
                return redirect('view_cart')

    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            user_name = form.cleaned_data['first_name']
            user_lastname = form.cleaned_data['last_name']
            user_email = form.cleaned_data['email']
            user_phone = form.cleaned_data['phone']
            delivery_address = form.cleaned_data['address']
            comment = form.cleaned_data.get('comment', '') or ''

            lines = _build_checkout_lines_for_post(request)
            if not lines:
                messages.error(request, 'Корзина пуста или устарела. Оформите заказ снова.')
                return redirect('view_cart')

            try:
                with transaction.atomic():
                    order = Order.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        status='new',
                    )
                    OrderContact.objects.create(
                        order=order,
                        first_name=user_name,
                        last_name=user_lastname,
                        email=user_email,
                        phone=user_phone,
                        address=delivery_address,
                        comment=comment,
                    )
                    for product_id, qty in sorted(lines, key=lambda t: t[0]):
                        product = Product.objects.select_for_update().get(pk=product_id)
                        OrderItem.objects.create(order=order, product=product, quantity=qty)
                        product.stock = max(0, product.stock - qty)
                        product.save(update_fields=['stock'])
                    if request.user.is_authenticated:
                        CartItem.objects.filter(cart__user=request.user).delete()
                    else:
                        request.session['cart'] = {}
                        request.session.modified = True
            except Product.DoesNotExist:
                messages.error(request, 'В корзине указан несуществующий товар. Обновите корзину.')
                return redirect('view_cart')

            request.session['last_order_id'] = order.id
            email_items = [
                {
                    'product': oi.product,
                    'quantity': oi.quantity,
                    'total_price': oi.total_price,
                }
                for oi in order.items.select_related('product').all()
            ]
            html_order_summary = render_to_string('products/order_email_template.html', {
                'items': email_items,
                'total_price': order.total_cost,
                'user_name': user_name,
                'user_lastname': user_lastname,
                'user_email': user_email,
                'user_phone': user_phone,
                'delivery_address': delivery_address,
                'order': order,
            })
            plain_text = strip_tags(html_order_summary)
            notify = _order_notify_recipient()
            _queue_order_notification_email(
                _sanitize_mail_subject_line(
                    f'Новый заказ №{order.id}'
                ),
                plain_text,
                html_order_summary,
                settings.DEFAULT_FROM_EMAIL,
                notify,
                order.id,
            )
            return redirect('checkout_success')
        messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = OrderForm(user=request.user)

    return render(request, 'products/checkout.html', {
        'form': form,
        'cart_items': cart_items,
        'total_price': total_price,
    })

def checkout_success(request):
    order = None
    order_id = request.session.pop('last_order_id', None)
    if order_id:
        order = Order.objects.filter(pk=order_id).first()
    return render(request, 'products/checkout_success.html', {'order': order})

@ratelimit(key='ip', rate='20/m', method='POST', block=True)
def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            notify = _order_notify_recipient()
            try:
                send_mail(
                    _sanitize_mail_subject_line('Новое сообщение с сайта Stroyma (форма контактов)'),
                    f'Имя: {name}\nEmail: {email}\n\nСообщение:\n{message}',
                    settings.DEFAULT_FROM_EMAIL,
                    [notify],
                    fail_silently=False
                )
                messages.success(request, 'Ваше сообщение успешно отправлено!')
            except Exception:
                logger.exception('Ошибка при отправке email из формы контактов')
                messages.error(
                    request,
                    'Произошла ошибка при отправке сообщения. Попробуйте позже.',
                )
            return redirect('contact')
    else:
        form = ContactForm()

    return render(request, 'products/contact.html', {
        'form': form,
    })

@ratelimit(key='ip', rate='20/m', method='POST', block=True)
def color_selection(request):
    sent = request.GET.get('sent') == '1'
    send_error = False
    defaults = {'f': 'kamesh15', 'c': 'c2', 'p': 'tibet-5', 't': 'day', 'l': 'full'}
    if request.method == 'POST':
        try:
            state = json.loads((request.POST.get('config_state') or '')[:500] or '{}')
        except (ValueError, TypeError):
            state = {}
        if not isinstance(state, dict):
            state = {}
        selected = {
            'f': state.get('facadeTexture'),
            'c': state.get('facadeColor'),
            'p': state.get('plinthTexture'),
            't': state.get('time'),
            'l': state.get('landscape'),
        }
    else:
        selected = {key: request.GET.get(key) for key in defaults}
    for key, value in selected.items():
        if isinstance(value, str) and re.fullmatch(r'[a-z0-9-]{1,40}', value):
            defaults[key] = value
    widget_query = urlencode({**defaults, 's': 'page', 'v': '53'})

    if request.method == 'POST':
        form = ColorSelectionRequestForm(request.POST)
        if form.is_valid():
            details = form.cleaned_data
            body = (
                f"Имя: {details['name']}\n"
                f"Телефон: {details['phone']}\n"
                f"Email: {details['email'] or 'не указан'}\n\n"
                f"Фасад: {details['facade'] or 'не выбран'}\n"
                f"Цоколь: {details['plinth'] or 'не выбран'}\n\n"
                f"Комментарий: {details['message'] or 'нет'}"
            )
            try:
                send_mail(
                    'Заявка на подбор цвета фасада — СтройМа',
                    body,
                    settings.DEFAULT_FROM_EMAIL,
                    [_order_notify_recipient()],
                    fail_silently=False,
                )
            except Exception:
                logger.exception('Ошибка при отправке заявки на подбор цвета фасада')
                send_error = True
            else:
                return redirect(f"{reverse('color_selection')}?sent=1#colorRequest")
    else:
        initial = {}
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            profile = getattr(user, 'profile', None)
            initial = {
                'name': user.get_full_name().strip()[:100],
                'email': user.email or '',
                'phone': profile.phone if profile and profile.phone else '',
            }
        form = ColorSelectionRequestForm(initial=initial)

    return render(request, 'products/color_selection.html', {
        'form': form,
        'sent': sent,
        'send_error': send_error,
        'widget_query': widget_query,
    })

class CategoryDetailView(DetailView):
    model = Category
    template_name = 'products/category_detail.html'
    context_object_name = 'category'
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        
        context.update({
            'meta_title': f'{category.name} - Каталог товаров',
            'meta_description': category.description or f'Товары категории {category.name}',
            'og_description': f'Просмотрите товары категории {category.name}. {category.description or ""}',
            'subcategories': category.get_children(),
            'breadcrumbs': self.get_breadcrumbs(category),
            **_browser_page_context(self.request, category, self.paginate_by),
        })
        return context
    
    def get_breadcrumbs(self, category):
        """Формирует хлебные крошки для категории"""
        breadcrumbs = []
        current = category
        
        while current:
            breadcrumbs.insert(0, {
                'name': current.name,
                'url': current.get_absolute_url()
            })
            current = current.parent
            
        # Добавляем ссылку на главную
        breadcrumbs.insert(0, {
            'name': 'Главная',
            'url': reverse('product_list')
        })
        
        return breadcrumbs

def about(request):
    """
    Отображает страницу "О компании"
    """
    return render(request, 'products/about.html')

def policy(request):
    """Отображение страницы политики конфиденциальности"""
    return render(request, 'products/policy.html', {
        'meta_title': 'Политика конфиденциальности - ООО "СТРОЙМА"',
        'meta_description': 'Политика конфиденциальности ООО "СТРОЙМА". Узнайте, какие персональные данные мы собираем и как обрабатываем их на нашем сайте.',
        'keywords': 'политика конфиденциальности, защита персональных данных, обработка данных, СтройМА',
    })

def cookies_policy(request):
    """Отображение страницы политики использования файлов cookie"""
    return render(request, 'products/cookies_policy.html', {
        'meta_title': 'Политика использования файлов cookie - ООО "СТРОЙМА"',
        'meta_description': 'Политика использования файлов cookie ООО "СТРОЙМА". Узнайте, какие файлы cookie мы используем и как они помогают улучшить работу нашего сайта.',
        'keywords': 'cookies, файлы cookie, политика cookie, куки, СтройМА, конфиденциальность',
    })

def offer(request):
    """Публичная оферта (условия продажи товаров дистанционным способом)."""
    return render(request, 'products/legal/offer.html', {
        'meta_title': 'Публичная оферта - ООО "СТРОЙМА"',
        'meta_description': 'Условия продажи товаров дистанционным способом, порядок оформления заказа, оплаты, доставки, возврата.',
        'keywords': 'публичная оферта, условия продажи, дистанционная торговля, СтройМА',
    })


def payment(request):
    """Информация об оплате."""
    return render(request, 'products/legal/payment.html', {
        'meta_title': 'Оплата - ООО "СТРОЙМА"',
        'meta_description': 'Способы оплаты заказов в интернет-магазине ООО «СТРОЙМА».',
        'keywords': 'оплата, способы оплаты, СтройМА',
    })


def delivery(request):
    """Информация о доставке."""
    return render(request, 'products/legal/delivery.html', {
        'meta_title': 'Доставка - ООО "СТРОЙМА"',
        'meta_description': 'Условия и сроки доставки заказов, самовывоз, стоимость доставки.',
        'keywords': 'доставка, самовывоз, СтройМА',
    })


def returns(request):
    """Информация о возврате и обмене."""
    return render(request, 'products/legal/returns.html', {
        'meta_title': 'Возврат и обмен - ООО "СТРОЙМА"',
        'meta_description': 'Правила возврата и обмена товаров в соответствии с законодательством РФ.',
        'keywords': 'возврат, обмен, защита прав потребителей, СтройМА',
    })

class CatalogView(TemplateView):
    """
    Представление для отображения каталога категорий.
    Использует MPTT для построения дерева категорий.
    """
    template_name = 'products/catalog.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Получаем только корневые категории
        categories = Category.objects.filter(parent=None).order_by('tree_id', 'lft')
        
        # Добавляем метаданные для SEO
        context.update({
            'categories': categories,
            'meta_title': 'Каталог товаров - Строительные материалы',
            'meta_description': 'Полный каталог строительных материалов с удобной навигацией по категориям',
            'og_description': 'Изучите наш каталог строительных материалов. Удобная навигация по категориям с визуальным представлением.',
            **_browser_page_context(self.request),
        })
        return context
