"""Render labeled catalog illustrations where an exact product photo is unavailable.

These are schematic category drawings, deliberately distinct from product photos.
Every image carries the exact name from the dated stock snapshot.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "products" / "data"
OUTPUT = DATA / "illustrations"
FONT_REGULAR = Path("C:/Windows/Fonts/segoeui.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/segoeuib.ttf")
SIZE = 1000


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size)


def family(item: dict) -> str:
    name = item["name"].lower()
    leaf = item["category"][1].lower()
    if "пигмент" in name:
        return "pigment"
    if "профиль" in name or "подвес" in name or "угол" in name:
        return "profile"
    if "патрубок" in name:
        return "pipe"
    if "датчик" in name or "термообразователь" in name:
        return "sensor"
    if "пленка" in name or "серпянка" in name or "скайфлекс" in name:
        return "roll"
    if "утеплитель" in name or "izomin" in name or "изомин" in name:
        return "insulation"
    if "герметик" in name or "силикон" in name:
        return "cartridge"
    if "клей для обоев" in name or "titan wild" in name:
        return "box"
    if "затирк" in name:
        return "grout"
    if "краска" in name or "грунтовка" in name or "жидкое стекло" in name:
        return "bucket"
    if "распылитель" in name:
        return "sprayer"
    if "сух" in leaf or "смес" in name or "гипс" in name or "мел" in name or "цемент" in name:
        return "bag"
    return "material"


ACCENTS = {
    "pigment": "#B05B44", "profile": "#617A80", "pipe": "#5387A4",
    "sensor": "#566C8A", "roll": "#719C8A", "insulation": "#B99060",
    "cartridge": "#8A80A0", "box": "#8677A8", "grout": "#B47873",
    "bucket": "#7294A6", "sprayer": "#66939D", "bag": "#A58B6B",
    "material": "#8E9984",
}

PIGMENT_COLORS = {
    "желтый": "#E6BC3C", "белый": "#F1F1E9", "голубой": "#5BA6C2",
    "черный": "#2F3337", "красный": "#C94E4E", "розовый": "#DD8FA3",
    "пурпурный": "#9B568E", "зеленый": "#68A16D",
}


def icon(draw: ImageDraw.ImageDraw, kind: str, name: str, accent: str) -> None:
    dark, light = "#32413F", "#FAFAF5"
    if kind == "pigment":
        color = next((value for key, value in PIGMENT_COLORS.items() if key in name.lower()), accent)
        draw.rounded_rectangle((330, 226, 670, 550), radius=42, fill=light, outline=dark, width=9)
        draw.rounded_rectangle((390, 190, 610, 252), radius=15, fill=dark)
        draw.ellipse((378, 298, 622, 536), fill=color, outline=dark, width=8)
        draw.ellipse((450, 345, 550, 445), fill="#FFFFFF", outline=dark, width=5)
    elif kind == "profile":
        draw.polygon([(236, 466), (577, 270), (778, 314), (437, 510)], fill="#CED8D7")
        draw.polygon([(236, 466), (437, 510), (437, 580), (236, 536)], fill="#718D93")
        draw.polygon([(437, 510), (778, 314), (778, 383), (437, 580)], fill="#97ACAE")
        draw.line([(236, 466), (577, 270), (778, 314)], fill=dark, width=11, joint="curve")
        draw.line([(236, 466), (236, 536), (437, 580), (778, 383), (778, 314)], fill=dark, width=11, joint="curve")
    elif kind == "pipe":
        draw.rounded_rectangle((250, 330, 746, 473), radius=60, fill="#7194AE", outline=dark, width=10)
        draw.ellipse((645, 330, 765, 473), fill="#ECF3F3", outline=dark, width=10)
        draw.ellipse((678, 364, 731, 438), fill="#708EA4", outline=dark, width=7)
        draw.line((260, 352, 640, 352), fill="#BDD6DF", width=12)
    elif kind == "sensor":
        draw.rounded_rectangle((365, 235, 635, 415), radius=32, fill=light, outline=dark, width=9)
        draw.rectangle((405, 414, 595, 526), fill="#8A9BAB", outline=dark, width=8)
        draw.line((500, 525, 500, 590), fill=dark, width=12)
        draw.ellipse((472, 263, 528, 319), fill=accent, outline=dark, width=5)
        draw.line((416, 365, 584, 365), fill=dark, width=8)
    elif kind in ("roll", "insulation"):
        fill = "#D7B27F" if kind == "insulation" else "#D6E5DB"
        draw.rounded_rectangle((320, 315, 675, 540), radius=23, fill=fill, outline=dark, width=8)
        draw.ellipse((236, 315, 406, 540), fill=fill, outline=dark, width=9)
        draw.ellipse((280, 364, 365, 491), fill="#F9FAF5", outline=dark, width=7)
        draw.line((450, 335, 450, 522), fill=accent, width=10)
        draw.line((490, 335, 490, 522), fill=accent, width=10)
    elif kind == "cartridge":
        draw.polygon([(624, 300), (730, 337), (624, 366)], fill=dark)
        draw.rounded_rectangle((300, 340, 635, 465), radius=18, fill=light, outline=dark, width=9)
        draw.rectangle((236, 370, 300, 435), fill="#B5A9BF", outline=dark, width=7)
        draw.line((190, 402, 235, 402), fill=dark, width=12)
        draw.rounded_rectangle((385, 355, 570, 450), radius=10, fill=accent)
    elif kind in ("box", "bag", "grout", "material"):
        if kind == "box":
            draw.polygon([(300, 280), (650, 280), (710, 335), (360, 335)], fill="#C9BFD7", outline=dark)
            draw.polygon([(650, 280), (710, 335), (710, 560), (650, 510)], fill="#AB9CBE", outline=dark)
            draw.rounded_rectangle((300, 280, 650, 560), radius=12, fill=light, outline=dark, width=9)
        else:
            draw.polygon([(340, 250), (660, 250), (710, 560), (290, 560)], fill=light, outline=dark)
            draw.line([(340, 250), (660, 250), (710, 560), (290, 560), (340, 250)], fill=dark, width=9)
            draw.line((330, 315, 670, 315), fill=accent, width=11)
        draw.rounded_rectangle((356, 360, 644, 495), radius=18, fill=accent)
        draw.line((394, 408, 606, 408), fill="#FFFFFF", width=11)
        draw.line((418, 448, 582, 448), fill="#FFFFFF", width=11)
    elif kind in ("bucket", "sprayer"):
        draw.polygon([(312, 295), (688, 295), (650, 550), (350, 550)], fill=light, outline=dark)
        draw.line([(312, 295), (688, 295), (650, 550), (350, 550), (312, 295)], fill=dark, width=9)
        draw.ellipse((300, 266, 700, 323), fill="#DEE5E3", outline=dark, width=9)
        draw.rounded_rectangle((366, 367, 634, 475), radius=18, fill=accent)
        if kind == "sprayer":
            draw.rectangle((446, 227, 554, 269), fill=dark)
            draw.rectangle((500, 199, 668, 232), fill=dark)


def wrapped(text: str, draw: ImageDraw.ImageDraw, face: ImageFont.FreeTypeFont,
            width: int) -> list[str]:
    result: list[str] = []
    line = ""
    for token in text.split():
        trial = f"{line} {token}".strip()
        if line and draw.textbbox((0, 0), trial, font=face)[2] > width:
            result.append(line)
            line = token
        else:
            line = trial
    if line:
        result.append(line)
    return result


def render(item: dict, destination: Path) -> None:
    kind = family(item)
    accent = ACCENTS[kind]
    image = Image.new("RGB", (SIZE, SIZE), "#F1F4EF")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((55, 48, 945, 950), radius=38, fill="#E6EBE5")
    draw.rounded_rectangle((75, 68, 925, 640), radius=30, fill="#F9FAF6")
    draw.ellipse((180, 110, 820, 635), fill="#E9EFE9")
    draw.rounded_rectangle((106, 96, 332, 145), radius=24, fill=accent)
    draw.text((130, 103), "ИЛЛЮСТРАЦИЯ", font=font(25, True), fill="#FFFFFF")
    icon(draw, kind, item["name"], accent)

    draw.rounded_rectangle((75, 650, 925, 930), radius=28, fill="#FFFFFF")
    category = item["category"][1]
    if len(category) > 42:
        category = category[:39].rstrip() + "…"
    draw.text((115, 673), category.upper(), font=font(26, True), fill=accent)

    name = re.sub(r"\s+", " ", item["name"]).strip()
    for size in range(45, 27, -1):
        face = font(size, True)
        lines = wrapped(name, draw, face, 770)
        line_height = int(size * 1.22)
        if len(lines) * line_height <= 190 and all(
            draw.textbbox((0, 0), line, font=face)[2] <= 770 for line in lines
        ):
            break
    else:
        raise ValueError(f"Product name does not fit: {item['stock_row']} {name}")
    for index, line in enumerate(lines):
        draw.text((115, 721 + index * line_height), line, font=face, fill="#25322F")
    image.save(destination, "WEBP", quality=88, method=6)


def main() -> None:
    snapshot = json.loads((DATA / "catalog_2026_09_29.json").read_text(encoding="utf-8"))
    photo_rows = {entry["row"] for entry in json.loads(
        (DATA / "catalog_photo_sources.json").read_text(encoding="utf-8")
    )["photos"]}
    OUTPUT.mkdir(exist_ok=True)
    count = 0
    for item in snapshot["products"]:
        row = item["stock_row"]
        destination = OUTPUT / f"catalog-row-{row}.webp"
        if row in photo_rows:
            if destination.exists():
                destination.unlink()
            continue
        render(item, destination)
        count += 1
    print(f"Generated {count} labeled illustrations; {len(photo_rows)} products use matched photos")


if __name__ == "__main__":
    main()
