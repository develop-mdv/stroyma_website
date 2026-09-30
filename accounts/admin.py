from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin, UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.contrib.auth.models import Permission
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import Q
from .models import LegalAcceptance, UserProfile
from django.utils.html import format_html, format_html_join
from django.urls import reverse


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(LegalAcceptance)
class LegalAcceptanceAdmin(admin.ModelAdmin):
    list_display = ('kind', 'version', 'accepted_at', 'source_path', 'user', 'order')
    list_filter = ('kind', 'version')
    search_fields = ('subject', 'user__username')
    readonly_fields = ('kind', 'version', 'document_snapshot', 'accepted_at', 'source_path',
                       'subject', 'user', 'order')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)


COMMON_ROLE_MODELS = (
    ('products', 'product'),
    ('products', 'productimage'),
    ('products', 'category'),
    ('products', 'order'),
    ('services', 'service'),
    ('services', 'servicephoto'),
    ('auth', 'user'),
)


def common_permission_filter():
    query = Q(pk__in=[])
    for app_label, model in COMMON_ROLE_MODELS:
        model_query = Q(content_type__app_label=app_label, content_type__model=model)
        if (app_label, model) == ('auth', 'user'):
            model_query &= ~Q(codename='delete_user')
        query |= model_query
    return query


class ReadablePermissionField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, permission):
        model = permission.content_type.model_class()
        model_name = str(model._meta.verbose_name_plural) if model else permission.content_type.model
        action = permission.codename.split('_', 1)[0]
        action_name = {'view': 'Просмотр', 'add': 'Добавление', 'change': 'Изменение', 'delete': 'Удаление'}.get(action)
        if action_name:
            return f'{model_name} — {action_name}'
        return f'{model_name} — {permission.name}'


class StoreRoleForm(forms.ModelForm):
    common_permissions = ReadablePermissionField(
        queryset=Permission.objects.none(), required=False,
        label='Права менеджера', widget=forms.CheckboxSelectMultiple,
    )
    other_permissions = ReadablePermissionField(
        queryset=Permission.objects.none(), required=False,
        label='Системные и дополнительные права',
        widget=FilteredSelectMultiple('Системные и дополнительные права', False),
    )

    class Meta:
        model = Group
        fields = ('name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        common_query = common_permission_filter()
        self.fields['common_permissions'].queryset = Permission.objects.filter(common_query).select_related('content_type').order_by('content_type__app_label', 'content_type__model', 'codename')
        self.fields['other_permissions'].queryset = Permission.objects.exclude(common_query).select_related('content_type').order_by('content_type__app_label', 'content_type__model', 'codename')
        if self.instance.pk:
            selected = self.instance.permissions.values_list('pk', flat=True)
            self.fields['common_permissions'].initial = list(self.fields['common_permissions'].queryset.filter(pk__in=selected).values_list('pk', flat=True))
            self.fields['other_permissions'].initial = list(self.fields['other_permissions'].queryset.filter(pk__in=selected).values_list('pk', flat=True))

    def _save_m2m(self):
        super()._save_m2m()
        selected = set(self.cleaned_data['common_permissions'].values_list('pk', flat=True))
        selected.update(self.cleaned_data['other_permissions'].values_list('pk', flat=True))
        self.instance.permissions.set(selected)


@admin.register(User)
class StoreUserAdmin(BaseUserAdmin):
    """Managers may edit customer details but cannot grant staff or model rights."""

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff')
    list_filter = ('is_staff', 'is_active', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset if request.user.is_superuser else queryset.filter(is_staff=False, is_superuser=False)

    def get_fieldsets(self, request, obj=None):
        if request.user.is_superuser or obj is None:
            return super().get_fieldsets(request, obj)
        return (
            (None, {'fields': ('username', 'password')}),
            ('Контакты', {'fields': ('first_name', 'last_name', 'email')}),
            ('Доступ покупателя', {'fields': ('is_active',)}),
        )

    def has_view_permission(self, request, obj=None):
        return super().has_view_permission(request, obj) and (
            obj is None or request.user.is_superuser or not obj.is_staff
        )

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (
            obj is None or request.user.is_superuser or not obj.is_staff
        )

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)


@admin.register(Group)
class StoreRoleAdmin(BaseGroupAdmin):
    """Role definitions and permission grants remain under superuser control."""

    form = StoreRoleForm
    filter_horizontal = ()
    list_display = ('name', 'users_count', 'permissions_count')
    search_fields = ('name',)
    fieldsets = (
        ('Роль', {'fields': ('name',)}),
        ('Основные права', {
            'fields': ('common_permissions',),
            'description': 'Отметьте только нужные действия. Для каталога обычно достаточно просмотра и изменения товаров; для заказов — просмотра и изменения заказов.',
        }),
        ('Дополнительные права', {
            'fields': ('other_permissions',),
            'classes': ('collapse',),
            'description': 'Служебные разрешения. Открывайте только если они действительно нужны.',
        }),
    )

    @admin.display(description='Сотрудников')
    def users_count(self, obj):
        return obj.user_set.filter(is_staff=True).count()

    @admin.display(description='Разрешений')
    def permissions_count(self, obj):
        return obj.permissions.count()

    def has_module_permission(self, request):
        return request.user.is_superuser and super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_view_permission(request, obj)

    def has_add_permission(self, request):
        return request.user.is_superuser and super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_delete_permission(request, obj)

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
            'fields': ('email_confirmed', 'last_visit', 'bio')
        }),
        ('Заказы', {
            'fields': ('orders_history',)
        }),
    )

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(super().get_fieldsets(request, obj))
        if not request.user.has_perm('products.view_order'):
            fieldsets = [section for section in fieldsets if section[0] != 'Заказы']
        return fieldsets

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        return fields + ['user'] if obj is not None else fields

    def get_list_display(self, request):
        fields = list(super().get_list_display(request))
        if not request.user.has_perm('products.view_order'):
            fields.remove('orders_count')
        return fields
    
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
