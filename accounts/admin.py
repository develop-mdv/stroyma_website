from django.contrib import admin
from .models import UserProfile
from django.utils.html import format_html
from django.urls import reverse
from products.models import Order

# Удаляем неработающий inline и используем другой подход
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'email_confirmed', 'last_visit', 'orders_count')
    search_fields = ('user__username', 'user__email', 'phone', 'delivery_address')
    list_filter = ('email_confirmed', 'last_visit')
    readonly_fields = ('user_info', 'confirmation_token', 'email_confirmed', 'last_visit', 'orders_history')
    fieldsets = (
        (None, {
            'fields': ('user', 'user_info')
        }),
        ('Контактная информация', {
            'fields': ('phone', 'delivery_address')
        }),
        ('Аккаунт', {
            'fields': ('email_confirmed', 'confirmation_token', 'last_visit', 'bio')
        }),
        ('Заказы', {
            'fields': ('orders_history',)
        }),
    )
    
    def user_info(self, obj):
        return format_html(
            '<strong>Имя:</strong> {}<br>'
            '<strong>Email:</strong> {}<br>'
            '<strong>Дата регистрации:</strong> {}',
            obj.user.get_full_name() or obj.user.username,
            obj.user.email,
            obj.user.date_joined.strftime('%d.%m.%Y %H:%M')
        )
    user_info.short_description = 'Информация о пользователе'
    
    def orders_count(self, obj):
        count = obj.get_orders().count()
        if count > 0:
            url = reverse('admin:products_order_changelist') + f'?user__id__exact={obj.user.id}'
            return format_html('<a href="{}">{} заказов</a>', url, count)
        return '0 заказов'
    orders_count.short_description = 'Заказы'
    
    def orders_history(self, obj):
        orders = obj.get_last_orders(10)
        if not orders:
            return 'Нет заказов'
        
        html = '<table style="width:100%; border-collapse: collapse;">'
        html += '<tr><th style="border:1px solid #ddd; padding:8px;">ID</th><th style="border:1px solid #ddd; padding:8px;">Дата</th><th style="border:1px solid #ddd; padding:8px;">Статус</th><th style="border:1px solid #ddd; padding:8px;">Сумма</th><th style="border:1px solid #ddd; padding:8px;">Действие</th></tr>'
        
        for order in orders:
            status_colors = {
                'pending': '#FFC107',
                'processing': '#2196F3',
                'shipped': '#9C27B0',
                'completed': '#4CAF50',
                'canceled': '#F44336',
            }
            status_display = {
                'pending': 'В ожидании',
                'processing': 'Обработка',
                'shipped': 'Доставляется',
                'completed': 'Завершен',
                'canceled': 'Отменен',
            }
            color = status_colors.get(order.status, '#000')
            url = reverse('admin:products_order_change', args=[order.id])
            
            html += f'<tr>'
            html += f'<td style="border:1px solid #ddd; padding:8px;">{order.id}</td>'
            html += f'<td style="border:1px solid #ddd; padding:8px;">{order.created_at.strftime("%d.%m.%Y %H:%M")}</td>'
            html += f'<td style="border:1px solid #ddd; padding:8px; color:{color}; font-weight:bold;">{status_display.get(order.status, order.status)}</td>'
            html += f'<td style="border:1px solid #ddd; padding:8px;">{order.total_cost} ₽</td>'
            html += f'<td style="border:1px solid #ddd; padding:8px;"><a href="{url}" class="button">Просмотр</a></td>'
            html += f'</tr>'
        
        html += '</table>'
        
        # Ссылка на все заказы пользователя
        all_orders_url = reverse('admin:products_order_changelist') + f'?user__id__exact={obj.user.id}'
        html += f'<div style="margin-top:10px;"><a href="{all_orders_url}" class="button">Все заказы пользователя</a></div>'
        
        return format_html(html)
    orders_history.short_description = 'История заказов'