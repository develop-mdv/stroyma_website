from stroyma.legal import DOCUMENT_VERSION
"""Guard catalogue pricing and ordering of goods with no recorded stock."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .admin import ProductAdminForm
from .models import Order, Product


class CatalogPricingTests(TestCase):
    def setUp(self):
        self.unpriced = Product.objects.create(
            name="Товар без цены", slug="tovar-bez-tseny", description="Описание",
            price=Decimal("0"), stock=Decimal("3"), rating=0,
        )
        self.priced = Product.objects.create(
            name="Товар с ценой", slug="tovar-s-tsenoy", description="Описание",
            price=Decimal("120.80"), stock=Decimal("2"), unit="мл", rating=0,
        )

    def test_search_keeps_kopecks_and_unit(self):
        response = self.client.get(reverse("search_ajax"), {
            "query": "Товар с ценой", "autocomplete": "1",
        })
        self.assertEqual(response.status_code, 200)
        result = response.json()["products"][0]
        self.assertEqual(result["price"], "120,8")
        self.assertEqual(result["unit"], "мл")

    def test_unpriced_product_remains_searchable(self):
        response = self.client.get(reverse("search_ajax"), {
            "view": "grid", "query": "Товар без цены",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("Товар без цены", response.json()["results"])
        self.assertIn("Цена уточняется", response.json()["results"])

    def test_unpriced_product_is_visible_but_cannot_be_added_to_cart(self):
        detail = self.client.get(self.unpriced.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Цена уточняется")
        self.assertNotContains(detail, 'id="add-to-cart-form"')

        response = self.client.post(
            reverse("add_to_cart", kwargs={"pk": self.unpriced.pk}),
            {"quantity": "1"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(str(self.unpriced.pk), self.client.session.get("cart", {}))

    def test_cart_accepts_quantity_above_stock_but_caps_total(self):
        url = reverse("add_to_cart", kwargs={"pk": self.priced.pk})
        self.assertEqual(self.client.post(url, {"quantity": "2"}).status_code, 302)
        response = self.client.post(url, {"quantity": "1"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session["cart"][str(self.priced.pk)], 3)
        response = self.client.post(url, {"quantity": "9997"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.session["cart"][str(self.priced.pk)], 3)

    def test_zero_stock_product_can_be_added_and_updated(self):
        self.priced.stock = Decimal("0")
        self.priced.save(update_fields=['stock'])
        detail = self.client.get(self.priced.get_absolute_url())
        self.assertContains(detail, 'id="add-to-cart-form"')
        url = reverse("add_to_cart", kwargs={"pk": self.priced.pk})
        self.assertEqual(self.client.post(url, {"quantity": "1"}).status_code, 302)
        response = self.client.post(reverse("update_cart", kwargs={"pk": self.priced.pk}), {"quantity": "4"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.session['cart'][str(self.priced.pk)], 4)

    def test_stock_is_optional_in_product_admin_form(self):
        form = ProductAdminForm(data={
            'name': 'Товар без остатка', 'slug': 'tovar-bez-ostatka',
            'description': 'Описание', 'price': '100', 'stock': '',
            'unit': 'шт', 'rating': '5',
        })
        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertEqual(product.stock, Decimal('0'))

    def test_explicitly_missing_stock_is_saved_as_zero(self):
        product = Product.objects.create(
            name='Товар без указанного остатка', slug='tovar-bez-ukazannogo-ostatka',
            description='Описание', price=Decimal('100'), stock=None,
        )
        product.refresh_from_db()
        self.assertEqual(product.stock, Decimal('0'))

    def test_checkout_rejects_stale_cart_with_unpriced_product(self):
        session = self.client.session
        session["cart"] = {str(self.unpriced.pk): 1}
        session.save()
        response = self.client.post(reverse("checkout"), {
            "name": "Покупатель", "email": "buyer@example.com", "phone": "+79990000000",
            "address": "Москва", "comment": "", "sales_terms": "on", "document_version": DOCUMENT_VERSION,
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)
        self.unpriced.refresh_from_db()
        self.assertEqual(self.unpriced.stock, Decimal("3"))
