import django_filters
from .models import Product, Category

class ProductFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    price_min = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    category = django_filters.ModelMultipleChoiceFilter(
        queryset=Category.objects.all(),
        field_name='categories',
        label='Категории'
    )

    class Meta:
        model = Product
        fields = ['name', 'price_min', 'price_max', 'category'] 