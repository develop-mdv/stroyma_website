from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.base import ContentFile
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from PIL import Image

from products.images import build_variants, image_srcset, image_url, variant_names
from products.management.commands.cleanup_media import Command as CleanupCommand
from products.models import Category, Product


class ResponsiveImageTests(SimpleTestCase):
    def test_portrait_dimensions_srcset_and_idempotent_build(self):
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            photo = BytesIO()
            Image.new('RGB', (480, 960), 'red').save(photo, 'PNG')
            product = Product(name='Photo', price=1)
            product.image.save('portrait.png', ContentFile(photo.getvalue()), save=False)
            original = Path(product.image.path).read_bytes()
            self.assertEqual(build_variants(product.image), 4)
            self.assertEqual(build_variants(product.image), 0)
            self.assertEqual(Path(product.image.path).read_bytes(), original)
            names = variant_names(product.image)
            with Image.open(Path(root) / names[400]) as image:
                self.assertEqual(image.size, (400, 800))
            self.assertIn('400w', image_srcset(product.image))
            self.assertIn('480w', image_srcset(product.image))
            self.assertNotIn('1280w', image_srcset(product.image))
            self.assertIn('.thumbnails/', image_url(product.image))

    def test_missing_and_animated_images_fall_back_to_original(self):
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            product = Product(image='products/missing.jpg', price=1)
            self.assertEqual(image_url(product.image), product.image.url)
            self.assertEqual(image_srcset(product.image), '')
            photo = BytesIO()
            Image.new('RGB', (20, 20), 'red').save(photo, 'GIF')
            product.image.save('animation.gif', ContentFile(photo.getvalue()), save=False)
            self.assertEqual(build_variants(product.image), 0)
            self.assertEqual(image_url(product.image), product.image.url)

    def test_rotated_jpeg_uses_transposed_width_in_srcset(self):
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            photo = BytesIO()
            image = Image.new('RGB', (480, 960), 'red')
            exif = image.getexif()
            exif[274] = 6
            image.save(photo, 'JPEG', exif=exif)
            product = Product(price=1)
            product.image.save('rotated.jpg', ContentFile(photo.getvalue()), save=False)
            build_variants(product.image)
            self.assertIn('800w', image_srcset(product.image))
            self.assertIn('960w', image_srcset(product.image))
            with Image.open(Path(root) / variant_names(product.image)[800]) as derived:
                self.assertEqual(derived.size, (800, 400))


class CatalogPerformanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = Category.objects.create(name='Root', slug='root')
        cls.child = Category.objects.create(name='Child', slug='child', parent=cls.root)
        cls.product = Product.objects.create(name='Visible', slug='visible', price=10)
        cls.product.categories.add(cls.root, cls.child)
        hidden = Product.objects.create(name='Hidden', slug='hidden', price=20, is_published=False)
        hidden.categories.add(cls.child)
        for number in range(12):
            root = Category.objects.create(name=f'Root {number}', slug=f'root-{number}')
            Category.objects.create(name=f'Child {number}', slug=f'child-{number}', parent=root)

    def test_catalog_queries_do_not_grow_with_category_tree(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get('/catalog/')
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 6)
        cards = response.context['visible_categories']
        root = next(card for card in cards if card.pk == self.root.pk)
        # A product attached to both parent and child must count only once.
        self.assertEqual(root.get_total_products_count(), 1)
        with self.assertNumQueries(0):
            self.assertEqual(len(root.get_children()), 1)
            self.assertEqual(root.get_total_products_count(), 1)
            self.assertIsNone(root.display_image)

    def test_cleanup_retains_current_derived_photos(self):
        with TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root):
            photo = BytesIO()
            Image.new('RGB', (600, 400), 'red').save(photo, 'PNG')
            self.product.image.save('source.png', ContentFile(photo.getvalue()), save=True)
            names = variant_names(self.product.image)
            referenced = CleanupCommand()._collect_referenced_relative_paths()
            self.assertTrue(set(names.values()).issubset(referenced))
            self.assertTrue(all((Path(root) / name).exists() for name in names.values()))

    def test_ajax_and_category_counts_remain_correct(self):
        response = self.client.get('/search-ajax/', {'view': 'grid', 'query': 'Visible'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        response = self.client.get(self.root.get_absolute_url())
        self.assertEqual(response.context['products'].paginator.count, 1)
