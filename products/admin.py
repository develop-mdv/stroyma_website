from django.contrib import admin
from mptt.admin import MPTTModelAdmin, DraggableMPTTAdmin
from .models import Product, Category, Order, OrderItem, Cart, CartItem, FacadeColor, BaseTexture, ProductImage
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django.utils.html import format_html
from rangefilter.filters import DateRangeFilter
from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.urls import path
from django.http import HttpResponse, JsonResponse
from django.template.response import TemplateResponse
import csv
from datetime import datetime, timedelta
from django.utils import timezone
import json
from .utils import export_orders_to_pdf, export_orders_csv
from mptt.forms import TreeNodeChoiceField
from django import forms
from colorfield.fields import ColorField
from colorfield.widgets import ColorWidget
from accounts.models import UserProfile
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Ресурсы для импорта/экспорта
class ProductResource(resources.ModelResource):
    """Ресурс для импорта/экспорта товаров через админку"""
    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'stock', 'rating', 'created_at')

class OrderResource(resources.ModelResource):
    """Ресурс для импорта/экспорта заказов через админку"""
    class Meta:
        model = Order
        fields = ('id', 'user__username', 'status', 'created_at')

class ProductImageInline(admin.TabularInline):
    """
    Встроенный редактор изображений товара, позволяющий добавлять/редактировать
    несколько изображений прямо на странице редактирования товара
    """
    model = ProductImage
    extra = 1
    fields = ('image', 'title', 'order')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        """Отображает миниатюру изображения в админке"""
        if obj.image:
            return format_html('<img src="{}" width="100" />', obj.image.url)
        return "-"
    image_preview.short_description = 'Предпросмотр'

@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    """
    Административный интерфейс для категорий с поддержкой MPTT.
    Позволяет перетаскивать категории для изменения их иерархии.
    """
    list_display = ('tree_actions', 'indented_title', 'get_products_count', 'image_preview')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    list_filter = ('parent',)
    mptt_level_indent = 20
    expand_tree_by_default = True
    readonly_fields = ('image_preview',)
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'parent', 'description')
        }),
        ('Изображение', {
            'fields': ('image', 'alt_text', 'image_preview')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )

    # Проверка формы для валидации слага
    form = forms.modelform_factory(
        Category,
        fields='__all__',
        widgets={
            'slug': forms.TextInput(attrs={'class': 'slug-field'}),
        }
    )

    def get_products_count(self, obj):
        """Возвращает количество товаров в категории"""
        return obj.products.count()
    get_products_count.short_description = 'Количество товаров'
    
    def image_preview(self, obj):
        """Отображает миниатюру изображения категории в админке"""
        if obj.image:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover;" />', obj.image.url)
        return "-"
    image_preview.short_description = 'Изображение'

class CategoryFilter(admin.SimpleListFilter):
    """
    Фильтр для товаров по категориям.
    Показывает все категории с указанием их иерархии.
    """
    title = 'Категория'
    parameter_name = 'category'

    def lookups(self, request, model_admin):
        categories = Category.objects.all()
        return [(cat.id, cat.name + (' → ' + cat.parent.name if cat.parent else '')) for cat in categories]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(categories__id=self.value())
        return queryset

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_classes = [ProductResource]
    list_display = ('image_preview', 'name', 'formatted_price', 'stock_status', 'rating', 'created_at')
    list_filter = (CategoryFilter, 'rating', 'created_at')
    search_fields = ('name', 'description')
    filter_horizontal = ('categories',)
    inlines = [ProductImageInline]
    list_display_links = ('image_preview', 'name')
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at', 'image_preview', 'product_popularity')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'description', 'price', 'stock', 'rating', 'categories', 'product_popularity'),
            'description': 'Заполните основные данные о товаре. Поле URL-имя заполнится автоматически.'
        }),
        ('Изображение', {
            'fields': ('image', 'image_preview'),
            'description': 'Загрузите главное изображение товара. Дополнительные фото можно добавить ниже.'
        }),
        ('SEO настройки', {
            'fields': ('meta_title', 'meta_description', 'keywords'),
            'classes': ('collapse',),
            'description': 'Настройки для поисковых систем (необязательно).'
        }),
        ('Служебная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    form = forms.modelform_factory(
        Product,
        fields='__all__',
        widgets={
            'slug': forms.TextInput(attrs={'class': 'slug-field'}),
        }
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="55" height="55" '
                'style="object-fit: cover; border-radius: 8px; '
                'border: 2px solid rgba(255,255,255,0.08);" />', obj.image.url
            )
        return format_html('<span style="color: rgba(255,255,255,0.2);">—</span>')
    image_preview.short_description = 'Фото'

    def formatted_price(self, obj):
        return format_html(
            '<span style="font-weight:600; font-size:14px;">{} ₽</span>',
            f'{obj.price:,.0f}'.replace(',', ' ')
        )
    formatted_price.short_description = 'Цена'
    formatted_price.admin_order_field = 'price'

    def stock_status(self, obj):
        if obj.stock == 0:
            return format_html('<span class="admin-stock-critical">Нет в наличии</span>')
        elif obj.stock <= 5:
            return format_html('<span class="admin-stock-low">{} шт.</span>', obj.stock)
        return format_html('<span class="admin-stock-ok">{} шт.</span>', obj.stock)
    stock_status.short_description = 'Остаток'
    stock_status.admin_order_field = 'stock'
    
    def save_model(self, request, obj, form, change):
        """
        Переопределение метода сохранения для автоматического добавления
        родительских категорий при сохранении товара.
        """
        super().save_model(request, obj, form, change)
        
        # Получаем выбранные категории из формы
        if 'categories' in form.cleaned_data:
            selected_categories = form.cleaned_data['categories']
            # Добавляем категории и их родителей
            obj.add_categories_with_parents(selected_categories)
    
    def product_popularity(self, obj):
        """
        Показывает популярность товара на основе заказов.
        Использует кеширование для оптимизации производительности.
        
        Отображает:
        - Общее количество заказов с товаром
        - Общее количество единиц товара в заказах
        - Заказы за последний месяц
        """
        # Используем кеширование для уменьшения нагрузки на БД
        cache_key = f'product_popularity_{obj.id}'
        popularity_data = cache.get(cache_key)
        
        if popularity_data is None:
            # Если данных нет в кеше, получаем их из базы
            orders_count = OrderItem.objects.filter(product=obj).count()
            
            total_quantity_result = OrderItem.objects.filter(product=obj).aggregate(
                total=Sum('quantity')
            )
            total_quantity = total_quantity_result['total'] or 0
            
            last_month_orders = OrderItem.objects.filter(
                product=obj, 
                order__created_at__gte=timezone.now() - timedelta(days=30)
            ).count()
            
            popularity_data = {
                'orders_count': orders_count,
                'total_quantity': int(total_quantity),  # Преобразуем в int для безопасной сериализации
                'last_month_orders': last_month_orders
            }
            
            # Кешируем на время, указанное в настройках
            try:
                cache.set(cache_key, popularity_data, settings.PRODUCT_CACHE_TIMEOUT)
            except Exception as e:
                # В случае ошибки кеширования просто логируем и продолжаем
                logger.warning('Ошибка кеширования популярности товара: %s', e)
        
        if popularity_data.get('orders_count', 0) > 0:
            return format_html(
                '<div style="background-color: #f9f9f9; padding: 10px; border-radius: 5px;">'
                '<strong>Всего заказов:</strong> {}<br>'
                '<strong>Всего единиц:</strong> {}<br>'
                '<strong>Заказов за 30 дней:</strong> {}'
                '</div>',
                popularity_data.get('orders_count', 0),
                popularity_data.get('total_quantity', 0),
                popularity_data.get('last_month_orders', 0)
            )
        return 'Нет данных о продажах'
    product_popularity.short_description = 'Популярность товара'

class OrderItemInline(admin.TabularInline):
    """
    Встроенный редактор элементов заказа.
    Отображает товары в заказе, их количество и стоимость.
    """
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'get_price', 'get_total')

    def get_price(self, obj):
        """Возвращает цену единицы товара"""
        return obj.product.price
    get_price.short_description = 'Цена'

    def get_total(self, obj):
        """Рассчитывает общую стоимость позиции заказа (цена × количество)"""
        return obj.product.price * obj.quantity
    get_total.short_description = 'Сумма'

@admin.register(Order)
class OrderAdmin(ImportExportModelAdmin):
    resource_classes = [OrderResource]
    list_display = ('order_number', 'user', 'colored_status', 'created_at', 'formatted_total', 'get_items_count')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id', 'user__profile__phone', 'user__email')
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'get_total_cost', 'get_user_info']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    actions = ['export_to_csv', 'export_to_pdf']
    list_per_page = 25
    change_list_template = 'admin/products/order/change_list.html'
    fieldsets = (
        ('Основное', {
            'fields': ('user', 'status'),
            'description': 'Выберите пользователя и установите статус заказа.'
        }),
        ('Информация о клиенте', {
            'fields': ('get_user_info',),
        }),
        ('Детали заказа', {
            'fields': ('get_total_cost', 'created_at', 'updated_at')
        }),
    )

    def order_number(self, obj):
        return format_html('<strong>#{}</strong>', obj.id)
    order_number.short_description = '№'
    order_number.admin_order_field = 'id'

    def colored_status(self, obj):
        status_map = {
            'pending': ('В ожидании', 'admin-badge-pending'),
            'processing': ('Обработка', 'admin-badge-processing'),
            'shipped': ('Доставка', 'admin-badge-shipped'),
            'completed': ('Завершён', 'admin-badge-completed'),
            'canceled': ('Отменён', 'admin-badge-canceled'),
        }
        label, css_class = status_map.get(obj.status, (obj.status, ''))
        return format_html('<span class="admin-badge {}">{}</span>', css_class, label)
    colored_status.short_description = 'Статус'
    colored_status.admin_order_field = 'status'

    def formatted_total(self, obj):
        total = obj.total_cost
        return format_html(
            '<span style="font-weight:600;">{} ₽</span>',
            f'{total:,.0f}'.replace(',', ' ')
        )
    formatted_total.short_description = 'Сумма'

    def get_user_info(self, obj):
        if obj.user:
            try:
                profile = UserProfile.objects.get(user=obj.user)
                return format_html(
                    '<strong>Email:</strong> {}<br>'
                    '<strong>Телефон:</strong> {}<br>'
                    '<strong>Адрес:</strong> {}',
                    obj.user.email,
                    profile.phone or 'Не указан',
                    profile.delivery_address or 'Не указан'
                )
            except UserProfile.DoesNotExist:
                return format_html(
                    '<strong>Email:</strong> {}<br>'
                    '<strong>Профиль не создан</strong>',
                    obj.user.email
                )
        return 'Гость'
    get_user_info.short_description = 'Информация о пользователе'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('export-csv/', self.admin_site.admin_view(self.export_csv_view), name='order_export_csv'),
            path('export-pdf/', self.admin_site.admin_view(self.export_pdf_view), name='order_export_pdf'),
            path('sales-report/', self.admin_site.admin_view(self.sales_report_view), name='sales_report'),
            path('sales-chart-data/', self.admin_site.admin_view(self.sales_chart_data), name='sales_chart_data'),
            path('popular-products/', self.admin_site.admin_view(self.popular_products_view), name='popular_products'),
        ]
        return custom_urls + urls

    def export_csv_view(self, request):
        """Экспортирует все заказы в CSV"""
        orders = self.get_queryset(request)
        return export_orders_csv(orders)

    def export_pdf_view(self, request):
        """Экспортирует все заказы в PDF"""
        orders = self.get_queryset(request)
        pdf = export_orders_to_pdf(orders)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="orders_{timezone.now().strftime("%Y%m%d%H%M%S")}.pdf"'
        response.write(pdf)
        
        return response

    def export_to_csv(self, request, queryset):
        """Экспортирует выбранные заказы в CSV"""
        return export_orders_csv(queryset)
    export_to_csv.short_description = "Экспорт выбранных заказов в CSV"

    def export_to_pdf(self, request, queryset):
        """Экспортирует выбранные заказы в PDF"""
        pdf = export_orders_to_pdf(queryset)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="orders_{timezone.now().strftime("%Y%m%d%H%M%S")}.pdf"'
        response.write(pdf)
        
        return response
    export_to_pdf.short_description = "Экспорт выбранных заказов в PDF"

    def get_total_cost(self, obj):
        return obj.total_cost
    get_total_cost.short_description = 'Сумма заказа'

    def get_items_count(self, obj):
        return obj.items.count()
    get_items_count.short_description = 'Товаров'

    def sales_report_view(self, request):
        """
        Представление для генерации и отображения отчета по продажам.
        
        Функция собирает и анализирует данные о продажах за выбранный период:
        - Общее количество заказов
        - Общая сумма продаж
        - Средний чек
        - Статистика по статусам заказов
        - Статистика заказов по дням недели
        - Топ самых продаваемых товаров
        
        Для оптимизации производительности используется кеширование результатов.
        """
        # Получение периода из GET-параметра или установка значения по умолчанию
        days = int(request.GET.get('days', 30))
        period_start = timezone.now() - timedelta(days=days)
        
        context = dict(
            # Include common variables for rendering the admin template
            self.admin_site.each_context(request),
            title="Отчет по продажам",
            days=days,
            opts=self.model._meta,  # Добавляем opts напрямую в контекст
        )
        
        # Кеширование результатов отчета, исключая objects которые нельзя сериализовать
        cache_key = f'sales_report_{days}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            context.update(cached_data)
        else:
            # Общее количество заказов
            total_orders = Order.objects.filter(created_at__gte=period_start).count()
            
            # Общая сумма продаж
            total_sales = sum(order.total_cost for order in Order.objects.filter(created_at__gte=period_start))
            
            # Среднее значение заказа
            avg_order_value = total_sales / total_orders if total_orders > 0 else 0
            
            # Количество заказов по статусам
            status_counts = Order.objects.filter(created_at__gte=period_start).values('status').annotate(count=Count('id'))
            status_data = {
                'pending': 0,
                'processing': 0,
                'shipped': 0,
                'completed': 0,
                'canceled': 0,
            }
            status_display = {
                'pending': 'В ожидании',
                'processing': 'Обработка',
                'shipped': 'Доставляется',
                'completed': 'Завершен',
                'canceled': 'Отменен',
            }
            
            for item in status_counts:
                status_data[item['status']] = item['count']
            
            # Преобразуем статусы в более читаемый формат для отображения
            status_display_data = [(status_display[k], v) for k, v in status_data.items()]
            
            # Заказы по дням недели
            weekday_orders = Order.objects.filter(created_at__gte=period_start).annotate(
                weekday=F('created_at__week_day')
            ).values('weekday').annotate(count=Count('id')).order_by('weekday')
            
            weekday_data = [0] * 7  # Пн, Вт, Ср, Чт, Пт, Сб, Вс
            for item in weekday_orders:
                # PostgreSQL: 1 - Воскресенье, 7 - Суббота
                # Django: 1 - Воскресенье, 7 - Суббота
                # Мы хотим: 0 - Пн, 6 - Вс
                weekday_idx = item['weekday'] % 7 - 2  # Преобразование
                if weekday_idx < 0:
                    weekday_idx += 7
                weekday_data[weekday_idx] = item['count']
            
            # Топ-10 самых продаваемых товаров - преобразуем в список словарей для безопасного кеширования
            top_products_query = (
                OrderItem.objects
                .filter(order__created_at__gte=period_start)
                .values('product__name')
                .annotate(total_sales=Sum(F('quantity') * F('product__price')))
                .annotate(quantity=Sum('quantity'))
                .order_by('-total_sales')[:10]
            )
            
            # Преобразуем в список словарей для безопасного кеширования
            top_products = [
                {
                    'product__name': item['product__name'],
                    'total_sales': float(item['total_sales']),  # Преобразуем Decimal в float для сериализации
                    'quantity': item['quantity']
                } 
                for item in top_products_query
            ]
            
            # Сохраняем данные в кеш на время из настроек
            cached_data = {
                'total_orders': total_orders,
                'total_sales': float(total_sales),  # Преобразуем Decimal в float для сериализации
                'avg_order_value': float(avg_order_value),  # Преобразуем Decimal в float
                'status_data': status_display_data,
                'weekday_data': weekday_data,
                'top_products': top_products,
                # opts не будем кешировать, так как он содержит несериализуемые объекты Django
            }
            
            cache.set(cache_key, cached_data, settings.DATA_CACHE_TIMEOUT)  # Кешируем на время из настроек
            context.update(cached_data)
        
        return TemplateResponse(request, "admin/products/order/sales_report.html", context)
    
    def sales_chart_data(self, request):
        """
        API для получения данных графика продаж.
        
        Возвращает данные для построения графиков в формате JSON:
        - При периоде до 31 дня - данные по дням
        - При периоде до 90 дней - данные по неделям
        - При периоде более 90 дней - данные по месяцам
        
        Для оптимизации используется кеширование результатов.
        """
        try:
            days = int(request.GET.get('days', 30))
            
            # Кеширование данных для графика
            cache_key = f'sales_chart_data_{days}'
            chart_data = cache.get(cache_key)
            
            if chart_data:
                return JsonResponse(chart_data)
                
            period_start = timezone.now() - timedelta(days=days)
            
            if days <= 31:  # Если период меньше месяца, показываем данные по дням
                # Формируем даты для диапазона
                dates = [(period_start + timedelta(days=i)).date() for i in range(days)]
                
                # Подготавливаем структуру для данных по дням
                sales_by_date = {date: 0 for date in dates}
                count_by_date = {date: 0 for date in dates}
                
                # Получаем количество заказов по дням
                order_counts = Order.objects.filter(
                    created_at__gte=period_start
                ).annotate(
                    date=TruncDay('created_at')
                ).values('date').annotate(
                    count=Count('id')
                )
                
                # Заполняем данные о количестве заказов
                for item in order_counts:
                    if item['date'] and item['date'].date() in count_by_date:
                        count_by_date[item['date'].date()] = item['count']
                
                # Получаем данные о продажах по дням
                orders = Order.objects.filter(created_at__gte=period_start)
                for order in orders:
                    order_date = order.created_at.date()
                    if order_date in sales_by_date:
                        sales_by_date[order_date] += float(order.total_cost)  # Преобразуем в float
                
                # Формируем данные для графика
                chart_data = {
                    'dates': [date.strftime('%d.%m') for date in dates],
                    'sales': [float(sales_by_date.get(date, 0)) for date in dates],  # Преобразуем в float
                    'counts': [count_by_date.get(date, 0) for date in dates],
                    'weekdays': self.get_weekday_data(period_start, days)
                }
            else:  # Если период больше месяца
                if days <= 90:  # Для периода до 3 месяцев группируем по неделям
                    # Формируем данные по неделям
                    chart_data = self.get_weekly_chart_data(period_start, days)
                else:  # Для более длительных периодов группируем по месяцам
                    # Формируем данные по месяцам
                    chart_data = self.get_monthly_chart_data(period_start)
            
            # Кешируем данные на время из настроек
            try:
                cache.set(cache_key, chart_data, settings.DATA_CACHE_TIMEOUT)
            except Exception as e:
                logger.warning('Ошибка кеширования данных графика: %s', e)
            
            return JsonResponse(chart_data)
        except Exception as e:
            logger.exception('Ошибка в sales_chart_data: %s', e)
            return JsonResponse({
                'error': 'Произошла ошибка при получении данных графика продаж',
                'details': str(e),
                'dates': [],
                'sales': [],
                'counts': [],
                'weekdays': [0] * 7,
            }, status=200)
    
    def get_weekday_data(self, period_start, days):
        """Получает данные о количестве заказов по дням недели"""
        weekday_orders = Order.objects.filter(
            created_at__gte=period_start
        ).annotate(
            weekday=F('created_at__week_day')
        ).values('weekday').annotate(
            count=Count('id')
        ).order_by('weekday')
        
        weekday_data = [0] * 7  # Пн, Вт, Ср, Чт, Пт, Сб, Вс
        for item in weekday_orders:
            # Преобразование к порядку дней недели: 0 - Пн, 6 - Вс
            weekday_idx = item['weekday'] % 7 - 2
            if weekday_idx < 0:
                weekday_idx += 7
            weekday_data[weekday_idx] = item['count']
            
        return weekday_data
    
    def get_weekly_chart_data(self, period_start, days):
        """Формирует данные для графика с группировкой по неделям"""
        # Получаем недели в диапазоне дат
        weeks = []
        current = period_start
        end_date = timezone.now()
        
        while current <= end_date:
            week_start = current - timedelta(days=current.weekday())
            weeks.append(week_start)
            current = week_start + timedelta(days=7)
        
        # Получаем количество заказов по неделям
        week_order_counts = Order.objects.filter(
            created_at__gte=period_start
        ).annotate(
            week=TruncWeek('created_at')
        ).values('week').annotate(
            count=Count('id')
        )
        
        # Структура для данных по неделям
        counts_by_week = {week: 0 for week in weeks}
        sales_by_week = {week: 0 for week in weeks}
        
        # Заполняем данные о количестве заказов
        for item in week_order_counts:
            if item['week'] in counts_by_week:
                counts_by_week[item['week']] = item['count']
        
        # Заполняем данные о продажах по неделям
        orders = Order.objects.filter(created_at__gte=period_start)
        for order in orders:
            order_week = order.created_at - timedelta(days=order.created_at.weekday())
            order_week = order_week.replace(hour=0, minute=0, second=0, microsecond=0)
            if order_week in sales_by_week:
                sales_by_week[order_week] += float(order.total_cost)  # Преобразуем в float
        
        # Формируем данные для графика
        return {
            'dates': [week.strftime('Неделя с %d.%m') for week in weeks],
            'sales': [float(sales_by_week.get(week, 0)) for week in weeks],  # Преобразуем в float
            'counts': [counts_by_week.get(week, 0) for week in weeks],
            'weekdays': self.get_weekday_data(period_start, days)
        }
    
    def get_monthly_chart_data(self, period_start):
        """Формирует данные для графика с группировкой по месяцам"""
        # Получаем уникальные месяцы в диапазоне дат
        start_month = period_start.replace(day=1)
        months = []
        current = start_month
        end_date = timezone.now()
        
        while current <= end_date:
            months.append(current)
            # Переходим к следующему месяцу
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        # Получаем количество заказов по месяцам
        month_order_counts = Order.objects.filter(
            created_at__gte=period_start
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        )
        
        # Структура для данных по месяцам
        counts_by_month = {month: 0 for month in months}
        sales_by_month = {month: 0 for month in months}
        
        # Заполняем данные о количестве заказов
        for item in month_order_counts:
            if item['month'] in counts_by_month:
                counts_by_month[item['month']] = item['count']
        
        # Заполняем данные о продажах по месяцам
        orders = Order.objects.filter(created_at__gte=period_start)
        for order in orders:
            order_month = order.created_at.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if order_month in sales_by_month:
                sales_by_month[order_month] += float(order.total_cost)  # Преобразуем в float
        
        # Формируем данные для графика
        return {
            'dates': [month.strftime('%b %Y') for month in months],
            'sales': [float(sales_by_month.get(month, 0)) for month in months],  # Преобразуем в float
            'counts': [counts_by_month.get(month, 0) for month in months],
            'weekdays': self.get_weekday_data(period_start, 365)  # для годового отчета
        }

    def popular_products_view(self, request):
        """API для получения данных о популярных товарах"""
        try:
            days = int(request.GET.get('days', 30))
            
            # Проверяем кеш
            cache_key = f'popular_products_view_{days}'
            chart_data = cache.get(cache_key)
            
            if chart_data:
                return JsonResponse(chart_data)
                
            period_start = timezone.now() - timedelta(days=days)
            
            # Получаем популярные товары только по количеству
            popular_items = OrderItem.objects.filter(
                order__created_at__gte=period_start
            ).values(
                'product__name'
            ).annotate(
                quantity=Sum('quantity')
            ).order_by('-quantity')[:10]
            
            # Формируем данные для графика
            chart_data = {
                'labels': [],
                'quantities': [],
                'sales': []
            }
            
            # Добавляем данные в график
            for item in popular_items:
                product_name = item['product__name']
                quantity = item['quantity']
                
                chart_data['labels'].append(product_name)
                chart_data['quantities'].append(quantity)
                chart_data['sales'].append(float(quantity))  # Для упрощения просто используем то же количество
            
            # Кешируем данные на время из настроек
            try:
                cache.set(cache_key, chart_data, settings.POPULAR_PRODUCTS_TIMEOUT)
            except Exception as e:
                logger.warning('Ошибка кеширования данных популярных товаров: %s', e)
                
            return JsonResponse(chart_data)
        except Exception as e:
            logger.exception('Ошибка в popular_products_view: %s', e)
            return JsonResponse({
                'error': 'Произошла ошибка при получении данных о популярных товарах',
                'details': str(e),
                'labels': [],
                'quantities': [],
                'sales': [],
            }, status=200)


class FacadeColorForm(forms.ModelForm):
    hex_code = forms.CharField(widget=ColorWidget, max_length=7)
    
    class Meta:
        model = FacadeColor
        fields = '__all__'

@admin.register(FacadeColor)
class FacadeColorAdmin(admin.ModelAdmin):
    form = FacadeColorForm
    list_display = ('name', 'hex_code', 'color_preview')
    search_fields = ('name', 'hex_code')
    ordering = ['name']
    
    def color_preview(self, obj):
        return format_html('<div style="width: 30px; height: 30px; background-color: {}; border: 1px solid #ccc;"></div>', obj.hex_code)
    color_preview.short_description = 'Предпросмотр цвета'

@admin.register(BaseTexture)
class BaseTextureAdmin(admin.ModelAdmin):
    list_display = ('name', 'texture_preview')
    search_fields = ('name',)
    ordering = ['name']
    
    def texture_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" />', obj.image.url)
        return "-"
    texture_preview.short_description = 'Предпросмотр'
