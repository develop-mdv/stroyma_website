"""Download only manually matched product photos and freeze them as WebP."""

from __future__ import annotations

import io
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "products" / "data" / "catalog_photo_sources.json"
DESTINATION = ROOT / "products" / "data" / "photos"
MAX_BYTES = 8 * 1024 * 1024


def download(photo: dict) -> tuple[int, str]:
    row = photo["row"]
    destination = DESTINATION / f"catalog-row-{row}.webp"
    if destination.exists():
        return row, "cached"
    request = urllib.request.Request(photo["image_url"], headers={
        "User-Agent": "Mozilla/5.0 (compatible; STROYMA catalog image preparation)",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
    })
    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            contents = response.read(MAX_BYTES + 1)
        if len(contents) > MAX_BYTES:
            raise ValueError("image exceeds 8 MB")
        with Image.open(io.BytesIO(contents)) as image:
            image.load()
            if min(image.size) < 100:
                raise ValueError(f"image is too small: {image.size}")
            image = ImageOps.exif_transpose(image)
            image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)
            if image.mode in ("RGBA", "P"):
                rgba = image.convert("RGBA")
                background = Image.new("RGBA", rgba.size, "white")
                background.alpha_composite(rgba)
                image = background.convert("RGB")
            else:
                image = image.convert("RGB")
            temporary = destination.with_suffix(".tmp")
            image.save(temporary, "WEBP", quality=86, method=6)
            temporary.replace(destination)
        return row, f"saved {destination.stat().st_size} bytes"
    except Exception as error:
        return row, f"ERROR {type(error).__name__}: {error}"


def main() -> None:
    photos = json.loads(MANIFEST.read_text(encoding="utf-8"))["photos"]
    DESTINATION.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(download, photo) for photo in photos]
        results = sorted(future.result() for future in as_completed(futures))
    for row, result in results:
        print(f"{row}: {result}")
    print(f"Photos available: {len(list(DESTINATION.glob('catalog-row-*.webp')))} / {len(photos)}")


if __name__ == "__main__":
    main()
