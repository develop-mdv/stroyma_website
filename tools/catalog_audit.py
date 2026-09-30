"""Read-only audit of the stock and price files for the catalog import."""

from __future__ import annotations

import difflib
import re
from pathlib import Path

import openpyxl
import xlrd


STOCK_PATH = Path(r"C:\Users\dima_\Downloads\Остатки на склад 2.xlsx")
PRICE_PATH = Path(r"C:\Users\dima_\Downloads\прайс.xls")


def normalize(value: str) -> str:
    return re.sub(r"[^а-яa-z0-9]+", "", value.lower().replace("ё", "е"))


stock_sheet = openpyxl.load_workbook(STOCK_PATH, read_only=True, data_only=True).active
stock = [
    (row_number, str(row[2]).strip(" ,"), row[15], row[11])
    for row_number, row in enumerate(stock_sheet.iter_rows(values_only=True), 1)
    if 9 <= row_number <= 143
]
price_sheet = xlrd.open_workbook(PRICE_PATH).sheets()[0]
prices = [
    (row_number + 1, str(price_sheet.cell_value(row_number, 3)).strip(),
     price_sheet.cell_value(row_number, 7), price_sheet.cell_value(row_number, 8))
    for row_number in range(2, price_sheet.nrows)
    if price_sheet.cell_value(row_number, 3)
]

print(f"Остатки: {len(stock)}, прайс: {len(prices)}")


def similarity(first: str, second: str) -> float:
    direct = difflib.SequenceMatcher(None, normalize(first), normalize(second)).ratio()
    tokens_a = sorted(re.findall(r"[а-яa-z0-9]+", first.lower().replace("ё", "е")))
    tokens_b = sorted(re.findall(r"[а-яa-z0-9]+", second.lower().replace("ё", "е")))
    tokens = difflib.SequenceMatcher(None, " ".join(tokens_a), " ".join(tokens_b)).ratio()
    return max(direct, tokens)


# The price list is in the same product order as the stock export. Align the
# sequences, permitting an item to be absent from either file.
rows, cols = len(stock), len(prices)
dp = [[0.0] * (cols + 1) for _ in range(rows + 1)]
step = [[""] * (cols + 1) for _ in range(rows + 1)]
for i in range(1, rows + 1):
    dp[i][0] = -0.45 * i
    step[i][0] = "stock_only"
for j in range(1, cols + 1):
    dp[0][j] = -0.45 * j
    step[0][j] = "price_only"
for i in range(1, rows + 1):
    for j in range(1, cols + 1):
        score = similarity(stock[i - 1][1], prices[j - 1][1])
        options = [
            (dp[i - 1][j - 1] + 2 * score - 0.8, "match"),
            (dp[i - 1][j] - 0.45, "stock_only"),
            (dp[i][j - 1] - 0.45, "price_only"),
        ]
        dp[i][j], step[i][j] = max(options)

alignment = []
i, j = rows, cols
while i or j:
    action = step[i][j]
    if action == "match":
        alignment.append((stock[i - 1], prices[j - 1]))
        i -= 1
        j -= 1
    elif action == "stock_only":
        alignment.append((stock[i - 1], None))
        i -= 1
    else:
        alignment.append((None, prices[j - 1]))
        j -= 1
alignment.reverse()

for item, price in alignment:
    if not item:
        print(f"ТОЛЬКО ПРАЙС {price[0]}: {price[1]}")
    elif not price:
        print(f"БЕЗ ЦЕНЫ {item[0]}: {item[1]}")
    elif similarity(item[1], price[1]) < 0.85:
        print(f"СВЕРИТЬ {item[0]} -> {price[0]} ({similarity(item[1], price[1]):.3f}): "
              f"{item[1]} | {price[1]}")
