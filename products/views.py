import logging
import threading

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Max, Min
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.generic import DetailView, TemplateView
from django_ratelimit.decorators import ratelimit

from .filters import ProductFilter
from .forms import ContactForm, OrderForm, SearchForm
from .models import (
    BaseTexture,
    Cart,
    CartItem,
    Category,
    FacadeColor,
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

def product_list(request):
    form = SearchForm(request.GET)
    products = Product.objects.all()
    min_price = products.aggregate(Min('price'))['price__min'] or 0
    max_price = products.aggregate(Max('price'))['price__max'] or 0

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

    price_min = str(request.GET.get('price_min', min_price))
    price_max = str(request.GET.get('price_max', max_price))
    if price_min and price_min.isdigit():
        products = products.filter(price__gte=int(price_min))
    if price_max and price_max.isdigit():
        products = products.filter(price__lte=int(price_max))

    sort_by = request.GET.get('sort_by', 'name')
    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')

    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'products/product_list.html', {
        'page_obj': page_obj,
        'search_form': form,
        'min_price': int(min_price),
        'max_price': int(max_price),
        'sort_by': sort_by,
        'categories_tree': categories_tree,
        'selected_categories': selected_categories,
    })


@ratelimit(key='ip', rate='30/m', block=True)
def search_ajax(request):
    query = request.GET.get('query', '').lower()
    price_min = request.GET.get('price_min', None)
    price_max = request.GET.get('price_max', None)
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
        products = products[:5]
        return JsonResponse({'products': [{'name': product.name} for product in products]})

    if price_min and price_min.isdigit():
        products = products.filter(price__gte=int(price_min))
    if price_max and price_max.isdigit():
        products = products.filter(price__lte=int(price_max))

    if sort_by == 'price_asc':
        products = products.order_by('price')
    elif sort_by == 'price_desc':
        products = products.order_by('-price')

    paginator = Paginator(products, 12)
    page = paginator.get_page(page_number)

    context = {
        'products': page,
        'sort_by': sort_by,
    }

    results_html = render_to_string('products/search_results.html', context, request=request)
    return JsonResponse({
        'results': results_html,
        'has_next': page.has_next(),
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

def color_selection(request):
    facade_colors = FacadeColor.objects.all()
    base_textures = BaseTexture.objects.all()
    return render(request, 'products/color_selection.html', {
        'facade_colors': facade_colors,
        'base_textures': base_textures,
    })

class CategoryDetailView(DetailView):
    model = Category
    template_name = 'products/category_detail.html'
    context_object_name = 'category'
    paginate_by = 12

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        
        # Получаем все товары из текущей категории и её подкатегорий
        products = Product.objects.filter(
            Q(categories=category) | 
            Q(categories__in=category.get_descendants())
        ).distinct()

        # Глобальные min/max цены для слайдера (до применения фильтров)
        price_range = products.aggregate(Min('price'), Max('price'))
        min_price = int(price_range.get('price__min') or 0)
        max_price = int(price_range.get('price__max') or 0)

        # Применяем фильтры
        self.filterset = ProductFilter(self.request.GET, queryset=products)
        products = self.filterset.qs

        # Сортировка
        sort_by = self.request.GET.get('sort_by', 'name')
        if sort_by == 'price_asc':
            products = products.order_by('price')
        elif sort_by == 'price_desc':
            products = products.order_by('-price')
        else:
            products = products.order_by('name')

        # Добавляем пагинацию
        paginator = Paginator(products, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Получаем выбранные категории
        selected_categories = self.request.GET.getlist('category')
        
        # Добавляем метаданные для SEO
        context.update({
            'products': page_obj,
            'filter': self.filterset,
            'meta_title': f'{category.name} - Каталог товаров',
            'meta_description': category.description or f'Товары категории {category.name}',
            'og_description': f'Просмотрите товары категории {category.name}. {category.description or ""}',
            'subcategories': category.get_children(),
            'breadcrumbs': self.get_breadcrumbs(category),
            'selected_categories': selected_categories,
            'min_price': min_price,
            'max_price': max_price,
            'sort_by': sort_by,
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

@method_decorator(cache_page(60 * 15), name='dispatch')  # Кеширование на 15 минут
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
        })
        return context