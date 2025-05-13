# products/management/commands/clear_sessions.py
from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.utils import timezone

class Command(BaseCommand):
    help = 'Удаляет устаревшие сессии'

    def handle(self, *args, **kwargs):
        # Удаление устаревших сессий
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        count, _ = expired_sessions.delete()
        self.stdout.write(self.style.SUCCESS(f'Удалено устаревших сессий: {count}'))