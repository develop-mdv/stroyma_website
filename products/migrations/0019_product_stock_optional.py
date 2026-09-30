from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('products', '0018_product_source_key_product_unit_alter_product_image_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='stock',
            field=models.DecimalField(
                blank=True, decimal_places=3, default=0,
                help_text='Необязательно. Пустое поле означает 0; товар всё равно можно заказать.',
                max_digits=12,
                validators=[MinValueValidator(Decimal('0'))],
                verbose_name='Остаток на складе',
            ),
        ),
    ]
