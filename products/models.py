from django.db import models
from django.contrib.auth.models import User

class Product(models.Model):
    name = models.CharField(max_length=255)  # Название товара
    description = models.TextField()          # Описание товара
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Цена
    image = models.ImageField(upload_to='products/')  # Изображение товара
    stock = models.PositiveIntegerField(default=0)  # Количество на складе
    rating = models.PositiveIntegerField(default=5)  # Рейтинг товара (от 1 до 5)

    def __str__(self):
        return self.name

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