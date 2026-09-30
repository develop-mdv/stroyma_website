"""Refresh reviewed service text without deleting services or their photos."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stroyma.settings')

import django
django.setup()

from services.content import SERVICE_CONTENT
from services.models import Service


def run():
    for item in SERVICE_CONTENT:
        values = {key: value for key, value in item.items() if key != 'slug'}
        service, created = Service.objects.update_or_create(slug=item['slug'], defaults=values)
        print(f"{'Created' if created else 'Updated'}: {service.title}")


if __name__ == '__main__':
    run()
