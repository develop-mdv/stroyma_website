from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Order, OrderItem, Cart, CartItem, FacadeColor, BaseTexture, Category
from .forms import OrderForm, SearchForm, ContactForm
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q, Max, Min
from django.contrib import messages
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.utils.html import strip_tags
import logging
from django.views.generic import ListView, DetailView
from .filters import ProductFilter

logger = logging.getLogger(__name__)
EMAIL_TO_SEND = 'ivanverovitch@yandex.ru'

def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
        # Синхронизация сессии с базой данных при входе
        session_cart = request.session.get('cart', {})
        for product_id, quantity in session_cart.items():
            product = get_object_or_404(Product, pk=product_id)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            cart_item.quantity = quantity
            cart_item.save()
        request.session['cart'] = {}
    else:
        cart = None
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

def search_ajax(request):
    query = request.GET.get('query', '').lower()
    price_min = request.GET.get('price_min', None)
    price_max = request.GET.get('price_max', None)
    sort_by = request.GET.get('sort_by', 'name')
    page_number = request.GET.get('page', 1)
    autocomplete = request.GET.get('autocomplete', False)
    
    # Получаем все параметры category из запроса
    selected_categories = request.GET.getlist('category')
    print(f"Request GET: {request.GET}")  # Отладочная информация
    print(f"Selected categories: {selected_categories}")  # Отладочная информация

    products = Product.objects.all()

    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    if selected_categories:
        # Получаем только выбранные категории
        categories_to_filter = []
        for category_id in selected_categories:
            try:
                category = Category.objects.get(id=category_id)
                categories_to_filter.append(category)
            except Category.DoesNotExist:
                print(f"Category not found: {category_id}")  # Отладочная информация
                continue
        
        print(f"Categories to filter: {[cat.id for cat in categories_to_filter]}")  # Отладочная информация
        
        # Создаем Q-объект для каждой категории
        category_filters = Q()
        for category in categories_to_filter:
            category_filters |= Q(categories=category)
        
        # Применяем фильтр с использованием OR
        products = products.filter(category_filters).distinct()
        print(f"SQL Query: {products.query}")  # Отладочная информация
        print(f"Filtered products count: {products.count()}")  # Отладочная информация

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

    results_html = render_to_string('products/search_results.html', context)
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

def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    quantity = int(request.POST.get('quantity', 1))

    if request.user.is_authenticated:
        cart = get_or_create_cart(request)
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        cart_item.quantity = quantity if created else cart_item.quantity + quantity
        cart_item.save()
    else:
        cart = request.session.get('cart', {})
        if str(product.pk) in cart:
            cart[str(product.pk)] += quantity
        else:
            cart[str(product.pk)] = quantity
        request.session['cart'] = cart

    return redirect('view_cart')

def update_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
            if quantity <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Количество должно быть больше 0.',
                    'current_quantity': 1
                })

            if quantity > product.stock:
                return JsonResponse({
                    'success': False,
                    'message': f'Доступно только {product.stock} шт.',
                    'current_quantity': product.stock
                })

            if request.user.is_authenticated:
                cart = get_or_create_cart(request)
                cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
                cart_item.quantity = quantity
                cart_item.save()
                total_price = sum(item.product.price * item.quantity for item in CartItem.objects.filter(cart=cart))
            else:
                cart = request.session.get('cart', {})
                cart[str(product.pk)] = quantity
                request.session['cart'] = cart
                total_price = sum(get_object_or_404(Product, pk=pid).price * qty for pid, qty in cart.items())

            item_total_price = product.price * quantity

            return JsonResponse({
                'success': True,
                'item_total_price': float(item_total_price),
                'total_price': float(total_price)
            })
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Недопустимое количество.',
                'current_quantity': 1
            })

    return redirect('view_cart')

def view_cart(request):
    cart_items = []
    total_price = 0

    if request.user.is_authenticated:
        cart = get_or_create_cart(request)
        cart_items = CartItem.objects.filter(cart=cart) if cart else []
        total_price = sum(item.total_price for item in cart_items)
    else:
        cart = request.session.get('cart', {})
        for product_id, quantity in cart.items():
            product = get_object_or_404(Product, pk=product_id)
            total_item_price = product.price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total_price': total_item_price,
            })
            total_price += total_item_price

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
    session_cart = request.session.get('cart', {})
    if request.user.is_authenticated and session_cart:
        cart, created = Cart.objects.get_or_create(user=request.user)
        for product_id, quantity in session_cart.items():
            product = get_object_or_404(Product, pk=product_id)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            cart_item.quantity = quantity
            cart_item.save()
        request.session['cart'] = {}

def checkout(request):
    cart = request.session.get('cart', {}) if not request.user.is_authenticated else get_or_create_cart(request).items.all()
    if not cart:
        return redirect('view_cart')

    cart_items = []
    total_price = 0

    if request.user.is_authenticated:
        for item in cart:
            cart_items.append({
                'product': item.product,
                'quantity': item.quantity,
                'total_price': item.total_price,
            })
            total_price += item.total_price
    else:
        for product_id, quantity in cart.items():
            product = get_object_or_404(Product, pk=product_id)
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'total_price': product.price * quantity,
            })
            total_price += product.price * quantity

    if request.method == 'POST':
        form = OrderForm(request.POST, user=request.user)
        if form.is_valid():
            user_name = form.cleaned_data['first_name']
            user_lastname = form.cleaned_data['last_name']
            user_email = form.cleaned_data['email']
            user_phone = form.cleaned_data['phone']
            delivery_address = form.cleaned_data['address']

            order = Order.objects.create(
                user=request.user if request.user.is_authenticated else None,
                status='pending'
            )

            if request.user.is_authenticated:
                for item in cart:
                    OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)
                    item.delete()  # Удаляем из корзины после оформления
            else:
                for product_id, quantity in cart.items():
                    product = get_object_or_404(Product, pk=product_id)
                    OrderItem.objects.create(order=order, product=product, quantity=quantity)

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
                if not request.user.is_authenticated:
                    request.session['cart'] = {}
                messages.success(request, 'Спасибо! Заказ отправлен менеджеру. С вами свяжутся.')
                return redirect('checkout_success')
            except Exception as e:
                logger.error(f'Ошибка при отправке email: {e}')
                messages.error(request, f'Произошла ошибка при отправке заказа: {e}')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = OrderForm(user=request.user)

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

def color_selection(request):
    facade_colors = FacadeColor.objects.all()
    base_textures = BaseTexture.objects.all()
    return render(request, 'products/color_selection.html', {
        'facade_colors': facade_colors,
        'base_textures': base_textures,
    })

class ProductListView(ListView):
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.all()
        self.filterset = ProductFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['filter'] = self.filterset
        return context

class CategoryDetailView(DetailView):
    model = Category
    template_name = 'products/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.get_object()
        products = Product.objects.filter(
            Q(categories=category) | 
            Q(categories__in=category.get_descendants())
        ).distinct()
        
        self.filterset = ProductFilter(self.request.GET, queryset=products)
        context['products'] = self.filterset.qs
        context['filter'] = self.filterset
        return context

def get_subcategories(request):
    category_id = request.GET.get('category_id')
    if category_id:
        subcategories = Category.objects.filter(parent_id=category_id)
        data = [{'id': cat.id, 'name': cat.name} for cat in subcategories]
        return JsonResponse({'subcategories': data})
    return JsonResponse({'subcategories': []})

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