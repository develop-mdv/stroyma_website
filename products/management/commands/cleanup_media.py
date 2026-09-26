"""
Удаляет файлы в MEDIA_ROOT, которые не указаны ни в одном FileField моделей Django.
По умолчанию только dry-run; для удаления добавьте --apply.
"""

from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import models


class Command(BaseCommand):
    help = (
        'Находит файлы в media/, не связанные с записью БД (FileField), и удаляет их '
        '(например дубликаты текстур после повторных импортов). По умолчанию dry-run.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Реально удалить файлы (иначе только список)',
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']
        referenced = self._collect_referenced_relative_paths()

        media_root = Path(settings.MEDIA_ROOT).resolve()
        if not media_root.exists():
            self.stdout.write(self.style.WARNING(f'Нет каталога MEDIA_ROOT: {media_root}'))
            return

        orphaned = []
        for path in media_root.rglob('*'):
            if not path.is_file():
                continue
            try:
                rel = path.relative_to(media_root).as_posix()
            except ValueError:
                continue
            if rel not in referenced:
                orphaned.append(path)

        self.stdout.write(f'Упомянутых в БД файлов (FileField): {len(referenced)}')
        self.stdout.write(f'Найдено «лишних» файлов на диске: {len(orphaned)}')

        for path in sorted(orphaned):
            display = path.relative_to(media_root).as_posix()
            self.stdout.write(f'  [orphan] {display}')
            if apply_changes:
                path.unlink()

        if apply_changes:
            self.stdout.write(self.style.SUCCESS('Удаление выполнено.'))
        else:
            self.stdout.write(self.style.WARNING('Dry-run: повторите с --apply для удаления'))

    def _collect_referenced_relative_paths(self):
        referenced = set()
        for model in apps.get_models():
            for field in model._meta.get_fields():
                if isinstance(field, models.FileField):
                    fname = field.name
                    qs = model.objects.exclude(**{f'{fname}__isnull': True}).exclude(**{fname: ''})
                    for val in qs.values_list(fname, flat=True):
                        if val:
                            referenced.add(str(val).replace('\\', '/'))
        return referenced
