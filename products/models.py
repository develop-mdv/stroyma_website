import time

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from mptt.models import MPTTModel, TreeForeignKey
from django.utils.text import slugify
from django.urls import reverse
from django.utils.timezone import now
from django.core.cache import cache

from stroyma.validators import MaxFileSizeValidator, MAX_IMAGE_UPLOAD_BYTES

class Category(MPTTModel):
    """
    Модель для категорий товаров с поддержкой иерархии (вложенных категорий).
    Использует MPTT (Modified Preorder Tree Traversal) для эффективной работы 
    с древовидной структурой категорий.
    """
    name = models.CharField(max_length=100, verbose_name='Название категории')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='URL-имя')
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, 
                           related_name='children', verbose_name='Родительская категория')
    description = models.TextField(blank=True, verbose_name='Описание категории')
    meta_title = models.CharField(max_length=255, blank=True, verbose_name='SEO заголовок')
    meta_description = models.CharField(max_length=255, blank=True, verbose_name='SEO описание')
    image = models.ImageField(
        upload_to='category_images/', blank=True, null=True, verbose_name='Изображение категории',
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'gif']),
            MaxFileSizeValidator(MAX_IMAGE_UPLOAD_BYTES),
        ],
    )
    alt_text = models.CharField(max_length=255, blank=True, verbose_name='Альтернативный текст изображения')
    updated_at = models.DateTimeField(auto_now=True, null=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    class MPTTMeta:
        order_insertion_by = ['name']

    def clean(self):
        """
        Валидация данных перед сохранением:
        - Автоматическое создание slug из названия, если он не предоставлен
        - Проверка на уникальность slug
        """
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
        """
        Переопределение метода save для автоматического создания уникального slug.
        Если slug уже существует, добавляет числовой суффикс.
        """
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

    def get_total_products_count(self):
        """
        Возвращает общее количество товаров в данной категории 
        и во всех ее дочерних подкатегориях.
        """
        from django.db.models import Q
        return Product.objects.filter(
            Q(categories=self) | Q(categories__in=self.get_descendants())
        ).distinct().count()

    def __str__(self):
        return self.name

class Product(models.Model):
    """
    Модель товара с полной информацией о продукте, 
    включая SEO-параметры и связи с категориями.
    """
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name='URL-имя')
    description = models.TextField(verbose_name='Описание')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    image = models.ImageField(
        upload_to='products/', verbose_name='Изображение',
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'gif']),
            MaxFileSizeValidator(MAX_IMAGE_UPLOAD_BYTES),
        ],
    )
    stock = models.PositiveIntegerField(default=0, verbose_name='Остаток на складе')
    rating = models.PositiveIntegerField(default=5, verbose_name='Рейтинг')
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
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def clean(self):
        """
        Валидация данных перед сохранением:
        - Автоматическое создание slug из названия, если он не предоставлен
        - Проверка на уникальность slug
        """
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
        """
        Переопределение метода save для автоматического создания уникального slug.
        Если slug уже существует, добавляет числовой суффикс.
        """
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

    def add_categories_with_parents(self, categories):
        """
        Добавляет категории и их родительские категории к товару.
        
        Args:
            categories: QuerySet или список категорий для добавления
        """
        all_categories = set()
        
        # Собираем все категории и их родителей
        for category in categories:
            all_categories.add(category)
            # Добавляем всех родителей категории
            parent = category.parent
            while parent:
                all_categories.add(parent)
                parent = parent.parent
        
        # Добавляем все собранные категории к товару
        self.categories.add(*all_categories)

    @classmethod
    def get_popular_products(cls, count=5):
        """
        Получение популярных товаров с использованием кеширования для 
        оптимизации производительности. Популярность определяется по 
        количеству заказов и рейтингу.
        
        Args:
            count: Количество популярных товаров для возврата
            
        Returns:
            QuerySet с популярными товарами
        """
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
    ('new', 'Новый'),
    ('pending', 'В ожидании'),
    ('processing', 'Обработка'),
    ('shipped', 'Доставляется'),
    ('delivered', 'Доставлен'),
    ('completed', 'Завершен'),
    ('cancelled', 'Отменен'),
)

class Order(models.Model):
    """
    Модель заказа, связывающая пользователя с заказанными товарами.
    Имеет систему отслеживания статусов с ведением истории изменений.
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Пользователь')
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='new', verbose_name='Статус')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"

    def __str__(self):
        return f"Заказ #{self.id}"

    @property
    def total_cost(self):
        """
        Вычисляет общую стоимость заказа, суммируя цены всех входящих товаров
        с учетом их количества.
        """
        return sum(item.product.price * item.quantity for item in self.items.all())
        
    def save(self, *args, **kwargs):
        """
        Переопределение метода save для автоматического создания записи 
        в истории статусов при создании заказа или изменении его статуса.
        """
        # Проверяем, существует ли экземпляр в базе данных
        is_new = self.pk is None
        
        # Если не новый объект, сохраняем старый статус
        old_status = None
        if not is_new:
            old_status = Order.objects.get(pk=self.pk).status
            
        # Сохраняем объект
        super().save(*args, **kwargs)
        
        # Если это новый заказ или статус изменился, записываем в историю
        if is_new or old_status != self.status:
            OrderStatusHistory.objects.create(
                order=self,
                status=self.status
            )
            
    @property
    def total_items_count(self):
        """Вычисляет общее количество товаров в заказе"""
        return sum(item.quantity for item in self.items.all())

class OrderItem(models.Model):
    """
    Модель элемента заказа, связывает заказ с конкретным товаром
    и указывает его количество.
    """
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')

    class Meta:
        verbose_name = "Позиция заказа"
        verbose_name_plural = "Позиции заказов"

    @property
    def total_price(self):
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.product.name} ({self.quantity} шт.)"

class OrderContact(models.Model):
    """
    Контактная и адресная информация по заказу.
    Хранится отдельно от Order, чтобы не смешивать бизнес-состояние заказа
    и персональные данные клиента.
    """
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='contact', verbose_name='Заказ')
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    email = models.EmailField(verbose_name='Email')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    address = models.CharField(max_length=255, verbose_name='Адрес доставки')
    comment = models.TextField(blank=True, verbose_name='Комментарий')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Контакты заказа'
        verbose_name_plural = 'Контакты заказов'

    def __str__(self):
        return f"Контакты заказа #{self.order_id}"


class OrderStatusHistory(models.Model):
    """
    Модель для хранения истории изменений статусов заказа,
    позволяет отслеживать все изменения с временными метками.
    """
    order = models.ForeignKey(Order, related_name='status_history', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'История статуса заказа'
        verbose_name_plural = 'История статусов заказов'

    def __str__(self):
        return f"Статус '{self.get_status_display()}' для заказа #{self.order.id}"

class Cart(models.Model):
    """
    Модель корзины покупок, может быть привязана к пользователю
    или использоваться для анонимных покупателей.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Пользователь')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self):
        return f"Корзина для {self.user.username if self.user else 'Гостя'}"

class CartItem(models.Model):
    """
    Модель элемента корзины, связывает корзину с конкретным товаром
    и указывает его количество.
    """
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE, verbose_name='Корзина')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')

    class Meta:
        verbose_name = "Товар в корзине"
        verbose_name_plural = "Товары в корзинах"

    @property
    def total_price(self):
        """Вычисляет общую стоимость элемента корзины с учетом количества"""
        return self.quantity * self.product.price

    def __str__(self):
        return f"{self.product.name} ({self.quantity} шт.)"

class FacadeColor(models.Model):
    """
    Модель для хранения цветов фасадов, используемых для фильтрации
    и выбора при создании/редактировании товаров.
    """
    name = models.CharField(max_length=100, verbose_name='Название цвета')
    hex_code = models.CharField(max_length=7, verbose_name='Код цвета (HEX)')

    class Meta:
        verbose_name = "Цвет фасада"
        verbose_name_plural = "Цвета фасадов"

    def __str__(self):
        return self.name

class BaseTexture(models.Model):
    """
    Модель для хранения базовых текстур, используемых для фильтрации
    и выбора при создании/редактировании товаров.
    """
    name = models.CharField(max_length=100, verbose_name='Название текстуры')
    image = models.ImageField(
        upload_to='base_textures/', verbose_name='Изображение текстуры',
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'gif']),
            MaxFileSizeValidator(MAX_IMAGE_UPLOAD_BYTES),
        ],
    )

    class Meta:
        verbose_name = "Базовая текстура"
        verbose_name_plural = "Базовые текстуры"

    def __str__(self):
        return self.name

class ProductImage(models.Model):
    """
    Модель для хранения дополнительных изображений товара,
    позволяет создавать галерею изображений для каждого товара.
    """
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE, verbose_name='Товар')
    image = models.ImageField(
        upload_to='products/gallery/', verbose_name='Изображение',
        validators=[
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'gif']),
            MaxFileSizeValidator(MAX_IMAGE_UPLOAD_BYTES),
        ],
    )
    title = models.CharField(max_length=255, blank=True, verbose_name='Название')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        ordering = ['order']
        verbose_name = "Фото товара"
        verbose_name_plural = "Фото товаров"

    def __str__(self):
        return f"Изображение для {self.product.name}"