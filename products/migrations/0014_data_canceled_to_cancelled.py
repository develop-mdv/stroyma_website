from django.db import migrations


def canceled_to_cancelled(apps, schema_editor):
    Order = apps.get_model('products', 'Order')
    OrderStatusHistory = apps.get_model('products', 'OrderStatusHistory')
    Order.objects.filter(status='canceled').update(status='cancelled')
    OrderStatusHistory.objects.filter(status='canceled').update(status='cancelled')


def cancelled_to_canceled(apps, schema_editor):
    Order = apps.get_model('products', 'Order')
    OrderStatusHistory = apps.get_model('products', 'OrderStatusHistory')
    Order.objects.filter(status='cancelled').update(status='canceled')
    OrderStatusHistory.objects.filter(status='cancelled').update(status='canceled')


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0013_category_updated_at_alter_order_status_and_more'),
    ]

    operations = [
        migrations.RunPython(canceled_to_cancelled, cancelled_to_canceled),
    ]
