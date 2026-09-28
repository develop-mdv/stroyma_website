import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


def snapshot_existing_items(apps, schema_editor):
    OrderItem = apps.get_model('products', 'OrderItem')
    batch = []
    for item in OrderItem.objects.select_related('product').iterator(chunk_size=500):
        item.product_name = item.product.name
        item.unit_price = item.product.price
        batch.append(item)
        if len(batch) >= 500:
            OrderItem.objects.bulk_update(batch, ['product_name', 'unit_price'])
            batch.clear()
    if batch:
        OrderItem.objects.bulk_update(batch, ['product_name', 'unit_price'])


class Migration(migrations.Migration):
    dependencies = [('products', '0015_alter_basetexture_image_alter_category_image_and_more')]

    operations = [
        migrations.AddField(
            model_name='orderitem', name='product_name',
            field=models.CharField(max_length=255, null=True, verbose_name='Название на момент заказа'),
        ),
        migrations.AddField(
            model_name='orderitem', name='unit_price',
            field=models.DecimalField(max_digits=10, decimal_places=2, null=True, verbose_name='Цена на момент заказа'),
        ),
        migrations.RunPython(snapshot_existing_items, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='orderitem', name='product_name',
            field=models.CharField(max_length=255, verbose_name='Название на момент заказа'),
        ),
        migrations.AlterField(
            model_name='orderitem', name='unit_price',
            field=models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена на момент заказа'),
        ),
        migrations.AlterField(
            model_name='orderitem', name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='products.product', verbose_name='Товар'),
        ),
        migrations.CreateModel(
            name='OrderNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('next_attempt_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('last_error', models.CharField(blank=True, max_length=200)),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification', to='products.order')),
            ],
            options={'verbose_name': 'Уведомление о заказе', 'verbose_name_plural': 'Уведомления о заказах'},
        ),
    ]
