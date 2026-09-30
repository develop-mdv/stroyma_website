from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import LegalAcceptance
from stroyma.legal import DOCUMENT_VERSION
from products.models import Order, Product


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
                   RATELIMIT_ENABLE=False)
class LegalFlowTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name='Смесь', price=Decimal('100'), stock=5)
        session = self.client.session
        session['cart'] = {str(self.product.pk): 2}
        session.save()
        self.order_data = {'name': 'Покупатель', 'email': 'buyer@example.com', 'phone': '+79991234567',
                           'address': 'Курск', 'sales_terms': 'on', 'document_version': DOCUMENT_VERSION}

    def test_checkout_requires_terms_and_current_version_without_side_effects(self):
        for field, value in [('sales_terms', ''), ('document_version', ''), ('document_version', 'old')]:
            with self.subTest(field=field, value=value):
                response = self.client.post(reverse('checkout'), {**self.order_data, field: value})
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['form'].errors)
                self.assertFalse(Order.objects.exists())
                self.assertFalse(LegalAcceptance.objects.exists())
                self.product.refresh_from_db()
                self.assertEqual(self.product.stock, 5)
                self.assertEqual(self.client.session['cart'][str(self.product.pk)], 2)

    def test_order_records_server_document_and_does_not_require_extra_consent(self):
        self.product.unit = 'кг'
        self.product.save(update_fields=['unit'])
        response = self.client.post(reverse('checkout'), {**self.order_data, 'document_snapshot': 'forged'})
        self.assertEqual(response.status_code, 302)
        receipt = LegalAcceptance.objects.get(kind='sale')
        self.assertEqual(receipt.order_id, Order.objects.get().pk)
        self.assertEqual(receipt.version, DOCUMENT_VERSION)
        self.assertIn('десяти дней', receipt.document_snapshot)
        self.assertNotIn('forged', receipt.document_snapshot)
        self.assertIsNone(receipt.user_id)
        item = receipt.order.items.get()
        self.product.unit = 'мешок'
        self.product.save(update_fields=['unit'])
        item.refresh_from_db()
        self.assertEqual(item.product_unit, 'кг')

    @patch('products.views.record_acceptance', side_effect=DatabaseError('evidence unavailable'))
    def test_evidence_failure_rolls_back_order_and_stock(self, _record):
        response = self.client.post(reverse('checkout'), self.order_data)
        self.assertEqual(response.status_code, 503)
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(self.client.session['cart'][str(self.product.pk)], 2)

    def test_contact_requires_consent_before_sending_email(self):
        data = {'name': 'Иван', 'email': 'test@example.com', 'message': 'Вопрос',
                'document_version': DOCUMENT_VERSION}
        response = self.client.post(reverse('contact'), data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(mail.outbox)
        self.assertFalse(LegalAcceptance.objects.exists())
        response = self.client.post(reverse('contact'), {**data, 'consent': 'on'})
        self.assertEqual(response.status_code, 302)
        receipt = LegalAcceptance.objects.get(kind='contact')
        self.assertEqual(receipt.subject, data['email'])
        self.assertIn(str(receipt.pk), mail.outbox[0].body)

    @patch('accounts.views._send_confirmation_email', return_value=True)
    def test_registration_requires_and_records_separate_consent(self, _send):
        data = {'username': 'new-buyer', 'email': 'new@example.com', 'password1': 'Long-Password-2026!',
                'password2': 'Long-Password-2026!', 'document_version': DOCUMENT_VERSION}
        self.assertEqual(self.client.post(reverse('register'), data).status_code, 400)
        self.assertFalse(User.objects.exists())
        self.assertFalse(LegalAcceptance.objects.exists())
        response = self.client.post(reverse('register'), {**data, 'privacy_policy': 'on'})
        self.assertEqual(response.status_code, 200)
        receipt = LegalAcceptance.objects.get(kind='registration')
        self.assertEqual(receipt.user_id, User.objects.get().pk)
        self.assertEqual(receipt.subject, data['email'])
        self.assertIn('личного кабинета', receipt.document_snapshot)

    def test_color_selection_records_consent_and_normalized_contact(self):
        data = {'name': 'Анна', 'phone': '8 (999) 123-45-67', 'consent': 'on',
                'document_version': DOCUMENT_VERSION}
        response = self.client.post(reverse('color_selection'), data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(LegalAcceptance.objects.get(kind='color_selection').subject, '+79991234567')

    def test_legal_documents_have_no_staging_notes_or_third_party_embeds(self):
        for name in ('policy', 'cookies_policy', 'offer', 'delivery', 'returns', 'contact'):
            with self.subTest(name=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'шаблон для публикации на стенде')
                self.assertNotContains(response, 'map-widget')
                self.assertNotContains(response, 'cdn.jsdelivr.net')
        for purpose in ('registration', 'contact', 'color_selection'):
            response = self.client.get(reverse('consent', args=[purpose]))
            self.assertContains(response, DOCUMENT_VERSION)
            self.assertContains(response, 'Отзыв')
        self.assertEqual(self.client.get(reverse('consent', args=['unknown'])).status_code, 404)
