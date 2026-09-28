import csv
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django_ratelimit.core import _get_ip
from django_ratelimit.exceptions import Ratelimited
from axes.helpers import get_client_ip_address

from accounts.forms import CustomUserChangeForm
from accounts.models import UserProfile
from products.models import Order, Product
from products.utils import export_orders_csv
from stroyma.middleware import PrivateResponseMiddleware, RateLimitResponseMiddleware
from stroyma.security import client_ip
from stroyma.views import handler500


class SecurityBoundaryTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer', email='customer@example.com', password='Strong-Original-2026!'
        )
        self.other = User.objects.create_user(
            username='other', email='other@example.com', password='Strong-Original-2026!'
        )
        self.staff = User.objects.create_user(
            username='limited-staff', password='Strong-Original-2026!', is_staff=True
        )
        self.order = Order.objects.create(user=self.customer)

    def test_staff_without_order_permission_cannot_open_order_exports_or_reports(self):
        self.client.force_login(self.staff)
        for name in (
            'admin:order_export_csv', 'admin:order_export_pdf',
            'admin:sales_report', 'admin:sales_chart_data', 'admin:popular_products',
            'admin:products_order_export', 'admin:products_order_import',
            'admin:products_product_export', 'admin:products_product_import',
        ):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 403)
        dashboard = self.client.get(reverse('admin:index'))
        self.assertEqual(dashboard.status_code, 200)
        self.assertNotContains(dashboard, 'customer', status_code=200)
        self.assertNotContains(dashboard, 'Последние заказы', status_code=200)

    def test_staff_with_order_view_permission_can_export(self):
        permission = Permission.objects.get(codename='view_order', content_type__app_label='products')
        self.staff.user_permissions.add(permission)
        self.client.force_login(self.staff)
        response = self.client.get(reverse('admin:order_export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'customer', response.content)

    def test_staff_with_product_write_permissions_can_open_import(self):
        permissions = Permission.objects.filter(
            codename__in=('add_product', 'change_product'), content_type__app_label='products'
        )
        self.staff.user_permissions.add(*permissions)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('admin:products_product_import')).status_code, 200)

    def test_order_csv_escapes_spreadsheet_formula_in_customer_name(self):
        self.customer.username = '=1+1'
        self.customer.save(update_fields=['username'])
        response = export_orders_csv(Order.objects.filter(pk=self.order.pk))
        rows = list(csv.reader(StringIO(response.content.decode('utf-8-sig'))))
        self.assertEqual(rows[1][1], "'=1+1")

    def test_other_customer_order_is_not_visible(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse('order_detail', args=[self.order.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['Cache-Control'], 'no-store, private')
        self.assertIn('noindex', response['X-Robots-Tag'])

    def test_signed_in_customer_cannot_open_or_submit_registration(self):
        self.client.force_login(self.customer)
        self.assertRedirects(self.client.get(reverse('register')), reverse('profile'))
        count = User.objects.count()
        response = self.client.post(reverse('register'), {
            'username': 'second-account', 'email': 'second@example.com',
            'password1': 'Another-Strong-Password-2026!',
            'password2': 'Another-Strong-Password-2026!',
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(User.objects.count(), count)
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)

    def test_checkout_success_requires_fresh_order_in_same_session(self):
        self.assertRedirects(self.client.get(reverse('checkout_success')), reverse('view_cart'))
        session = self.client.session
        session['last_order_id'] = self.order.pk
        session.save()
        self.client.force_login(self.customer)
        response = self.client.get(reverse('checkout_success'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'№ {self.order.pk}')
        self.assertRedirects(self.client.get(reverse('checkout_success')), reverse('view_cart'))

        session = self.client.session
        session['last_order_id'] = self.order.pk
        session.save()
        self.client.force_login(self.other)
        self.assertRedirects(self.client.get(reverse('checkout_success')), reverse('view_cart'))

    def test_cart_removal_needs_post(self):
        product = Product.objects.create(
            name='Тестовый товар', description='Для проверки корзины',
            price=Decimal('100.00'), stock=1, image='products/test.webp',
        )
        session = self.client.session
        session['cart'] = {str(product.pk): 1}
        session.save()
        url = reverse('remove_from_cart', args=[product.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertIn(str(product.pk), self.client.session['cart'])
        strict_client = Client(enforce_csrf_checks=True)
        strict_session = strict_client.session
        strict_session['cart'] = {str(product.pk): 1}
        strict_session.save()
        self.assertEqual(strict_client.post(url).status_code, 403)
        self.assertIn(str(product.pk), strict_client.session['cart'])
        self.assertRedirects(self.client.post(url), reverse('view_cart'))
        self.assertNotIn(str(product.pk), self.client.session['cart'])

    def test_contact_form_has_per_ip_spam_limit(self):
        url = reverse('contact')
        for _ in range(15):
            self.assertEqual(self.client.post(url, {}, REMOTE_ADDR='203.0.113.171').status_code, 200)
        self.assertEqual(self.client.post(url, {}, REMOTE_ADDR='203.0.113.171').status_code, 429)

    def test_password_reset_has_case_insensitive_email_limit(self):
        url = reverse('password_reset')
        for address in ('Target@example.invalid', 'target@example.invalid', 'TARGET@example.invalid'):
            self.assertEqual(self.client.post(url, {'email': address}, REMOTE_ADDR='203.0.113.173').status_code, 302)
        self.assertEqual(
            self.client.post(url, {'email': 'target@example.invalid'}, REMOTE_ADDR='203.0.113.173').status_code,
            429,
        )

    def test_search_rejects_sql_like_and_oversized_filter_values(self):
        Product.objects.create(
            name='Безопасный товар', slug='safe-product', description='Обычное описание',
            price=Decimal('100.00'), stock=1, image='products/test.webp',
        )
        url = reverse('search_ajax')
        response = self.client.get(url, {
            'query': "' OR 1=1 --", 'category': '1 OR 1=1',
        }, REMOTE_ADDR='203.0.113.172')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 0)
        response = self.client.get(url, {
            'view': 'grid', 'category': '9' * 5000,
            'price_min': '9' * 5000, 'scope': '9' * 5000,
        }, REMOTE_ADDR='203.0.113.172')
        self.assertEqual(response.status_code, 200)

    def test_account_get_actions_have_no_side_effect(self):
        profile = UserProfile.objects.create(user=self.customer)
        original_token = profile.confirmation_token
        self.client.force_login(self.customer)
        logout_get = self.client.get(reverse('logout'))
        self.assertEqual(logout_get.status_code, 405)
        self.assertIn(b'405', logout_get.content)
        self.assertEqual(self.client.get(reverse('resend_confirmation')).status_code, 405)
        profile.refresh_from_db()
        self.assertEqual(profile.confirmation_token, original_token)
        self.assertTrue(self.client.get(reverse('profile')).wsgi_request.user.is_authenticated)
        with patch('accounts.views._send_confirmation_email', return_value=True):
            self.assertEqual(self.client.post(reverse('resend_confirmation')).status_code, 302)
        profile.refresh_from_db()
        self.assertNotEqual(profile.confirmation_token, original_token)

    def test_profile_change_requires_password_and_revalidates_email(self):
        profile = UserProfile.objects.create(user=self.customer, email_confirmed=True)
        original_token = profile.confirmation_token
        data = {
            'username': self.customer.username, 'first_name': '', 'last_name': '',
            'email': 'new@example.com', 'phone': '', 'delivery_address': '',
            'current_password': '', 'new_password': '', 'new_password_confirm': '',
        }
        form = CustomUserChangeForm(data, instance=self.customer)
        self.assertFalse(form.is_valid())
        self.assertIn('current_password', form.errors)

        self.customer.refresh_from_db()
        data['current_password'] = 'Strong-Original-2026!'
        form = CustomUserChangeForm(data, instance=self.customer)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        profile.refresh_from_db()
        self.assertFalse(profile.email_confirmed)
        self.assertNotEqual(profile.confirmation_token, original_token)

    def test_profile_password_obeys_site_validators(self):
        data = {
            'username': self.customer.username, 'first_name': '', 'last_name': '',
            'email': self.customer.email, 'phone': '', 'delivery_address': '',
            'current_password': 'Strong-Original-2026!',
            'new_password': '123', 'new_password_confirm': '123',
        }
        form = CustomUserChangeForm(data, instance=self.customer)
        self.assertFalse(form.is_valid())
        self.assertIn('new_password', form.errors)

    def test_password_change_keeps_current_session(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse('edit_profile'), {
            'username': self.customer.username, 'first_name': '', 'last_name': '',
            'email': self.customer.email, 'phone': '', 'delivery_address': '',
            'current_password': 'Strong-Original-2026!',
            'new_password': 'Another-Strong-Password-2026!',
            'new_password_confirm': 'Another-Strong-Password-2026!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)

    def test_error_pages_are_generic_and_rate_limit_is_429(self):
        request = RequestFactory().get('/missing/')
        response = handler500(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn(b'500', response.content)
        self.assertNotIn(b'Traceback', response.content)
        limited = RateLimitResponseMiddleware(lambda req: None).process_exception(request, Ratelimited())
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited['Cache-Control'], 'no-store, private')
        with patch('django_ratelimit.decorators.is_ratelimited', return_value=True):
            response = self.client.get(reverse('search_ajax'))
        self.assertEqual(response.status_code, 429)
        self.assertIn(b'429', response.content)

        with override_settings(DEBUG=True):
            response = self.client.get('/this-security-check-missing/')
        self.assertEqual(response.status_code, 404)
        self.assertIn(b'404', response.content)
        self.assertNotIn(b'Page not found at', response.content)

        response = PrivateResponseMiddleware(
            lambda req: HttpResponse('Traceback and secret', status=500)
        )(RequestFactory().get('/'))
        self.assertEqual(response.status_code, 500)
        self.assertNotIn(b'Traceback', response.content)

    def test_proxy_address_is_trusted_only_in_production_mode(self):
        request = RequestFactory().get('/', REMOTE_ADDR='172.18.0.3', HTTP_X_STROYMA_CLIENT_IP='203.0.113.42')
        self.assertEqual(client_ip(request), '172.18.0.3')
        with override_settings(TRUST_PROXY_CLIENT_IP=True, DEBUG=False):
            self.assertEqual(client_ip(request), '203.0.113.42')
            self.assertEqual(_get_ip(request), '203.0.113.42')
            self.assertEqual(get_client_ip_address(request), '203.0.113.42')
            request.META['HTTP_X_STROYMA_CLIENT_IP'] = 'not-an-ip'
            self.assertEqual(client_ip(request), '172.18.0.3')
