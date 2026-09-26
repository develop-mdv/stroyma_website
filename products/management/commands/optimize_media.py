"""
Конвертирует существующие JPG/PNG изображений в WEBP (качество 90), ресайз длинной стороны до 1920 px.
Делает резервную копию MEDIA_ROOT в media_backup/<timestamp>/ перед изменениями.
Использование: python manage.py optimize_media [--apply]
"""

import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from products.models import BaseTexture, Category, Product, ProductImage
from products.utils import convert_image_bytes_to_webp
from services.models import Service, ServicePhoto


MODEL_FIELDS = (
    (Category, 'image'),
    (Product, 'image'),
    (ProductImage, 'image'),
    (BaseTexture, 'image'),
    (Service, 'image'),
    (ServicePhoto, 'image'),
)


class Command(BaseCommand):
    help = 'Бэкапит media/, конвертирует JPG/PNG в WEBP по записям БД; старые файлы сохраняет'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Выполнить конвертацию и обновить БД',
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']
        media_root = Path(settings.MEDIA_ROOT).resolve()
        if not media_root.exists():
            self.stdout.write(self.style.WARNING(f'Нет MEDIA_ROOT: {media_root}'))
            return

        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_target = Path(settings.BASE_DIR) / 'media_backup' / stamp / 'media'

        if apply_changes:
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(media_root, backup_target, dirs_exist_ok=True)
            self.stdout.write(self.style.SUCCESS(f'Резервная копия: {backup_target}'))

        total_done = 0
        for model_cls, field_name in MODEL_FIELDS:
            qs = model_cls.objects.exclude(**{f'{field_name}__isnull': True}).exclude(**{field_name: ''})
            for obj in qs.iterator():
                done = self._process_one(obj, field_name, apply_changes)
                if done:
                    total_done += 1

        self.stdout.write(f'Обработано записей (конвертировано): {total_done}')
        if not apply_changes:
            self.stdout.write(self.style.WARNING('Dry-run: добавьте --apply для записи WEBP и обновления БД'))

    def _process_one(self, obj, field_name: str, apply_changes: bool) -> bool:
        fld = getattr(obj, field_name, None)
        if not fld or not fld.name:
            return False

        old_name = fld.name
        lower = old_name.lower()
        if lower.endswith('.webp'):
            return False
        if lower.endswith('.gif'):
            return False
        suf = Path(old_name).suffix.lower()
        if suf not in ('.jpg', '.jpeg', '.png'):
            return False

        path = Path(fld.path)
        if not path.exists():
            self.stdout.write(self.style.WARNING(f'Файл отсутствует: {old_name}'))
            return False

        data = path.read_bytes()
        try:
            webp_bytes = convert_image_bytes_to_webp(data, quality=90, max_dim=1920)
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Ошибка PIL для {old_name}: {exc}'))
            return False

        stem = Path(old_name).stem
        upload_to = fld.field.upload_to
        if callable(upload_to):
            new_rel = upload_to(obj, f'{stem}.webp')
        else:
            prefix = str(upload_to or '').strip('/')
            new_rel = f'{prefix}/{stem}.webp' if prefix else f'{stem}.webp'

        new_rel = new_rel.replace('\\', '/')

        self.stdout.write(f'  {old_name} -> {new_rel} ({len(data)} -> {len(webp_bytes)} bytes)')

        if not apply_changes:
            return True

        from django.core.files.base import ContentFile
        with transaction.atomic():
            fld.save(Path(new_rel).name, ContentFile(webp_bytes), save=False)
            obj.save(update_fields=[field_name])

        # Один и тот же исходный файл может быть указан в нескольких записях.
        # Не удаляем его здесь: после проверки результатов это сделает cleanup_media.
        return True
