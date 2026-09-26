from io import BytesIO, StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase, override_settings
from django.test import RequestFactory
from PIL import Image

from accounts.models import UserProfile
from products.forms import ColorSelectionRequestForm
from products.models import BaseTexture, Product, ProductImage
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
