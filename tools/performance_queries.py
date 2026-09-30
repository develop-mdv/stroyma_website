"""Read-only SQL/render timing audit against the configured local database."""
import json
import os
import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stroyma.settings')
import django
django.setup()
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from products.models import Category, Product

client = Client(HTTP_HOST='localhost')
paths = ['/', '/catalog/', '/services/', '/search-ajax/?view=grid']
for obj in [Category.objects.filter(parent=None).first(), Product.published.first()]:
    if obj:
        paths.append(obj.get_absolute_url())
results = []
for route in paths:
    samples = []
    for _ in range(3):
        start = perf_counter()
        with CaptureQueriesContext(connection) as queries:
            response = client.get(route)
        samples.append({'status': response.status_code, 'queries': len(queries),
                        'render_ms': round((perf_counter() - start) * 1000, 1),
                        'sql_ms': round(sum(float(q['time']) for q in queries) * 1000, 1)})
    results.append({'route': route, 'samples': samples})
print(json.dumps(results, ensure_ascii=False, indent=2))
