import os
import django
import sys

# Setup Django environment
sys.path.append(r'd:\ProgHub\stroyma\stroyma_website')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stroyma.settings')
django.setup()

from django.core.files import File
from products.models import Product

images = [
    r'C:\Users\dima_\.gemini\antigravity\brain\1537fd37-25a0-471d-91f6-54510ee2ddfc\premium_red_bricks_1775491776019.png',
    r'C:\Users\dima_\.gemini\antigravity\brain\1537fd37-25a0-471d-91f6-54510ee2ddfc\premium_wood_planks_1775491789687.png',
    r'C:\Users\dima_\.gemini\antigravity\brain\1537fd37-25a0-471d-91f6-54510ee2ddfc\premium_cement_bags_1775491817120.png'
]

products = Product.objects.all()
updated_count = 0

for i, p in enumerate(products):
    img_path = images[i % len(images)]
    if os.path.exists(img_path):
        with open(img_path, 'rb') as f:
            p.image.save(f'premium_mat_{i}.png', File(f), save=True)
            
        # Also clean up the names to look like real products if they start with Test
        if p.name.startswith('Тест') or 'вапв' in p.name:
            if 'bricks' in img_path:
                p.name = f"Кирпич строительный Premium марки M{150 + i*10}"
                p.description = "Высококачественный керамический кирпич для надежной кладки. Идеальная геометрия и максимальная прочность."
            elif 'wood' in img_path:
                p.name = f"Доска строганая Дуб сорт Экстра {20+i}мм"
                p.description = "Премиальная дубовая доска камерной сушки. Отличная текстура для отделочных работ и создания элитной мебели."
            elif 'cement' in img_path:
                p.name = f"Смесь сухая Портланд-цемент ПЦ-500 Д{i * 5}"
                p.description = "Профессиональная сухая строительная смесь высокой прочности. Быстрое схватывание, морозостойкость."
            p.save()
        updated_count += 1

print(f"Updated {updated_count} products with premium images and text!")
