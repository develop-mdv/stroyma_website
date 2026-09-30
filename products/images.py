"""Prebuilt responsive images; page requests never resize photographs."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

WIDTHS = (160, 400, 800, 1280)
RECIPE = 'webp-q80-v1'


def variant_names(field):
    if not field or Path(field.name).suffix.lower() == '.gif':
        return {}
    try:
        stat = Path(field.path).stat()
    except (OSError, NotImplementedError, ValueError):
        return {}
    key = sha256(f'{RECIPE}:{field.name}:{stat.st_size}:{stat.st_mtime_ns}'.encode()).hexdigest()[:24]
    parent = Path(field.name).parent.as_posix()
    return {width: f'{parent}/.thumbnails/{key}-{width}.webp' for width in WIDTHS}


def build_variants(field):
    names = variant_names(field)
    missing = {width: name for width, name in names.items() if not field.storage.exists(name)}
    if not missing:
        return 0
    with field.open('rb') as source, Image.open(source) as image:
        # Animated images retain their original playback.
        if getattr(image, 'is_animated', False):
            return 0
        original = ImageOps.exif_transpose(image).convert('RGBA' if 'A' in image.getbands() or 'transparency' in image.info else 'RGB')
        for width, name in missing.items():
            copy = original.copy()
            copy.thumbnail((width, max(1, round(original.height * width / original.width))), Image.Resampling.LANCZOS)
            data = BytesIO()
            copy.save(data, format='WEBP', quality=80, method=4)
            field.storage.save(name, ContentFile(data.getvalue()))
    return len(missing)


def image_url(field, width=400):
    if not field:
        return ''
    names = variant_names(field)
    name = names.get(int(width))
    if name and field.storage.exists(name):
        return field.storage.url(name)
    return field.url


def image_srcset(field):
    if not field:
        return ''
    names = variant_names(field)
    if not names:
        return ''
    try:
        source_width = field.width
        # Legacy JPEGs can rotate at display time; derived copies are transposed.
        if Path(field.name).suffix.lower() in {'.jpg', '.jpeg'}:
            with field.open('rb') as source, Image.open(source) as image:
                if image.getexif().get(274) in {5, 6, 7, 8}:
                    source_width = image.height
    except (OSError, ValueError):
        return ''
    available = {min(width, source_width): field.storage.url(name)
                 for width, name in names.items() if field.storage.exists(name)}
    return ', '.join(f'{url} {width}w' for width, url in available.items())
