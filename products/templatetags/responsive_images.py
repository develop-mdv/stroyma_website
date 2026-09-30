from django import template
from products.images import image_url, image_srcset

register = template.Library()
register.filter('image_url', image_url)
register.filter('image_srcset', image_srcset)
