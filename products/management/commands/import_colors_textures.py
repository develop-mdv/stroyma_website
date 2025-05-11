import json
import os
from datetime import time

import requests
from django.core.files import File
from django.core.management.base import BaseCommand
from bs4 import BeautifulSoup
from pathlib import Path
from products.models import FacadeColor, BaseTexture  # ⬅️ замени 'your_app' на имя своего приложения


headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def rgb_to_hex(rgb_str):
    """Преобразует строку 'rgb(r, g, b)' в HEX"""
    parts = rgb_str.strip("rgb()").split(",")
    r, g, b = map(int, parts)
    return "#%02x%02x%02x" % (r, g, b)


def download_image(url, upload_dir='media/base_textures', retries=3):
    os.makedirs(upload_dir, exist_ok=True)
    filename = os.path.join(upload_dir, os.path.basename(url))

    for attempt in range(retries):
        try:
            response = requests.get(url, stream=True, timeout=10, headers=headers)
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return filename
            else:
                print(f"❌ Ошибка загрузки {url} (код {response.status_code})")
                break
        except (requests.exceptions.RequestException, ConnectionError) as e:
            print(f"🔁 Попытка {attempt + 1} не удалась: {e}")
            time.sleep(2)
    return None


class Command(BaseCommand):
    help = 'Импортирует цвета и текстуры из JSON файла'

    def handle(self, *args, **kwargs):
        json_file = 'ceresit_colors_textures.json'  # Путь к твоему JSON-файлу

        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Цвета
        for item in data['colors']:
            name = item['name']
            color_rgb = item['color']
            hex_code = rgb_to_hex(color_rgb)

            FacadeColor.objects.get_or_create(
                name=name,
                defaults={'hex_code': hex_code}
            )

        # Текстуры
        for item in data['textures']:
            name = item['name']
            image_url = item['image_url']

            local_path = download_image(image_url)

            with open(local_path, 'rb') as img_file:
                BaseTexture.objects.get_or_create(
                    name=name,
                    defaults={'image': File(img_file, name=os.path.basename(local_path))}
                )

        self.stdout.write(self.style.SUCCESS('✅ Данные успешно импортированы'))