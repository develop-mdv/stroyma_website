from io import BytesIO, StringIO
import json
from decimal import Decimal
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import DatabaseError
from django.db.models.deletion import ProtectedError
from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.test import RequestFactory
from django.utils import timezone
from PIL import Image

from accounts.models import UserProfile
from products.forms import ColorSelectionRequestForm, OrderForm
from products.models import BaseTexture, Order, OrderNotification, Product, ProductImage
from products.utils import compress_image_field_if_needed
from products.views import color_selection


def image_bytes(format='JPEG'):
    buffer = BytesIO()
    Image.new('RGB', (12, 12), 'red').save(buffer, format=format)
    return buffer.getvalue()


class ImageUploadTests(SimpleTestCase):
    def test_webp_upload_uses_upload_to_once(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            product = Product(name='Тест', price=100)
            product.image = SimpleUploadedFile('photo.jpg', image_bytes(), content_type='image/jpeg')
            compress_image_field_if_needed(product, 'image')
            self.assertEqual(product.image.name, 'products/photo.webp')
            self.assertTrue((Path(media_root) / product.image.name).is_file())

            gallery_image = ProductImage(product=product)
            gallery_image.image = SimpleUploadedFile(
                'detail.jpg', image_bytes(), content_type='image/jpeg'
            )
            compress_image_field_if_needed(gallery_image, 'image')
            self.assertEqual(gallery_image.image.name, 'products/gallery/detail.webp')
            self.assertTrue((Path(media_root) / gallery_image.image.name).is_file())


class OptimizeMediaTests(TestCase):
    def test_shared_source_remains_available_for_all_references(self):
        with TemporaryDirectory() as root:
            media_root = Path(root) / 'media'
            source = media_root / 'base_textures' / 'shared.jpg'
            source.parent.mkdir(parents=True)
            source.write_bytes(image_bytes())

            with override_settings(BASE_DIR=Path(root), MEDIA_ROOT=media_root):
                first = BaseTexture.objects.create(name='Первый', image='base_textures/shared.jpg')
                second = BaseTexture.objects.create(name='Второй', image='base_textures/shared.jpg')

                call_command('optimize_media', '--apply', stdout=StringIO())

                first.refresh_from_db()
                second.refresh_from_db()
                self.assertNotEqual(first.image.name, second.image.name)
                for obj in (first, second):
                    self.assertTrue(obj.image.name.endswith('.webp'))
                    self.assertTrue((media_root / obj.image.name).is_file())
                self.assertTrue(source.is_file())


class ImportTextureTests(TestCase):
    def test_import_stores_only_one_file_at_upload_to_path(self):
        with TemporaryDirectory() as root:
            media_root = Path(root) / 'media'
            json_path = Path(root) / 'textures.json'
            json_path.write_text(json.dumps({
                'textures': [{'name': 'Текстура', 'image_url': 'https://example.com/sample.jpg'}]
            }), encoding='utf-8')

            def fake_download(url, dest):
                dest.write_bytes(image_bytes())
                return dest

            with override_settings(MEDIA_ROOT=media_root), patch(
                'products.management.commands.import_colors_textures.download_texture',
                side_effect=fake_download,
            ):
                call_command('import_colors_textures', '--json-path', str(json_path),
                             stdout=StringIO())

            texture = BaseTexture.objects.get(name='Текстура')
            self.assertEqual(texture.image.name, 'base_textures/sample.jpg')
            self.assertEqual(
                list(media_root.rglob('*.jpg')),
                [media_root / 'base_textures' / 'sample.jpg'],
            )


class ColorSelectionRequestTests(SimpleTestCase):
    def test_phone_is_normalized_and_consent_required(self):
        data = {'name': 'Анна', 'phone': '8 (999) 123-45-67', 'consent': 'on'}
        form = ColorSelectionRequestForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['phone'], '+79991234567')

        data.pop('consent')
        self.assertFalse(ColorSelectionRequestForm(data).is_valid())

    @patch('products.views.send_mail')
    def test_selection_is_in_email(self, send_mail_mock):
        request = RequestFactory().post('/color-selection/', {
            'name': 'Анна',
            'phone': '+79991234567',
            'email': 'anna@example.com',
            'message': 'Площадь 120 м²',
            'facade': 'Камешковая 1,5 мм, Sahara 1 (#F3F2DE)',
            'plinth': 'Мозаичная штукатурка, Tibet 5',
            'consent': 'on',
        })
        with override_settings(ORDER_NOTIFY_EMAIL='orders@example.com'), patch(
            'products.views.render'
        ):
            response = color_selection(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('?sent=1', response['Location'])
        body = send_mail_mock.call_args.args[1]
        self.assertIn('Sahara 1', body)
        self.assertIn('Tibet 5', body)
        self.assertIn('+79991234567', body)

    @patch('products.views.render', return_value=HttpResponse())
    def test_invalid_request_keeps_widget_selection(self, render_mock):
        request = RequestFactory().post('/color-selection/', {
            'name': 'Анна',
            'phone': 'abc',
            'consent': 'on',
            'config_state': json.dumps({
                'facadeTexture': 'koroed3',
                'facadeColor': 'c2',
                'plinthTexture': 'tibet-2',
                'time': 'sunset',
                'landscape': 'full',
            }),
        })
        response = color_selection(request)
        self.assertEqual(response.status_code, 200)
        context = render_mock.call_args.args[2]
        self.assertIn('f=koroed3', context['widget_query'])
        self.assertIn('p=tibet-2', context['widget_query'])
        self.assertIn('t=sunset', context['widget_query'])


class ColorSelectionProfilePrefillTests(TestCase):
    def test_logged_in_user_gets_available_profile_contacts(self):
        user = User.objects.create_user(
            username='ivan', first_name='Иван', last_name='Петров',
            email='ivan@example.com', password='password',
        )
        UserProfile.objects.create(user=user, phone='+79991234567')
        self.client.force_login(user)

        response = self.client.get('/color-selection/')
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form['name'].value(), 'Иван Петров')
        self.assertEqual(form['email'].value(), 'ivan@example.com')
        self.assertEqual(form['phone'].value(), '+79991234567')
        self.assertFalse(form['consent'].value())

    def test_missing_profile_fields_remain_empty(self):
        user = User.objects.create_user(username='new-user', password='password')
        self.client.force_login(user)

        response = self.client.get('/color-selection/')
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form['name'].value(), '')
        self.assertEqual(form['email'].value(), '')
        self.assertEqual(form['phone'].value(), '')
        self.assertFalse(UserProfile.objects.filter(user=user).exists())

    def test_invalid_post_preserves_manually_edited_contacts(self):
        user = User.objects.create_user(
            username='anna', first_name='Анна', email='profile@example.com',
            password='password',
        )
        UserProfile.objects.create(user=user, phone='+79991234567')
        self.client.force_login(user)

        response = self.client.post('/color-selection/', {
            'name': 'Другое имя',
            'email': 'other@example.com',
            'phone': 'invalid',
            'consent': 'on',
        })
        self.assertEqual(response.status_code, 200)
        form = response.context['form']
        self.assertEqual(form['name'].value(), 'Другое имя')
        self.assertEqual(form['email'].value(), 'other@example.com')
        self.assertEqual(form['phone'].value(), 'invalid')


class CheckoutPersistenceTests(TransactionTestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name='Краска', description='Тестовый товар', price=Decimal('125.50'),
            stock=2, image='products/test.webp',
        )
        self.contact = {
            'name': 'Иван Иванов',
            'email': 'ivan@example.com', 'phone': '+79991234567',
            'address': 'Курск, Ленина, 1',
        }

    def set_cart(self, quantity):
        session = self.client.session
        session['cart'] = {str(self.product.pk): quantity}
        session.save()

    def test_checkout_accepts_organization_name(self):
        self.set_cart(1)
        organization = 'ООО «Строительные материалы Курск»'
        response = self.client.post('/checkout/', {**self.contact, 'name': organization})
        self.assertRedirects(response, '/checkout/success/', fetch_redirect_response=False)
        self.assertEqual(Order.objects.get().contact.name, organization)
        with patch('products.management.commands.process_order_notifications.send_mail', return_value=1) as send_mail_mock:
            call_command('process_order_notifications', stdout=StringIO())
        self.assertIn(organization, send_mail_mock.call_args.kwargs['html_message'])

    def test_checkout_requires_name(self):
        self.set_cart(1)
        response = self.client.post('/checkout/', {**self.contact, 'name': ''})
        self.assertEqual(response.status_code, 200)
        self.assertIn('name', response.context['form'].errors)
        self.assertFalse(Order.objects.exists())

    def test_checkout_prefills_full_name_from_account(self):
        user = User.objects.create_user(
            username='buyer', first_name='Иван', last_name='Иванов', password='password',
        )
        form = OrderForm(user=user)
        self.assertEqual(form['name'].value(), 'Иван Иванов')

    def test_order_keeps_price_and_name_after_catalog_change(self):
        self.set_cart(2)
        response = self.client.post('/checkout/', self.contact)
        self.assertRedirects(response, '/checkout/success/', fetch_redirect_response=False)

        order = Order.objects.get()
        item = order.items.get()
        self.assertEqual(item.unit_price, Decimal('125.50'))
        self.assertEqual(item.product_name, 'Краска')
        self.assertEqual(order.total_cost, Decimal('251.00'))
        with self.assertRaises(ProtectedError):
            self.product.delete()
        self.assertEqual(OrderNotification.objects.get(order=order).attempts, 0)

        self.product.price = Decimal('999.00')
        self.product.name = 'Новое название'
        self.product.save()
        item.refresh_from_db()
        self.assertEqual(item.total_price, Decimal('251.00'))
        self.assertEqual(item.product_name, 'Краска')
        self.assertEqual(order.total_cost, Decimal('251.00'))

    def test_insufficient_stock_rolls_back_order_and_keeps_cart(self):
        self.set_cart(3)
        response = self.client.post('/checkout/', self.contact)
        self.assertRedirects(response, '/cart/', fetch_redirect_response=False)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderNotification.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.assertEqual(self.client.session['cart'][str(self.product.pk)], 3)

    def test_database_write_failure_shows_error_and_keeps_cart(self):
        self.set_cart(1)
        with patch('products.views.OrderNotification.objects.create', side_effect=DatabaseError('write failed')):
            response = self.client.post('/checkout/', self.contact)

        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'Не удалось подтвердить заказ', status_code=503)
        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderNotification.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 2)
        self.assertEqual(self.client.session['cart'][str(self.product.pk)], 1)
        self.assertNotIn('last_order_id', self.client.session)

    def test_failed_notification_retries_from_database(self):
        self.set_cart(1)
        self.client.post('/checkout/', self.contact)
        notification = OrderNotification.objects.get()
        with patch('products.management.commands.process_order_notifications.send_mail', side_effect=OSError('SMTP down')), patch('products.management.commands.process_order_notifications.logger'):
            call_command('process_order_notifications', stdout=StringIO())
        notification.refresh_from_db()
        self.assertIsNone(notification.sent_at)
        self.assertEqual(notification.attempts, 1)
        notification.next_attempt_at = timezone.now() - timedelta(seconds=1)
        notification.save(update_fields=['next_attempt_at'])
        self.product.price = Decimal('999.00')
        self.product.save(update_fields=['price'])

        with patch('products.management.commands.process_order_notifications.send_mail', return_value=1) as send_mail_mock:
            call_command('process_order_notifications', stdout=StringIO())
            call_command('process_order_notifications', stdout=StringIO())
        notification.refresh_from_db()
        self.assertIsNotNone(notification.sent_at)
        self.assertEqual(notification.attempts, 2)
        self.assertEqual(send_mail_mock.call_count, 1)
        self.assertIn('125,50', send_mail_mock.call_args.kwargs['html_message'])
