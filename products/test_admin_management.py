from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse

from .models import Order, Product


class ProductPublicationTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name='Скрываемый товар', slug='hidden-product', description='Для проверки',
            price=Decimal('125.00'), stock=Decimal('5'),
        )

    def test_hidden_product_is_absent_from_public_catalog_and_cart(self):
        self.client.post(reverse('add_to_cart', args=[self.product.pk]), {'quantity': '1'})
        self.product.is_published = False
        self.product.save(update_fields=['is_published'])

        self.assertNotContains(self.client.get(reverse('product_list')), self.product.name)
        self.assertNotContains(self.client.get(reverse('catalog')), self.product.name)
        self.assertNotContains(
            self.client.get(reverse('search_ajax'), {'query': self.product.name, 'autocomplete': '1'}),
            self.product.name,
        )
        self.assertEqual(self.client.get(self.product.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(reverse('quick_view', args=[self.product.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('add_to_cart', args=[self.product.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('view_cart')), self.product.name)
        self.assertNotContains(self.client.get(reverse('django.contrib.sitemaps.views.sitemap')), self.product.get_absolute_url())

    def test_admin_actions_hide_and_publish_product(self):
        self.client.force_login(User.objects.create_superuser('owner', 'owner@example.com', 'password'))
        url = reverse('admin:products_product_changelist')
        for action, published in (('hide_products', False), ('publish_products', True)):
            response = self.client.post(url, {
                'action': action,
                '_selected_action': [self.product.pk],
                'index': '0',
            })
            self.assertEqual(response.status_code, 302)
            self.product.refresh_from_db()
            self.assertEqual(self.product.is_published, published)


class AdminAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_superuser('owner', 'owner@example.com', 'password')
        self.customer = User.objects.create_user('buyer', 'buyer@example.com', 'password')

    def test_report_handles_all_current_order_statuses(self):
        Order.objects.create(user=self.customer, status='new')
        Order.objects.create(user=self.customer, status='cancelled')
        self.client.force_login(self.owner)

        response = self.client.get(reverse('admin:sales_report'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Новый')
        self.assertContains(response, 'Отменен')
        self.assertEqual(self.client.get(reverse('admin:sales_report') + '?days=90').status_code, 200)

    def test_manager_cannot_grant_staff_or_role_permissions(self):
        manager = User.objects.create_user('manager', 'manager@example.com', 'password', is_staff=True)
        role = Group.objects.create(name='Менеджер')
        role.permissions.set(Permission.objects.filter(
            content_type__app_label='auth', codename__in=('view_user', 'change_user', 'change_group')
        ))
        manager.groups.add(role)
        self.client.force_login(manager)

        self.assertEqual(self.client.get(reverse('admin:auth_group_changelist')).status_code, 403)
        self.assertNotEqual(self.client.get(reverse('admin:auth_user_change', args=[self.owner.pk])).status_code, 200)
        response = self.client.post(reverse('admin:auth_user_change', args=[self.customer.pk]), {
            'username': self.customer.username,
            'first_name': 'Изменено',
            'last_name': '',
            'email': self.customer.email,
            'is_active': 'on',
            'is_staff': 'on',
            'is_superuser': 'on',
            'groups': [role.pk],
            'user_permissions': [Permission.objects.get(codename='change_group', content_type__app_label='auth').pk],
            '_save': 'Сохранить',
        })
        self.assertEqual(response.status_code, 302)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, 'Изменено')
        self.assertFalse(self.customer.is_staff)
        self.assertFalse(self.customer.is_superuser)
        self.assertFalse(self.customer.groups.exists())
        self.assertFalse(self.customer.user_permissions.exists())

    def test_admin_uses_management_url(self):
        self.assertTrue(reverse('admin:index').startswith('/management-stroyma-7x4/'))
        self.assertEqual(self.client.get('/admin/').status_code, 404)

    def test_role_editor_saves_common_and_extra_permissions(self):
        common = Permission.objects.get(codename='change_product', content_type__app_label='products')
        extra = Permission.objects.get(codename='view_group', content_type__app_label='auth')
        self.client.force_login(self.owner)

        response = self.client.post(reverse('admin:auth_group_add'), {
            'name': 'Контент-менеджер',
            'common_permissions': [common.pk],
            'other_permissions': [extra.pk],
            '_save': 'Сохранить',
        })
        self.assertEqual(response.status_code, 302)
        role = Group.objects.get(name='Контент-менеджер')
        self.assertEqual(set(role.permissions.values_list('pk', flat=True)), {common.pk, extra.pk})
