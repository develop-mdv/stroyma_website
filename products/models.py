from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=255)  # Название товара
    description = models.TextField()          # Описание товара
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Цена
    image = models.ImageField(upload_to='products/')  # Изображение товара
    stock = models.PositiveIntegerField(default=0)  # Количество на складе

    def __str__(self):
        return self.name