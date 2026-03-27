from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import Product, Category

@receiver(m2m_changed, sender=Product.categories.through)
def add_parent_categories(sender, instance, action, pk_set, **kwargs):
    print(f"Signal fired! {action} {pk_set}")
    if action == 'post_add':
        categories = Category.objects.filter(pk__in=pk_set)
        all_parents = set()
        for cat in categories:
            print("cat:", cat, "parents:", [p.name for p in cat.get_ancestors()])
            for ancestor in cat.get_ancestors():
                all_parents.add(ancestor)
        print("Будут добавлены родители с id:", [p.pk for p in all_parents])
        instance.categories.add(*all_parents)
        print("Итого категорий у товара:", list(instance.categories.values_list("name", flat=True)))
    if action == 'post_remove':
        print('sdkhfbshdbfsdbfsjkdf')
        categories = Category.objects.filter(pk__in=pk_set)
        all_parents = set()
        for cat in categories:
            print("cat:", cat, "parents:", [p.name for p in cat.get_ancestors()])
            for ancestor in cat.get_ancestors():
                all_parents.add(ancestor)
        print("Будут добавлены родители с id:", [p.pk for p in all_parents])
        instance.categories.add(*all_parents)
        print("Итого категорий у товара:", list(instance.categories.values_list("name", flat=True)))
        print('sdkhfbshdbfsdbfsjkdf')
