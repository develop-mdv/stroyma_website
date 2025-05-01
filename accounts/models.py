from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    delivery_address = models.TextField(blank=True, null=True, verbose_name="Адрес доставки")

    def __str__(self):
        return f"Профиль {self.user.username}"