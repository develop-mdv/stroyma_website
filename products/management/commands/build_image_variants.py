"""Build smaller display copies without changing originals or database rows."""
from django.apps import apps
from django.core.management.base import BaseCommand
from products.images import build_variants


class Command(BaseCommand):
    help = 'Build responsive WebP copies of public photos (original files and DB remain intact).'

    def handle(self, *args, **options):
        total = 0
        failures = 0
        for label in ('products.Product', 'products.Category', 'products.ProductImage', 'services.Service', 'services.ServicePhoto'):
            model = apps.get_model(label)
            for obj in model.objects.exclude(image='').exclude(image__isnull=True).iterator():
                try:
                    total += build_variants(obj.image)
                except (OSError, ValueError) as exc:
                    failures += 1
                    self.stderr.write(f'{label} #{obj.pk}: {exc}')
        self.stdout.write(f'Created {total} variants; skipped unreadable sources: {failures}.')
