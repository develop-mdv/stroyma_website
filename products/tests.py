from io import BytesIO, StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from products.models import BaseTexture, Product, ProductImage
from products.utils import compress_image_field_if_needed


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
