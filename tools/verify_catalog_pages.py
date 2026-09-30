"""Check the imported catalog and its rendered product/category pages."""

import json
import os
import re
import sys
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "stroyma.settings")

import django

django.setup()

from django.test import Client
from django.template.defaultfilters import floatformat
from products.models import Category, Product


client = Client(HTTP_HOST="localhost")
products = Product.objects.exclude(source_key__isnull=True).order_by("id")
assert products.count() == 135
assert products.filter(price__gt=0).count() == 123
assert products.exclude(image="").count() == 135
assert sum(product.is_illustration for product in products) == 70
assert Product.objects.exclude(image="").count() == Product.objects.count()
assert Category.objects.count() >= 43

for product in products:
    response = client.get(product.get_absolute_url())
    assert response.status_code == 200, (product.name, response.status_code)
    html = response.content.decode()
    structured = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    data = next((entry for raw in structured if (entry := json.loads(raw)).get('@type') == 'Product'), None)
    assert data is not None, product.name
    assert data["name"] == product.name, (product.name, data["name"])
    assert product.image.storage.exists(product.image.name), product.name
    assert data["image"][0].endswith(product.image.url), product.name
    assert product.image.url in html, product.name
    assert ("Изображение товара — иллюстрация" in html) == product.is_illustration, product.name
    assert ("offers" in data) == product.has_price, product.name
    if product.has_price:
        assert Decimal(data["offers"]["price"]) == product.price, product.name
        assert floatformat(product.price, -2) in html, product.name
    assert ("id=\"add-to-cart-form\"" in html) == bool(
        product.has_price and product.max_order_quantity
    ), product.name

for category in Category.objects.all():
    response = client.get(category.get_absolute_url())
    assert response.status_code == 200, (category.name, response.status_code)
    structured = re.findall(r'<script type="application/ld\+json">(.*?)</script>', response.content.decode(), re.S)
    assert any(json.loads(raw).get('@type') == 'CollectionPage' for raw in structured), category.name

print(f"Verified {products.count()} product and {Category.objects.count()} category pages")
