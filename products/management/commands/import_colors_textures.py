import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import requests
from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand

from products.models import FacadeColor, BaseTexture


HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    ),
}


def rgb_to_hex(rgb_str):
    parts = rgb_str.strip().strip('rgb()').split(',')
    r, g, b = (int(x.strip()) for x in parts[:3])
    return '#%02x%02x%02x' % (r, g, b)


def download_texture(url: str, dest_abs: Path, retries: int = 3):
    dest_abs.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest_abs.with_suffix(dest_abs.suffix + '.download')

    for attempt in range(retries):
        try:
            resp = requests.get(url, stream=True, timeout=15, headers=HEADERS)
            if resp.status_code != 200:
                raise RuntimeError(f'HTTP {resp.status_code}')
            with open(tmp, 'wb') as f:
                for chunk in resp.iter_content(65536):
                    f.write(chunk)
            if dest_abs.exists():
                dest_abs.unlink()
            shutil.move(str(tmp), str(dest_abs))
            return dest_abs
        except (requests.exceptions.RequestException, OSError, RuntimeError) as exc:
            if tmp.exists():
                tmp.unlink(missing_ok=True)
            print(f'Попытка {attempt + 1}/{retries} для {url}: {exc}')
            time.sleep(2)

    return None


class Command(BaseCommand):
    help = 'Импорт цветов и текстур из ceresit_colors_textures.json (идемпотентно).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json-path',
            default=str(Path(settings.BASE_DIR) / 'ceresit_colors_textures.json'),
            help='Путь к JSON с ключами colors и textures',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Обновить hex-код цветов и файлы текстур, если записи уже есть',
        )

    def handle(self, *args, **options):
        json_path = Path(options['json_path']).resolve()
        update = options['update']

        if not json_path.is_file():
            raise SystemExit(f'Не найден файл: {json_path}')

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for item in data.get('colors', []):
            name = item['name']
            hex_code = rgb_to_hex(item['color'])
            existing = FacadeColor.objects.filter(name=name).first()
            if existing:
                if update and existing.hex_code != hex_code:
                    existing.hex_code = hex_code
                    existing.save(update_fields=['hex_code'])
                    self.stdout.write(f'Обновлён цвет: {name}')
                continue
            FacadeColor.objects.create(name=name, hex_code=hex_code)
            self.stdout.write(f'Добавлен цвет: {name}')

        # Сначала скачиваем во временный каталог. FileField сам поместит файл
        # в MEDIA_ROOT/base_textures и не создаст лишнюю копию с суффиксом.
        with tempfile.TemporaryDirectory(prefix='stroyma_textures_') as tmp_dir:
            for item in data.get('textures', []):
                name = item['name']
                image_url = item['image_url']
                basename = os.path.basename(image_url.split('?')[0])
                obj = BaseTexture.objects.filter(name=name).first()
                if obj is not None and not update:
                    continue

                downloaded = download_texture(image_url, Path(tmp_dir) / basename)
                if not downloaded or downloaded.stat().st_size == 0:
                    self.stdout.write(
                        self.style.ERROR(f'Не удалось скачать текстуру «{name}»: {image_url}')
                    )
                    continue

                with downloaded.open('rb') as img_file:
                    django_file = File(img_file, name=basename)
                    if obj:
                        obj.image.save(basename, django_file, save=False)
                        obj.save(update_fields=['image'])
                        self.stdout.write(f'Обновлена текстура: {name}')
                    else:
                        BaseTexture.objects.create(name=name, image=django_file)
                        self.stdout.write(f'Добавлена текстура: {name}')

        self.stdout.write(self.style.SUCCESS('Импорт завершён'))
