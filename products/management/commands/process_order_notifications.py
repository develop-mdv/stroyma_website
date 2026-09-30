"""Send durable order notifications queued in PostgreSQL."""

import logging
import time
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import close_old_connections, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags

from products.models import OrderNotification


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Отправить ожидающие email о заказах; --loop запускает постоянный worker.'

    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true')
        parser.add_argument('--interval', type=int, default=15)
        parser.add_argument('--limit', type=int, default=20)

    def handle(self, *args, **options):
        if options['interval'] < 1 or options['limit'] < 1:
            raise ValueError('interval и limit должны быть положительными')
        try:
            while True:
                close_old_connections()
                processed = self._process_batch(options['limit'])
                close_old_connections()
                if not options['loop']:
                    self.stdout.write(f'Обработано уведомлений: {processed}')
                    return
                if processed < options['limit']:
                    time.sleep(options['interval'])
        except KeyboardInterrupt:
            return

    def _process_batch(self, limit):
        processed = 0
        for _ in range(limit):
            with transaction.atomic():
                notification = (
                    OrderNotification.objects
                    .select_for_update(skip_locked=True)
                    .filter(sent_at__isnull=True, next_attempt_at__lte=timezone.now())
                    .order_by('next_attempt_at', 'pk')
                    .first()
                )
                if notification is None:
                    break
                order = notification.order
                try:
                    contact = order.contact
                    html = render_to_string('products/order_email_template.html', {
                        'items': order.items.all(),
                        'total_price': order.total_cost,
                        'customer_name': contact.name,
                        'user_email': contact.email,
                        'user_phone': contact.phone,
                        'delivery_address': contact.address,
                        'order': order,
                    })
                    sent = send_mail(
                        f'Новый заказ №{order.pk}',
                        strip_tags(html),
                        settings.DEFAULT_FROM_EMAIL,
                        [settings.ORDER_NOTIFY_EMAIL],
                        html_message=html,
                        fail_silently=False,
                    )
                    if sent != 1:
                        raise RuntimeError('SMTP не подтвердил отправку')
                except Exception as exc:
                    notification.attempts += 1
                    delay_minutes = min(2 ** min(notification.attempts - 1, 6), 60)
                    notification.next_attempt_at = timezone.now() + timedelta(minutes=delay_minutes)
                    notification.last_error = type(exc).__name__
                    notification.save(update_fields=['attempts', 'next_attempt_at', 'last_error'])
                    logger.exception('Не удалось отправить уведомление о заказе #%s', order.pk)
                else:
                    notification.attempts += 1
                    notification.sent_at = timezone.now()
                    notification.last_error = ''
                    notification.save(update_fields=['attempts', 'sent_at', 'last_error'])
                    logger.info('Отправлено уведомление о заказе #%s', order.pk)
                processed += 1
        return processed
