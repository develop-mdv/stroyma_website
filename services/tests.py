from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.test import TestCase

from .models import Service, ServicePhoto


class ReviewedCopyMigrationTests(TestCase):
    def test_replaces_known_seed_and_preserves_custom_text_and_photos(self):
        migration = import_module('services.migrations.0008_review_service_copy')
        before, after = migration.REVISIONS[0]
        service = Service.objects.create(**before, image='services/existing.webp')
        service.description = 'Согласованные владельцем условия услуги.'
        service.save(update_fields=['description'])

        migration.update_seed_copy(apps, SimpleNamespace(connection=SimpleNamespace(alias='default')))
        service.refresh_from_db()

        self.assertEqual(service.description, 'Согласованные владельцем условия услуги.')
        self.assertEqual(service.short_description, after['short_description'])
        self.assertEqual(service.image.name, 'services/existing.webp')
        self.assertEqual(service.slug, before['slug'])

        migration.update_seed_copy(apps, SimpleNamespace(connection=SimpleNamespace(alias='default')))
        self.assertEqual(Service.objects.count(), 1)

    def test_relabels_generated_gallery_without_changing_custom_titles(self):
        migration = import_module('services.migrations.0009_label_generated_gallery')
        service = Service.objects.create(title='Колеровка', slug='kolirovka')
        generated = ServicePhoto.objects.create(service=service, title='Пример работы 1',
                                               image='service_photos/gallery_kolirovka_1.webp')
        custom = ServicePhoto.objects.create(service=service, title='Работа по согласованному проекту',
                                            image='service_photos/gallery_kolirovka_2.webp')
        migration.label_generated_gallery(apps, SimpleNamespace(connection=SimpleNamespace(alias='default')))
        generated.refresh_from_db()
        custom.refresh_from_db()
        self.assertEqual(generated.title, 'Иллюстрация услуги 1')
        self.assertEqual(generated.image.name, 'service_photos/gallery_kolirovka_1.webp')
        self.assertEqual(custom.title, 'Работа по согласованному проекту')
