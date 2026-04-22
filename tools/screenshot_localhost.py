"""Полноэкранные скриншоты публичных страниц (sitemap + доп. маршруты)."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

BASE = "http://127.0.0.1:8000"
REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "скриншоты страниц"

EXTRA_PATHS = [
    "/catalog/",
    "/cart/",
    "/checkout/",
    "/checkout/success/",
    "/policy/",
    "/cookies-policy/",
    "/accounts/login/",
    "/accounts/register/",
    "/accounts/password-reset/",
]


def fetch_sitemap_urls() -> list[str]:
    xml = urlopen(f"{BASE}/sitemap.xml", timeout=60).read().decode("utf-8", errors="replace")
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def url_to_filename(url: str) -> str:
    p = urlparse(url)
    path = p.path.strip("/")
    if not path:
        return "home.png"
    name = path.replace("/", "__") + ".png"
    for c in '<>:"|?*':
        name = name.replace(c, "_")
    return name


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    urls = fetch_sitemap_urls()
    for path in EXTRA_PATHS:
        u = BASE.rstrip("/") + path
        if u not in urls:
            urls.append(u)
    seen: set[str] = set()
    ordered: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)

    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        print("Не найден npx (установите Node.js).", file=sys.stderr)
        return 1

    for url in ordered:
        out = OUT_DIR / url_to_filename(url)
        print(url, "->", out.name, flush=True)
        r = subprocess.run(
            [
                npx,
                "-y",
                "playwright",
                "screenshot",
                "--full-page",
                url,
                str(out),
            ],
            cwd=str(REPO_ROOT),
            shell=False,
        )
        if r.returncode != 0:
            print(f"Ошибка: {url}", file=sys.stderr)
            return r.returncode
    print(f"Готово: {len(ordered)} файлов в {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
