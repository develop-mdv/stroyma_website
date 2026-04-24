from django.contrib.sitemaps import Sitemap
from products.models import Product, Category
from services.models import Service
from django.urls import reverse

class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.all()

    def lastmod(self, obj):
        return obj.updated_at
    
    def location(self, obj):
        return obj.get_absolute_url()

class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Category.objects.all()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return obj.get_absolute_url()

class ServiceSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Service.objects.all()

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('service_detail', args=[obj.slug])

class StaticViewSitemap(Sitemap):
    priority = 0.6
    changefreq = "monthly"

    def items(self):
        return ['product_list', 'about', 'contact', 'service_list', 'color_selection']

    def location(self, item):
        return reverse(item)

# Объединяем все карты сайта
sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
    'services': ServiceSitemap,
    'static': StaticViewSitemap,
} 