from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from .models import Product, Category, Order, OrderItem, Cart, CartItem, FacadeColor, BaseTexture, ProductImage
from import_export.admin import ImportExportModelAdmin
from import_export import resources
from django.utils.html import format_html
from rangefilter.filters import DateRangeFilter
from django.db.models import Sum, Count, F, DecimalField
from django.db.models.functions import TruncDay, TruncMonth
from django.urls import path
from django.http import HttpResponse, JsonResponse
from django.template.response import TemplateResponse
import csv
from datetime import datetime, timedelta
from django.utils import timezone
import json
from .utils import export_orders_to_pdf, export_orders_csv

# Ресурсы для импорта/экспорта
class ProductResource(resources.ModelResource):
    class Meta:
        model = Product
        fields = ('id', 'name', 'price', 'stock', 'rating', 'created_at')

class OrderResource(resources.ModelResource):
    class Meta:
        model = Order
        fields = ('id', 'user__username', 'status', 'created_at')

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'title', 'order')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" />', obj.image.url)
        return "-"
    image_preview.short_description = 'Предпросмотр'

@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    list_display = ('name', 'parent', 'slug', 'get_products_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    list_filter = ('parent',)
    mptt_level_indent = 20
    expand_tree_by_default = True

    def get_products_count(self, obj):
        return obj.products.count()
    get_products_count.short_description = 'Количество товаров'

@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_classes = [ProductResource]
    list_display = ('image_preview', 'name', 'price', 'stock', 'rating', 'created_at')
    list_filter = ('categories', 'rating', ('created_at', DateRangeFilter))
    search_fields = ('name', 'description')
    filter_horizontal = ('categories',)
    inlines = [ProductImageInline]
    list_display_links = ('image_preview', 'name')
    list_per_page = 25
    readonly_fields = ('created_at', 'updated_at', 'image_preview')
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'price', 'stock', 'rating', 'categories')
        }),
        ('Изображение', {
            'fields': ('image', 'image_preview')
        }),
        ('Дата и время', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return "-"
    image_preview.short_description = 'Изображение'

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'get_price', 'get_total')

    def get_price(self, obj):
        return obj.product.price
    get_price.short_description = 'Цена'

    def get_total(self, obj):
        return obj.product.price * obj.quantity
    get_total.short_description = 'Сумма'

@admin.register(Order)
class OrderAdmin(ImportExportModelAdmin):
    resource_classes = [OrderResource]
    list_display = ('id', 'user', 'status', 'created_at', 'get_total_cost', 'get_items_count')
    list_filter = ('status', ('created_at', DateRangeFilter))
    search_fields = ('user__username', 'id')
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at', 'get_total_cost']
    inlines = [OrderItemInline]
    date_hierarchy = 'created_at'
    actions = ['export_to_csv', 'export_to_pdf']
    list_per_page = 25
    change_list_template = 'admin/products/order/change_list.html'
    fieldsets = (
        (None, {
            'fields': ('user', 'status')
        }),
        ('Информация о заказе', {
            'fields': ('get_total_cost', 'created_at', 'updated_at')
        }),
    )

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
        """Представление для отчета по продажам"""
        context = dict(
            # Include common variables for rendering the admin template
            self.admin_site.each_context(request),
            title="Отчет по продажам",
        )
        
        # Статистика за последние 30 дней
        period_start = timezone.now() - timedelta(days=30)
        
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
        
        # Топ-5 самых продаваемых товаров
        top_products = (
            OrderItem.objects
            .values('product__name')
            .annotate(total_sales=Sum(F('quantity') * F('product__price')))
            .annotate(quantity=Sum('quantity'))
            .order_by('-total_sales')[:5]
        )
        
        context.update({
            'total_orders': total_orders,
            'total_sales': total_sales,
            'avg_order_value': avg_order_value,
            'status_data': status_display_data,
            'top_products': top_products,
            'opts': self.model._meta,
        })
        
        return TemplateResponse(request, "admin/products/order/sales_report.html", context)
    
    def sales_chart_data(self, request):
        """API для получения данных графика продаж"""
        try:
            days = int(request.GET.get('days', 30))
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
                        sales_by_date[order_date] += order.total_cost
                
                # Формируем данные для графика
                chart_data = {
                    'labels': [date.strftime('%d.%m') for date in dates],
                    'sales': [sales_by_date.get(date, 0) for date in dates],
                    'counts': [count_by_date.get(date, 0) for date in dates],
                }
            else:  # Если период больше месяца, группируем по месяцам
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
                order_counts = Order.objects.filter(
                    created_at__gte=period_start
                ).annotate(
                    month=TruncMonth('created_at')
                ).values('month').annotate(
                    count=Count('id')
                )
                
                # Подготавливаем структуру для данных по месяцам
                counts_by_month = {month: 0 for month in months}
                sales_by_month = {month: 0 for month in months}
                
                # Заполняем данные о количестве заказов
                for item in order_counts:
                    if item['month'] in counts_by_month:
                        counts_by_month[item['month']] = item['count']
                
                # Заполняем данные о продажах по месяцам
                orders = Order.objects.filter(created_at__gte=period_start)
                for order in orders:
                    order_month = order.created_at.replace(day=1)
                    if order_month in sales_by_month:
                        sales_by_month[order_month] += order.total_cost
                
                # Формируем данные для графика
                chart_data = {
                    'labels': [month.strftime('%b %Y') for month in months],
                    'sales': [sales_by_month.get(month, 0) for month in months],
                    'counts': [counts_by_month.get(month, 0) for month in months],
                }
            
            return JsonResponse(chart_data)
        except Exception as e:
            print(f"Ошибка в sales_chart_data: {str(e)}")
            return JsonResponse({
                'error': 'Произошла ошибка при получении данных графика продаж',
                'details': str(e),
                'labels': [],
                'sales': [],
                'counts': [],
            }, status=200)
    
    def popular_products_view(self, request):
        """API для получения данных о популярных товарах"""
        try:
            days = int(request.GET.get('days', 30))
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
            
            return JsonResponse(chart_data)
        except Exception as e:
            print(f"Ошибка в popular_products_view: {str(e)}")
            return JsonResponse({
                'error': 'Произошла ошибка при получении данных о популярных товарах',
                'details': str(e),
                'labels': [],
                'quantities': [],
                'sales': [],
            }, status=200)

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'get_total')
    list_filter = ('order',)
    search_fields = ('product__name',)
    
    def get_total(self, obj):
        return obj.product.price * obj.quantity
    get_total.short_description = 'Сумма'

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_items', 'cart_total')
    search_fields = ('user__username',)

    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Товаров в корзине'
    
    def cart_total(self, obj):
        total = sum(item.product.price * item.quantity for item in obj.items.all())
        return total
    cart_total.short_description = 'Сумма'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'total_price')
    list_filter = ('cart',)
    search_fields = ('product__name',)

@admin.register(FacadeColor)
class FacadeColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code', 'color_preview')
    search_fields = ('name', 'hex_code')
    ordering = ['name']
    
    def color_preview(self, obj):
        return format_html('<div style="background-color: {}; width: 30px; height: 30px; border: 1px solid #000;"></div>', obj.hex_code)
    color_preview.short_description = 'Цвет'

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

# Кастомизация заголовка админки
admin.site.site_header = 'Система управления Stroyma'
admin.site.site_title = 'Stroyma - Панель администратора'
admin.site.index_title = 'Управление системой'