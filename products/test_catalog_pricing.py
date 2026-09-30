"""Guard the catalogue's unpriced items and imported stock limits."""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

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

    def test_cart_respects_stock_and_keeps_existing_quantity(self):
        url = reverse("add_to_cart", kwargs={"pk": self.priced.pk})
        self.assertEqual(self.client.post(url, {"quantity": "2"}).status_code, 302)
        response = self.client.post(url, {"quantity": "1"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.session["cart"][str(self.priced.pk)], 2)

    def test_checkout_rejects_stale_cart_with_unpriced_product(self):
        session = self.client.session
        session["cart"] = {str(self.unpriced.pk): 1}
        session.save()
        response = self.client.post(reverse("checkout"), {
            "name": "Покупатель", "email": "buyer@example.com", "phone": "+79990000000",
            "address": "Москва", "comment": "",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)
        self.unpriced.refresh_from_db()
        self.assertEqual(self.unpriced.stock, Decimal("3"))
