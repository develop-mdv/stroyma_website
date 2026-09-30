"""Subset public icon/currency fonts; administration keeps the vendor icon font.

Install requirements-build.txt, then run after changing public templates/icons.
"""
import hashlib
import re
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'static/vendor/fontawesome'
files = [*ROOT.glob('*/templates/**/*.html'), *ROOT.glob('templates/**/*.html'), *ROOT.glob('static/js/*.js')]
used = set()
for file in files:
    used.update(re.findall(r'\bfa-[a-z0-9-]+\b', file.read_text(encoding='utf-8')))
css = (VENDOR / 'css/all.min.css').read_text(encoding='utf-8')
unicodes = set()


def keep_rule(match):
    selectors, body = match.groups()
    glyph = re.search(r'content:"\\([a-fA-F0-9]+)"', body)
    if not glyph:
        return match.group(0)
    if used.intersection(re.findall(r'\bfa-[a-z0-9-]+\b', selectors)):
        unicodes.add(int(glyph[1], 16))
        return match.group(0)
    return ''


css = re.sub(r'([^{}]+)\{([^{}]+)\}', keep_rule, css)
css = re.sub(r'@font-face\{[^{}]+\}', '', css)
faces = [('fa-solid-900', 'Font Awesome 6 Free', 900),
         ('fa-regular-400', 'Font Awesome 6 Free', 400),
         ('fa-brands-400', 'Font Awesome 6 Brands', 400)]
for name, family, weight in faces:
    font = TTFont(VENDOR / f'webfonts/{name}.ttf', recalcTimestamp=False)
    options = subset.Options()
    options.flavor = 'woff2'
    worker = subset.Subsetter(options=options)
    worker.populate(unicodes=unicodes)
    worker.subset(font)
    # Give every generation a content-based URL for HTTP and service-worker caches.
    from io import BytesIO
    output = BytesIO()
    font.flavor = 'woff2'
    font.save(output)
    data = output.getvalue()
    filename = f'public-{name}-{hashlib.sha256(data).hexdigest()[:12]}.woff2'
    (VENDOR / 'webfonts' / filename).write_bytes(data)
    css += f'@font-face{{font-family:"{family}";font-style:normal;font-weight:{weight};font-display:swap;src:url(../webfonts/{filename}) format("woff2")}}'
    print(filename, len(data))
(VENDOR / 'css/public.min.css').write_text(css, encoding='utf-8')
print('public.min.css', len(css.encode()), 'bytes;', len(unicodes), 'glyphs')

# Prices must not download an 85 KB extended-Latin font for a single ruble sign.
inter = ROOT / 'static/vendor/fonts/inter'
font = TTFont(inter / 'files/inter-latin-ext-wght-normal.woff2', recalcTimestamp=False)
worker = subset.Subsetter(options=options)
worker.populate(unicodes=[0x20BD])
worker.subset(font)
output = BytesIO()
font.flavor = 'woff2'
font.save(output)
data = output.getvalue()
filename = f'inter-currency-{hashlib.sha256(data).hexdigest()[:12]}.woff2'
(inter / 'files' / filename).write_bytes(data)
css = (inter / 'wght.css').read_text(encoding='utf-8')
css = re.sub(r'/\* inter-currency-wght-normal \*/\s*@font-face\s*\{[^}]*\}', '', css).rstrip()
css = css.replace('U+20AD-20C0', 'U+20AD-20BC,U+20BE-20C0')
css += f'\n/* inter-currency-wght-normal */\n@font-face {{font-family: "Inter";font-style:normal;font-display:swap;font-weight:100 900;src:url(./files/{filename}) format("woff2-variations");unicode-range:U+20BD;}}\n'
(inter / 'wght.css').write_text(css, encoding='utf-8')
print(filename, len(data))
