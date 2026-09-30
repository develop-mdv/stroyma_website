from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from .models import Product, Category
from .images import build_variants
import logging


@receiver(post_save)
def build_public_image_variants(sender, instance, raw=False, **kwargs):
    if raw or sender._meta.label not in {
        'products.Product', 'products.Category', 'products.ProductImage',
        'services.Service', 'services.ServicePhoto',
    }:
        return
    try:
        build_variants(instance.image)
    except (OSError, ValueError):
        logging.getLogger(__name__).warning('Could not build image variants for %s #%s', sender._meta.label, instance.pk)


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
