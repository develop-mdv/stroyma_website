import requests
from bs4 import BeautifulSoup
import json

# URL страницы
url = "https://ceresitshop-msk.ru/kolerovka "

# Заголовки для имитации браузера
headers = {
    "User-Agent": "Mozilla/5.0"
}

# Отправляем GET-запрос
response = requests.get(url, headers=headers)

# Проверяем успешность запроса
if response.status_code != 200:
    print("Не удалось загрузить страницу")
    exit()

# Парсим HTML
soup = BeautifulSoup(response.text, 'html.parser')

colors_data = []
textures_data = []

# Находим вкладку с цветами (tab1)
color_tab = soup.find('div', {'id': 'tab1'})
if color_tab:
    color_items = color_tab.find_all('div', class_='intro__showcase_variant_item')
    for item in color_items:
        span = item.find('span')
        name = item.find('p').text.strip()
        color = span.get('data-color') or span.get('style', '').split('background-color:')[1].strip().rstrip('; ')
        colors_data.append({
            'name': name,
            'color': color
        })

# Находим вкладку с плинтусами (tab2)
texture_tab = soup.find('div', {'id': 'tab2'})
if texture_tab:
    texture_items = texture_tab.find_all('div', class_='intro__showcase_variant_item')
    for item in texture_items:
        span = item.find('span')
        name = item.find('p').text.strip()
        img_url = span.get('data-img')
        if img_url:
            textures_data.append({
                'name': name,
                'image_url': 'https://ceresitshop-msk.ru' + img_url if img_url.startswith('/') else img_url
            })

# Формируем общий словарь
result = {
    'colors': colors_data,
    'textures': textures_data
}

# Сохраняем в JSON файл
with open('ceresit_colors_textures.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, ensure_ascii=False, indent=4)

print("✅ Данные успешно сохранены в файл ceresit_colors_textures.json")