from django.db import models
from django.contrib.auth.models import User
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.text import slugify
from django.urls import reverse
from django.utils.timezone import now
from django.core.cache import cache

class Category(MPTTModel):
    name = models.CharField(max_length=100, verbose_name='Название категории')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='URL-имя')
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                           related_name='children', verbose_name='Родительская категория')
    description = models.TextField(blank=True, verbose_name='Описание категории')
    meta_title = models.CharField(max_length=255, blank=True, verbose_name='SEO заголовок')
    meta_description = models.CharField(max_length=255, blank=True, verbose_name='SEO описание')
    
    class MPTTMeta:
        order_insertion_by = ['name']
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.slug:
            self.slug = slugify(self.name)
            
        # Проверяем, существует ли уже категория с таким slug
        if Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError({
                'slug': f'Категория с URL "{self.slug}" уже существует. Пожалуйста, измените URL-имя.'
            })
        super().clean()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            
        # Добавляем суффикс, если slug уже существует
        original_slug = self.slug
        counter = 1
        while Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1
            
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('category_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name='URL-имя')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/')
    stock = models.PositiveIntegerField(default=0)
    rating = models.PositiveIntegerField(default=5)
    categories = models.ManyToManyField(Category, related_name='products', verbose_name='Категории', blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    meta_title = models.CharField(max_length=255, blank=True, verbose_name='SEO заголовок')
    meta_description = models.CharField(max_length=255, blank=True, verbose_name='SEO описание')
    keywords = models.CharField(max_length=255, blank=True, verbose_name='Ключевые слова')
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['price']),
            models.Index(fields=['created_at']),
            models.Index(fields=['slug']),
        ]
        ordering = ['-created_at']

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.slug:
            self.slug = slugify(self.name)
            
        # Проверяем, существует ли уже товар с таким slug
        if Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError({
                'slug': f'Товар с URL "{self.slug}" уже существует. Пожалуйста, измените URL-имя.'
            })
        super().clean()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            
        # Добавляем суффикс, если slug уже существует
        original_slug = self.slug
        counter = 1
        while Product.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1
            
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.name

    @classmethod
    def get_popular_products(cls, count=5):
        """Получение популярных товаров с использованием кеширования"""
        cache_key = f'popular_products_{count}'
        popular_products = cache.get(cache_key)
        
        if popular_products is None:
            # Если нет в кеше, получаем из базы и кешируем на 1 час
            from django.db.models import Count
            popular_products = cls.objects.annotate(
                order_count=Count('orderitem')
            ).order_by('-order_count', '-rating')[:count]
            
            cache.set(cache_key, popular_products, 60*60)  # 1 час
            
        return popular_products

ORDER_STATUS_CHOICES = (
    ('pending', 'В ожидании'),
    ('processing', 'Обработка'),
    ('shipped', 'Доставляется'),
    ('completed', 'Завершен'),
    ('canceled', 'Отменен'),
)

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Заказ #{self.id}"

    @property
    def total_cost(self):
        return sum(item.product.price * item.quantity for item in self.items.all())

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} ({self.quantity} шт.)"

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Корзина для {self.user.username if self.user else 'Гостя'}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.product.name} ({self.quantity} шт.)"

class FacadeColor(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название цвета')
    hex_code = models.CharField(max_length=7, verbose_name='Код цвета (HEX)')

    def __str__(self):
        return self.name

class BaseTexture(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название текстуры')
    image = models.ImageField(upload_to='base_textures/', verbose_name='Изображение текстуры')

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/gallery/')
    title = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Изображение для {self.product.name}"