from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('products', '0019_product_stock_optional')]

    operations = [
        migrations.AddField(
            model_name='product',
            name='is_published',
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text='Снимите галочку, чтобы скрыть товар из каталога, поиска и заказов без удаления.',
                verbose_name='Показывать на сайте',
            ),
        ),
    ]
