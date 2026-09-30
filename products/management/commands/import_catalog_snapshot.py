"""Import the reviewed 29 September 2026 stock and wholesale price snapshot."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from text_unidecode import unidecode

from products.models import Category, Product


SNAPSHOT = Path(settings.BASE_DIR) / "products" / "data" / "catalog_2026_09_29.json"
PHOTOS = SNAPSHOT.parent / "photos"
ILLUSTRATIONS = SNAPSHOT.parent / "illustrations"


def ascii_slug(value: str, limit: int) -> str:
    return slugify(unidecode(value))[:limit].strip("-")


class Command(BaseCommand):
    help = "Import the reviewed catalog snapshot; existing imported stock is preserved unless --reset-stocks is used."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Write catalog data to the database")
        parser.add_argument("--reset-stocks", action="store_true",
                            help="Reset already imported stock to the dated export; use only for a deliberate stocktake")

    def handle(self, *args, **options):
        if not SNAPSHOT.is_file():
            raise CommandError(f"Missing catalog snapshot: {SNAPSHOT}")
        data = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        items = data["products"]
        keys = [item["source_key"] for item in items]
        if len(items) != 135 or len(set(keys)) != len(keys):
            raise CommandError("Expected 135 products with unique source keys")
        for item in items:
            if Decimal(item["stock"]) < 0 or Decimal(item["price"]) < 0:
                raise CommandError(f"Negative quantity or price at row {item['stock_row']}")
            root, leaf = item["category"]
            if leaf not in data["categories"].get(root, []):
                raise CommandError(f"Unregistered category at row {item['stock_row']}")
        photos = sum((PHOTOS / f"catalog-row-{item['stock_row']}.webp").is_file() for item in items)
        illustrations = sum((ILLUSTRATIONS / f"catalog-row-{item['stock_row']}.webp").is_file()
                            for item in items if not (PHOTOS / f"catalog-row-{item['stock_row']}.webp").is_file())
        if photos + illustrations != len(items):
            raise CommandError(f"Missing images for {len(items) - photos - illustrations} catalog products")
        unpriced = sum(Decimal(item["price"]) == 0 for item in items)
        self.stdout.write(f"Snapshot: {len(items)} products, {photos} local photos, "
                          f"{illustrations} labeled illustrations, {unpriced} without a price")
        if not options["apply"]:
            self.stdout.write("Dry run complete. Use --apply to import.")
            return

        created = updated = attached = 0
        with transaction.atomic():
            categories = {}
            for root_name, children in data["categories"].items():
                root_slug = ascii_slug(root_name, 100)
                root, _ = Category.objects.get_or_create(
                    slug=root_slug,
                    defaults={"name": root_name, "description": f"{root_name} для строительства и ремонта."},
                )
                categories[(root_name,)] = root
                for child_name in children:
                    slug = ascii_slug(f"{root_name}-{child_name}", 100)
                    child, _ = Category.objects.get_or_create(
                        slug=slug,
                        defaults={"name": child_name, "parent": root,
                                  "description": f"{child_name}: товары для строительства и ремонта."},
                    )
                    categories[(root_name, child_name)] = child

            for item in items:
                row = item["stock_row"]
                product = Product.objects.filter(source_key=item["source_key"]).first()
                is_new = product is None
                if is_new:
                    product = Product(source_key=item["source_key"])
                    product.slug = ascii_slug(item["name"], 235) or "tovar"
                    product.slug = f"{product.slug}-{row}"
                    product.stock = Decimal(item["stock"])
                    product.rating = 0
                elif options["reset_stocks"]:
                    product.stock = Decimal(item["stock"])
                product.name = item["name"]
                product.description = item["description"]
                product.price = Decimal(item["price"])
                product.unit = item["unit"]
                product.meta_title = item["name"][:255]
                product.meta_description = item["description"][:255]
                photo = PHOTOS / f"catalog-row-{row}.webp"
                illustration = ILLUSTRATIONS / f"catalog-row-{row}.webp"
                missing_image = not product.image or not product.image.storage.exists(product.image.name)
                if photo.is_file() and (missing_image or product.is_illustration):
                    with photo.open("rb") as source:
                        product.image.save(f"catalog-2026-row-{row}.webp", File(source), save=False)
                    attached += 1
                elif not photo.is_file() and missing_image:
                    with illustration.open("rb") as source:
                        product.image.save(f"catalog-illustration-row-{row}.webp", File(source), save=False)
                    attached += 1
                product.full_clean()
                product.save()
                root, leaf = item["category"]
                product.categories.set([categories[(root,)], categories[(root, leaf)]])
                created += int(is_new)
                updated += int(not is_new)
        self.stdout.write(self.style.SUCCESS(
            f"Imported: {created} created, {updated} updated, {attached} images attached."
        ))
