"""Утилиты приложения products (изображения и др.)."""

from __future__ import annotations

import csv
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def convert_image_bytes_to_webp(data: bytes, *, quality: int = 90, max_dim: int = 1920) -> bytes:
    """Конвертирует произвольное изображение (JPEG/PNG/WebP вход) в байты WebP."""
    try:
        from PIL import Image
    except ImportError as e:
        raise RuntimeError('Pillow не установлен') from e

    img = Image.open(BytesIO(data))
    img.load()

    if img.mode in ('RGBA', 'LA', 'P'):
        if img.mode == 'P' and 'transparency' in img.info:
            img = img.convert('RGBA')
        elif img.mode == 'P':
            img = img.convert('RGB')
        else:
            img = img.convert('RGBA')
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    w, h = img.size
    if max(w, h) > max_dim:
        ratio = max_dim / float(max(w, h))
        new_size = (max(1, int(w * ratio)), max(1, int(h * ratio)))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    buf = BytesIO()
    save_kwargs = {
        'format': 'WEBP',
        'quality': quality,
        'method': 6,
    }
    if img.mode == 'RGBA':
        save_kwargs['lossless'] = False

    img.save(buf, **save_kwargs)
    return buf.getvalue()


def compress_image_field_if_needed(
    instance,
    field_name: str,
    *,
    quality: int = 90,
    max_dim: int = 1920,
) -> None:
    """
    Конвертирует новую загрузку JPG/PNG в WebP (качество по умолчанию 90),
    при необходимости уменьшает длинную сторону до max_dim.

    Вызывать до super().save(). Обрабатывает только свежие загрузки (UploadedFile).
    GIF не трогаем (анимация). Уже WebP пропускаем.
    """
    fld = getattr(instance, field_name, None)
    if not fld:
        return
    if fld._committed:
        return

    inner = getattr(fld, 'file', None)
    if not isinstance(inner, UploadedFile):
        return

    name = getattr(fld, 'name', '') or ''
    lower = name.lower()
    if lower.endswith('.webp'):
        return
    if lower.endswith('.gif'):
        return

    inner.seek(0)
    data = inner.read()
    if not data:
        return

    try:
        webp_bytes = convert_image_bytes_to_webp(data, quality=quality, max_dim=max_dim)
    except Exception:
        inner.seek(0)
        return

    base = name.rsplit('/', 1)[-1]
    stem = base.rsplit('.', 1)[0] if '.' in base else base

    content = ContentFile(webp_bytes)
    # FieldFile.save() applies upload_to itself; passing the directory here
    # would create paths like products/products/image.webp.
    fld.save(f'{stem}.webp', content, save=False)



def export_orders_to_pdf(queryset):
    """Экспортирует заказы в PDF-файл"""
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        title='Отчет по заказам'
    )

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']

    elements = []
    title = Paragraph(f"Отчет по заказам от {timezone.now().strftime('%d.%m.%Y')}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))

    table_data = [['ID', 'Пользователь', 'Статус', 'Дата создания', 'Товары', 'Сумма']]

    for order in queryset:
        items_list = ', '.join([f'{item.product.name} (x{item.quantity})' for item in order.items.all()])

        table_data.append([
            str(order.id),
            order.user.username if order.user else 'Гость',
            order.get_status_display(),
            timezone.localtime(order.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            items_list,
            str(order.total_cost) + ' ₽'
        ])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
    ]))

    elements.append(table)
    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def export_orders_csv(queryset):
    """Экспортирует заказы в CSV (UTF-8 с BOM для Excel)."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="orders_{timezone.now().strftime("%Y%m%d%H%M%S")}.csv"'
    )

    response.write('\ufeff')

    writer = csv.writer(response)
    writer.writerow(['ID', 'Пользователь', 'Статус', 'Дата создания', 'Товары', 'Сумма'])

    for order in queryset:
        items_list = ', '.join([f'{item.product.name} (x{item.quantity})' for item in order.items.all()])
        writer.writerow([
            order.id,
            order.user.username if order.user else 'Гость',
            order.get_status_display(),
            timezone.localtime(order.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            items_list,
            order.total_cost
        ])

    return response
