"""Create a reviewed catalog snapshot from the two 1C exports.

This is an offline data preparation tool. Run it with the repository's Python
environment and the two original files in Downloads. Product photos are added
from the separately reviewed image manifest, never guessed by this script.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

import openpyxl
import xlrd


ROOT = Path(__file__).resolve().parents[1]
STOCK_FILE = Path(r"C:\Users\dima_\Downloads\Остатки на склад 2.xlsx")
PRICE_FILE = Path(r"C:\Users\dima_\Downloads\прайс.xls")
OUTPUT = ROOT / "products" / "data" / "catalog_2026_09_29.json"
PHOTO_SOURCES = ROOT / "products" / "data" / "catalog_photo_sources.json"
NO_PRICE_ROWS = {31, 54, 68, 69, 70, 82, 84, 85, 114, 131, 132, 139}


CATEGORIES = {
    "Строительная химия": ["Жидкое стекло", "Грунтовки", "Герметики", "Очистители", "Монтажные клеи"],
    "Гидроизоляция": ["Обмазочная гидроизоляция", "Гидроизоляционные ленты"],
    "Сухие строительные смеси": ["Штукатурки", "Шпатлевки", "Наливные полы", "Пескобетон и цементные смеси", "Гипс, глина и мел"],
    "Плитка и облицовка": ["Плиточные клеи", "Цементные затирки", "Эпоксидные затирки", "Силиконовые затирки", "Керамогранит"],
    "Клеи": ["Клей для обоев"],
    "Лакокрасочные материалы": ["Фасадные краски", "Колеровочные пигменты"],
    "Тепло- и пароизоляция": ["Минеральная вата", "Экструдированный пенополистирол", "Изоляционные пленки", "Подложки"],
    "Профили и комплектующие": ["Профили для гипсокартона", "Подвесы", "Армирующие ленты и сетки", "Фасадные профили"],
    "Фасадные материалы": ["Декоративные штукатурки", "Фасадные сетки"],
    "Инженерное оборудование": ["Датчики", "Силиконовые патрубки", "Распылители"],
}


def category_for(row: int) -> tuple[str, str]:
    if row in (9, 32): return "Строительная химия", "Жидкое стекло"
    if row in (10, 128, 129, 140, 141, 143): return "Сухие строительные смеси", "Штукатурки"
    if row in (11, 12, 21, 22): return "Гидроизоляция", "Обмазочная гидроизоляция"
    if row == 13: return "Гидроизоляция", "Гидроизоляционные ленты"
    if row in (14, 26, 27, 28, 29, 30): return "Строительная химия", "Грунтовки"
    if 15 <= row <= 20: return "Строительная химия", "Герметики"
    if row in (23, 24, 25, 80): return "Сухие строительные смеси", "Гипс, глина и мел"
    if row in (31, 131, 132): return "Инженерное оборудование", "Датчики"
    if row == 33: return "Плитка и облицовка", "Силиконовые затирки"
    if row == 34: return "Плитка и облицовка", "Эпоксидные затирки"
    if 35 <= row <= 60: return "Плитка и облицовка", "Цементные затирки"
    if row in (61, 62, 63, 133, 134): return "Тепло- и пароизоляция", "Минеральная вата"
    if row == 64: return "Плитка и облицовка", "Керамогранит"
    if row in (*range(65, 71), *range(73, 77)): return "Клеи", "Клей для обоев"
    if row in (71, 72, 77, 78): return "Плитка и облицовка", "Плиточные клеи"
    if row == 79: return "Лакокрасочные материалы", "Фасадные краски"
    if row == 81: return "Строительная химия", "Монтажные клеи"
    if row == 82: return "Сухие строительные смеси", "Наливные полы"
    if row == 83: return "Строительная химия", "Очистители"
    if row in (84, 85): return "Инженерное оборудование", "Силиконовые патрубки"
    if row in (86, 110, 111, 126, 127): return "Сухие строительные смеси", "Пескобетон и цементные смеси"
    if 87 <= row <= 102: return "Лакокрасочные материалы", "Колеровочные пигменты"
    if 103 <= row <= 106: return "Тепло- и пароизоляция", "Изоляционные пленки"
    if row in (107, 108): return "Тепло- и пароизоляция", "Экструдированный пенополистирол"
    if row == 109: return "Профили и комплектующие", "Подвесы"
    if 112 <= row <= 118: return "Профили и комплектующие", "Профили для гипсокартона"
    if row == 119: return "Инженерное оборудование", "Распылители"
    if 120 <= row <= 122: return "Профили и комплектующие", "Армирующие ленты и сетки"
    if 123 <= row <= 125: return "Тепло- и пароизоляция", "Подложки"
    if row == 130: return "Фасадные материалы", "Фасадные сетки"
    if row in (135, 136): return "Профили и комплектующие", "Фасадные профили"
    if row in (137, 142): return "Фасадные материалы", "Декоративные штукатурки"
    if row in (138, 139): return "Сухие строительные смеси", "Шпатлевки"
    raise ValueError(f"Category missing for row {row}")


CERESIT_GROUT_SOURCE = "https://ceresit.ru/ru/products/tiling/grouts-and-sealants"


def description_for(row: int, name: str, unit: str) -> tuple[str, str]:
    if row in (16, 17):
        return (f"{name}. Нейтральный силиконовый герметик UNIS UN-80 для швов и стыков внутри и снаружи помещений, в том числе во влажных зонах. Фасовка 300 мл; цвет {'белый C01' if row == 16 else 'прозрачный C00'}.",
                "https://unistrom.ru/catalog/zatirki-i-germetiki/unis-un-80/")
    if row == 104:
        return (f"{name}. Двухслойная паро-гидроизоляционная плёнка повышенной прочности SpanIzol D Эконом для защиты конструкций от влаги и конденсата. Площадь рулона 70 м².",
                "https://stroy-ka.ru/goods/613736")
    if row == 119:
        return (f"{name}. Помповый распылитель SOUDAL объёмом 1 л для увлажнения поверхности и монтажной пены. Распыление регулируется; артикул производителя 799044.",
                "https://soudal.ru/skaczat/itemlist/tag/new")
    if row == 29:
        return (f"{name}. Адгезионная грунтовка «Бетонконтакт» с кварцевым наполнителем для гладких бетонных оснований перед нанесением штукатурки или плиточного клея. Фасовка 3 кг.",
                "https://www.vseinstrumenti.ru/product/gruntovka-betonkontakt-ceresit-ct-19-3-rossiya-2473931-2392762/")
    if row == 77:
        return (f"{name}. Цементный клей Ceresit CM 14 для облицовки стен и полов керамической плиткой и керамогранитом. Фасовка 25 кг.",
                "https://kemerovo.kwadratura.ru/katalog/plitka/smesi/klej/cerezit-cm14-klej-dlja-plitki")
    if row in (140, 141):
        source = ("https://famarket.ru/id/teplon-belyy-unis-5-kg-45998.html" if row == 140
                  else "https://famarket.ru/id/shtukaturka-unis-teplon-belyy-30kg-45997.html")
        return (f"{name}. Белая облегчённая гипсовая штукатурка UNIS Теплон с перлитом для выравнивания стен и потолков внутри помещений. Фасовка {5 if row == 140 else 30} кг.", source)
    if row in (11, 12):
        return (f"{name}. Готовая эластичная полимерная гидроизоляция для защиты основания перед укладкой плитки во влажных помещениях. "
                "Наносится кистью, валиком или шпателем.",
                "https://ceresit.ru/ru/products/tiling/waterproofing-for-tiling")
    if row in (21, 22):
        return (f"{name}. Цементная обмазочная гидроизоляция для недеформирующихся минеральных оснований. "
                "Применяется внутри и снаружи зданий, в том числе под плиточную облицовку.",
                "https://www.ceresit.ru/ru/products/waterproofing/waterproofing-materials/cr_65_waterproof")
    if row == 13:
        return (f"{name}. Эластичная лента UNIS UNIBAND 10 для герметизации примыканий, угловых и деформационных швов. "
                "Длина рулона 10 м.",
                "https://unistrom.ru/catalog/gidroizolyatsiya/gidroizolyatsionnaya-lenta-unis-uniband-10/")
    if 35 <= row <= 48:
        return (f"{name}. Цементная затирка Ceresit CE 33 для узких межплиточных швов шириной до 6 мм. "
                "Цвет и фасовка указаны в названии; перед покупкой сверьте номер оттенка.", CERESIT_GROUT_SOURCE)
    if 49 <= row <= 60:
        return (f"{name}. Эластичная водоотталкивающая затирка Ceresit CE 40 для межплиточных швов шириной до 10 мм. "
                "Подходит для стен и полов, в том числе с подогревом. Цвет и фасовка указаны в названии.",
                "https://ceresit.ru/ru/products/tiling/grouts-and-sealants/ce_40_aquastatic")
    if row == 34:
        return (f"{name}. Двухкомпонентная эпоксидная затирка для облицовочных швов. Цвет: серый 807; фасовка 2,5 кг.",
                CERESIT_GROUT_SOURCE)
    if row in (107, 108):
        return (f"{name}. Экструдированный пенополистирол ТЕХНОНИКОЛЬ CARBON ECO для теплоизоляции фундаментов, полов, крыш и фасадов. "
                "Размер плит и площадь упаковки указаны в названии.",
                "https://nav.tn.ru/cloud/iblock/bac/Tekhlist-4.01_CARBON-ECO_by.pdf")
    if row == 142:
        return (f"{name}. Акриловая декоративная штукатурка Ceresit CT 60 с камешковой фактурой, зерно 1,5 мм. "
                "Фасовка 25 кг.", "https://ceresit.ru/ru/products/etics/facade-plasters/ct-60-ct-63-ct-64")
    if row == 137:
        return (f"{name}. Силиконовая декоративная штукатурка Ceresit CT 74 с камешковой фактурой, зерно 1,5 мм. "
                "База под колеровку, фасовка 25 кг.", "https://www.ceresit.ru/ru/products/etics/facade-plasters")
    if row in (26, 28):
        return (f"{name}. Грунтовка Ceresit CT 17 глубокого проникновения для укрепления и обеспыливания впитывающих оснований "
                "перед последующими отделочными работами.", "https://www.ceresit.ru/ru/products/primers")
    if row in (27, 29, 30):
        return (f"{name}. Грунтовка Ceresit для подготовки основания перед нанесением отделочных материалов. "
                "Модель и фасовка указаны в названии.", "https://www.ceresit.ru/ru/products/primers")
    if row in (71, 72, 77, 78):
        return (f"{name}. Сухой плиточный клей для облицовочных работ. "
                "Используйте для оснований и форматов плитки, указанных производителем на упаковке.",
                "https://ceresit.ru/ru/products/tiling/tile-adhesives" if row == 77 else "")
    if 87 <= row <= 102:
        return (f"{name}. Колеровочный пигмент Ceresit. Учет и цена в прайсе ведутся за 1 мл, "
                "а обозначение 3 л относится к емкости. Цвет и буквенный код указаны в названии.", "")
    root, leaf = category_for(row)
    generic = {
        "Жидкое стекло": "Жидкое стекло для строительных и ремонтных работ.",
        "Штукатурки": "Штукатурная смесь для выравнивания поверхностей.",
        "Грунтовки": "Грунтовочный состав для подготовки основания.",
        "Герметики": "Герметизирующий состав для заполнения швов и стыков.",
        "Гипс, глина и мел": "Минеральный материал для строительных и отделочных работ.",
        "Силиконовые затирки": "Силиконовая затирка-герметик для облицовочных швов.",
        "Минеральная вата": "Минераловатный теплоизоляционный материал. Размеры и площадь упаковки указаны в названии.",
        "Керамогранит": "Керамогранит для облицовки. Формат и площадь указаны в названии.",
        "Клей для обоев": "Обойный клей. Тип обоев и масса упаковки указаны в названии.",
        "Фасадные краски": "Латексная фасадная краска для наружной отделки.",
        "Монтажные клеи": "Монтажный клей для строительных и ремонтных работ.",
        "Наливные полы": "Сухая смесь для устройства и выравнивания пола.",
        "Очистители": "Очиститель для монтажной пены.",
        "Силиконовые патрубки": "Силиконовый прямой патрубок. Диаметр и длина указаны в названии.",
        "Пескобетон и цементные смеси": "Сухая смесь на цементном вяжущем. Марка и фасовка указаны в названии.",
        "Изоляционные пленки": "Изоляционная пленка в рулоне. Назначение и площадь указаны в названии.",
        "Экструдированный пенополистирол": "Плиты экструдированного пенополистирола. Размеры указаны в названии.",
        "Подвесы": "Комплектующий элемент для каркасной системы.",
        "Профили для гипсокартона": "Металлический профиль для монтажа каркасных конструкций. Размеры указаны в названии.",
        "Распылители": "Ручной распылитель для воды объемом 1 л.",
        "Армирующие ленты и сетки": "Самоклеящаяся армирующая лента для усиления швов. Ширина и длина указаны в названии.",
        "Подложки": "Рулонная подложка. Толщина и площадь указаны в названии.",
        "Фасадные сетки": "Стеклотканевая фасадная сетка для армирования штукатурного слоя.",
        "Фасадные профили": "Профиль для фасадных работ. Размеры указаны в названии.",
        "Шпатлевки": "Шпатлевка для выравнивания поверхности перед финишной отделкой.",
        "Датчики": "Измерительный датчик. Точная модель указана в названии.",
    }
    return f"{name}. {generic[leaf]} Единица продажи: {unit}.", ""


def clean_name(value: str) -> str:
    value = value.strip(" ,")
    value = re.sub(r"!{2,}НЕТ В НАЛИЧИИ!{2,}", "", value, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", value).strip(" ,")


def main() -> None:
    photo_by_row = {item["row"]: item for item in
                    json.loads(PHOTO_SOURCES.read_text(encoding="utf-8"))["photos"]}
    sheet = openpyxl.load_workbook(STOCK_FILE, read_only=True, data_only=True).active
    stock_rows = [(number, row) for number, row in enumerate(sheet.iter_rows(values_only=True), 1)
                  if 9 <= number <= 143]
    price_sheet = xlrd.open_workbook(PRICE_FILE).sheets()[0]
    price_rows = [(number + 1, price_sheet.row_values(number)) for number in range(2, price_sheet.nrows)
                  if price_sheet.cell_value(number, 3)]
    priced_stock = [(number, row) for number, row in stock_rows if number not in NO_PRICE_ROWS]
    assert len(stock_rows) == 135 and len(price_rows) == len(priced_stock) == 123
    price_by_row = dict(zip((number for number, _ in priced_stock), price_rows))
    items = []
    for number, row in stock_rows:
        name = clean_name(str(row[2]))
        unit_raw = str(row[11]).strip()
        unit = {"см3 (мл)": "мл", "м2": "м²"}.get(unit_raw, unit_raw)
        available = Decimal(str(row[15] if row[15] is not None else 0))
        stock = max(Decimal(0), available)
        match = price_by_row.get(number)
        price = Decimal(str(match[1][7])) if match else Decimal(0)
        description, info_source = description_for(number, name, unit)
        root, leaf = category_for(number)
        assert leaf in CATEGORIES[root]
        items.append({
            "source_key": str(match[1][1]) if match else f"stock-2026-09-29-row-{number}",
            "stock_row": number,
            "price_row": match[0] if match else None,
            "name": name,
            "description": description,
            "price": str(price.quantize(Decimal('0.01'))),
            "stock": str(stock.quantize(Decimal('0.001'))),
            "unit": unit,
            "category": [root, leaf],
            "info_source": info_source,
            "photo_url": photo_by_row.get(number, {}).get("image_url", ""),
            "photo_page": photo_by_row.get(number, {}).get("source_page", ""),
            "image_kind": "photo" if number in photo_by_row else "illustration",
        })
    output = {"source": {"stock": STOCK_FILE.name, "price": PRICE_FILE.name,
                         "stock_date": "2026-09-29", "price_type": "Опт"},
              "categories": CATEGORIES, "products": items}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(items)} products to {OUTPUT}; {len(price_rows)} with prices, "
          f"{len(NO_PRICE_ROWS)} without prices")


if __name__ == "__main__":
    main()
