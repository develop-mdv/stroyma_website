from django.db import models
from django.contrib.auth.models import User
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    delivery_address = models.TextField(blank=True, null=True, verbose_name="Адрес доставки")
    email_confirmed = models.BooleanField(default=False, verbose_name="Email подтвержден")
    confirmation_token = models.UUIDField(default=uuid.uuid4, verbose_name="Токен подтверждения")

    def __str__(self):
        return f"Профиль {self.user.username}"