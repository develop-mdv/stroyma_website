from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from products.models import Product


class Command(BaseCommand):
    help = 'Проверить заполненность информации для покупателей без изменения каталога.'

    def add_arguments(self, parser):
        parser.add_argument('--strict', action='store_true', help='Ошибка, если опубликованы незаполненные карточки.')

    def handle(self, *args, **options):
        products = Product.published.all()
        fields = ('manufacturer_info', 'origin', 'safety_info', 'warranty_info')
        missing = Q()
        self.stdout.write(f'Опубликованных товаров: {products.count()}')
        for field in fields:
            missing |= Q(**{field: ''})
            self.stdout.write(f'{Product._meta.get_field(field).verbose_name}: не заполнено у {products.filter(**{field: ""}).count()}')
        incomplete = products.filter(missing)
        count = incomplete.count()
        self.stdout.write(f'Карточек, требующих проверки документов изготовителя: {count}')
        for product in incomplete.order_by('pk')[:10]:
            self.stdout.write(f'  #{product.pk}: {product.name}')
        self.stdout.write('Это проверка заполненности полей. Достоверность, достаточность сведений, маркировку, права на изображения и инфраструктуру проверяют отдельно по LEGAL_AUDIT_RU.md.')
        if options['strict'] and count:
            raise CommandError('Перед продажей заполните обязательную информацию по документам изготовителя.')
