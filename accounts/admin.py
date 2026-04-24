from django.contrib import admin
from .models import UserProfile
from django.utils.html import format_html, format_html_join
from django.urls import reverse

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
    
    STATUS_COLORS = {
        'new': '#03A9F4',
        'pending': '#FFC107',
        'processing': '#2196F3',
        'shipped': '#9C27B0',
        'delivered': '#8BC34A',
        'completed': '#4CAF50',
        'cancelled': '#F44336',
    }

    def orders_history(self, obj):
        orders = list(obj.get_last_orders(10))
        if not orders:
            return 'Нет заказов'

        rows = []
        for order in orders:
            color = self.STATUS_COLORS.get(order.status, '#000')
            url = reverse('admin:products_order_change', args=[order.id])
            rows.append((
                order.id,
                order.created_at.strftime('%d.%m.%Y %H:%M'),
                color,
                order.get_status_display(),
                order.total_cost,
                url,
            ))

        rows_html = format_html_join(
            '',
            (
                '<tr>'
                '<td style="border:1px solid #ddd; padding:8px;">{}</td>'
                '<td style="border:1px solid #ddd; padding:8px;">{}</td>'
                '<td style="border:1px solid #ddd; padding:8px; color:{}; font-weight:bold;">{}</td>'
                '<td style="border:1px solid #ddd; padding:8px;">{} ₽</td>'
                '<td style="border:1px solid #ddd; padding:8px;">'
                '<a href="{}" class="button">Просмотр</a></td>'
                '</tr>'
            ),
            rows,
        )

        all_orders_url = reverse('admin:products_order_changelist') + f'?user__id__exact={obj.user.id}'
        return format_html(
            '<table style="width:100%; border-collapse: collapse;">'
            '<tr>'
            '<th style="border:1px solid #ddd; padding:8px;">ID</th>'
            '<th style="border:1px solid #ddd; padding:8px;">Дата</th>'
            '<th style="border:1px solid #ddd; padding:8px;">Статус</th>'
            '<th style="border:1px solid #ddd; padding:8px;">Сумма</th>'
            '<th style="border:1px solid #ddd; padding:8px;">Действие</th>'
            '</tr>'
            '{}'
            '</table>'
            '<div style="margin-top:10px;"><a href="{}" class="button">Все заказы пользователя</a></div>',
            rows_html,
            all_orders_url,
        )
    orders_history.short_description = 'История заказов'