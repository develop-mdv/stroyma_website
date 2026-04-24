from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from .models import Product, Category


@receiver(m2m_changed, sender=Product.categories.through)
def add_parent_categories(sender, instance, action, pk_set, **kwargs):
    """При добавлении категорий к товару автоматически добавляет и все родительские."""
    if action != 'post_add' or not pk_set:
        return

    categories = Category.objects.filter(pk__in=pk_set)
    all_parents = set()
    for cat in categories:
        for ancestor in cat.get_ancestors():
            all_parents.add(ancestor)
    if all_parents:
        instance.categories.add(*all_parents)
