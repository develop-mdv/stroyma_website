import csv
import io
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.utils import timezone

def export_orders_to_pdf(queryset):
    """Экспортирует заказы в PDF-файл"""
    # Создаем буфер для PDF
    buffer = io.BytesIO()
    
    # Создаем PDF-документ
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        title="Отчет по заказам"
    )
    
    # Стили для отчета
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']
    
    # Данные для таблицы
    elements = []
    
    # Заголовок
    title = Paragraph(f"Отчет по заказам от {timezone.now().strftime('%d.%m.%Y')}", title_style)
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Заголовки таблицы
    table_data = [['ID', 'Пользователь', 'Статус', 'Дата создания', 'Товары', 'Сумма']]
    
    # Добавляем данные заказов
    for order in queryset:
        items_list = ', '.join([f"{item.product.name} (x{item.quantity})" for item in order.items.all()])
        
        table_data.append([
            str(order.id),
            order.user.username if order.user else 'Гость',
            order.get_status_display(),
            timezone.localtime(order.created_at).strftime("%Y-%m-%d %H:%M:%S"),
            items_list,
            str(order.total_cost) + ' ₽'
        ])
    
    # Создаем таблицу
    table = Table(table_data, repeatRows=1)
    
    # Стиль таблицы
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
    
    # Добавляем таблицу к элементам
    elements.append(table)
    
    # Строим документ
    doc.build(elements)
    
    # Получаем значение из буфера
    pdf = buffer.getvalue()
    buffer.close()
    
    return pdf

def export_orders_csv(queryset):
    """Экспортирует заказы в CSV-файл (UTF-8 с BOM для корректного открытия в Excel)."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="orders_{timezone.now().strftime("%Y%m%d%H%M%S")}.csv"'

    response.write('\ufeff')  # BOM для корректного открытия кириллицы в Excel

    writer = csv.writer(response)
    writer.writerow(['ID', 'Пользователь', 'Статус', 'Дата создания', 'Товары', 'Сумма'])
    
    for order in queryset:
        items_list = ', '.join([f"{item.product.name} (x{item.quantity})" for item in order.items.all()])
        writer.writerow([
            order.id,
            order.user.username if order.user else 'Гость',
            order.get_status_display(),
            timezone.localtime(order.created_at).strftime("%Y-%m-%d %H:%M:%S"),
            items_list,
            order.total_cost
        ])
    
    return response 