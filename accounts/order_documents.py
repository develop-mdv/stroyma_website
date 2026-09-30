"""Документы для одного заказа покупателя."""

from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _register_fonts():
    candidates = (
        (
            Path(settings.BASE_DIR) / 'static/fonts/DejaVuSans.ttf',
            Path(settings.BASE_DIR) / 'static/fonts/DejaVuSans-Bold.ttf',
        ),
        (
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
            Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
        ),
        (
            Path('C:/Windows/Fonts/arial.ttf'),
            Path('C:/Windows/Fonts/arialbd.ttf'),
        ),
    )
    for regular, bold in candidates:
        if regular.is_file() and bold.is_file():
            if 'OrderRegular' not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont('OrderRegular', str(regular)))
                pdfmetrics.registerFont(TTFont('OrderBold', str(bold)))
            return 'OrderRegular', 'OrderBold'
    raise RuntimeError('Для PDF заказа нужен шрифт DejaVu Sans или Arial с поддержкой кириллицы.')


def _text(value):
    return escape(str(value or '—')).replace('\n', '<br/>')


def _money(value):
    return f'{value:,.2f}'.replace(',', ' ').replace('.', ',') + ' ₽'


def build_order_pdf(order):
    """Возвращает PDF с данными одного заказа, без элементов сайта."""
    regular_font, bold_font = _register_fonts()
    dark = colors.HexColor('#15231c')
    green = colors.HexColor('#1a3628')
    muted = colors.HexColor('#65736b')
    border = colors.HexColor('#d9e0da')
    paper = colors.HexColor('#f3f6f3')

    title = ParagraphStyle('OrderTitle', fontName=bold_font, fontSize=21, leading=26, textColor=dark)
    brand = ParagraphStyle('OrderBrand', fontName=bold_font, fontSize=12, leading=15, textColor=green)
    label = ParagraphStyle('OrderLabel', fontName=bold_font, fontSize=8, leading=11, textColor=muted)
    body = ParagraphStyle('OrderBody', fontName=regular_font, fontSize=9, leading=14, textColor=dark)
    body_bold = ParagraphStyle('OrderBodyBold', parent=body, fontName=bold_font)
    header = ParagraphStyle('OrderTableHeader', parent=body_bold, fontSize=8, textColor=colors.white)
    right = ParagraphStyle('OrderRight', parent=body, alignment=TA_RIGHT)
    right_bold = ParagraphStyle('OrderRightBold', parent=body_bold, alignment=TA_RIGHT)
    center = ParagraphStyle('OrderCenter', parent=body, alignment=TA_CENTER)

    created = timezone.localtime(order.created_at).strftime('%d.%m.%Y в %H:%M')
    contact = getattr(order, 'contact', None)
    customer = contact.name if contact and contact.name else '—'

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, title=f'Заказ №{order.id} — СТРОЙМА',
        author='СТРОЙМА', leftMargin=14 * mm, rightMargin=14 * mm,
        topMargin=15 * mm, bottomMargin=18 * mm,
    )
    story = [
        Paragraph('СТРОЙМА', brand),
        Spacer(1, 8 * mm),
        Paragraph(f'Заказ №{order.id}', title),
        Spacer(1, 2 * mm),
        Paragraph(f'Оформлен {created} · Статус: {_text(order.get_status_display())}', body),
        Spacer(1, 9 * mm),
    ]

    details = [
        [Paragraph('ПОКУПАТЕЛЬ', label), Paragraph('ДОСТАВКА', label)],
        [
            Paragraph('<br/>'.join((
                _text(customer),
                _text(contact.phone if contact else None),
                _text(contact.email if contact else None),
            )), body),
            Paragraph(_text(contact.address if contact and contact.address else 'Самовывоз / не указан'), body),
        ],
    ]
    details_table = Table(details, colWidths=[91 * mm, 91 * mm])
    details_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), paper),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 3),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
    ]))
    story.extend([details_table, Spacer(1, 8 * mm)])

    if contact and contact.comment:
        story.extend([
            Paragraph('КОММЕНТАРИЙ К ЗАКАЗУ', label),
            Spacer(1, 2 * mm),
            Paragraph(_text(contact.comment), body),
            Spacer(1, 7 * mm),
        ])

    story.extend([Paragraph('Состав заказа', body_bold), Spacer(1, 3 * mm)])
    rows = [[
        Paragraph('Товар', header), Paragraph('Цена', header),
        Paragraph('Кол-во', header), Paragraph('Сумма', header),
    ]]
    for item in order.items.all():
        rows.append([
            Paragraph(_text(item.product_name), body),
            Paragraph(_money(item.unit_price), right),
            Paragraph(str(item.quantity), center),
            Paragraph(_money(item.total_price), right_bold),
        ])
    if len(rows) == 1:
        rows.append([Paragraph('В заказе нет товаров.', body), '', '', ''])

    items_table = Table(rows, colWidths=[91 * mm, 29 * mm, 24 * mm, 38 * mm], repeatRows=1, hAlign='LEFT')
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), green),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, paper]),
    ]))
    story.extend([items_table, Spacer(1, 8 * mm)])

    total_table = Table([[
        Paragraph('ИТОГО К ОПЛАТЕ', label),
        Paragraph(_money(order.total_cost), right_bold),
    ]], colWidths=[91 * mm, 91 * mm])
    total_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1, green),
        ('TOPPADDING', (0, 0), (-1, 0), 11),
    ]))
    story.append(total_table)

    def footer(canvas, pdf_doc):
        canvas.saveState()
        canvas.setStrokeColor(border)
        canvas.line(14 * mm, 13 * mm, A4[0] - 14 * mm, 13 * mm)
        canvas.setFont(regular_font, 8)
        canvas.setFillColor(muted)
        canvas.drawString(14 * mm, 9 * mm, 'СТРОЙМА · Документ по заказу')
        canvas.drawRightString(A4[0] - 14 * mm, 9 * mm, f'Страница {pdf_doc.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
