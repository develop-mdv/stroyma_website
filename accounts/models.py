from datetime import timedelta

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.utils import timezone
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$', 
        message="Телефон должен быть в формате: '+999999999'. До 15 цифр."
    )
    phone = models.CharField(
        validators=[phone_regex], 
        max_length=20, 
        blank=True, 
        null=True, 
        verbose_name="Телефон"
    )
    
    delivery_address = models.TextField(blank=True, null=True, verbose_name="Адрес доставки")
    email_confirmed = models.BooleanField(default=False, verbose_name="Email подтвержден")
    confirmation_token = models.UUIDField(default=uuid.uuid4, verbose_name="Токен подтверждения")
    confirmation_token_created_at = models.DateTimeField(default=timezone.now, verbose_name="Дата создания токена")
    last_visit = models.DateTimeField(auto_now=True, verbose_name="Последний визит")
    bio = models.TextField(blank=True, null=True, verbose_name="О себе")
    
    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"

    def __str__(self):
        return f"Профиль {self.user.username}"
    
    def get_orders(self):
        """Получить все заказы пользователя"""
        from products.models import Order
        return Order.objects.filter(user=self.user).order_by('-created_at')
    
    def get_last_orders(self, count=5):
        """Получить последние заказы пользователя"""
        from products.models import Order
        return Order.objects.filter(user=self.user).order_by('-created_at')[:count]

    def token_is_valid(self, ttl_hours=72):
        """Проверяет, что токен подтверждения email не просрочен."""
        if not self.confirmation_token_created_at:
            return False
        return timezone.now() - self.confirmation_token_created_at <= timedelta(hours=ttl_hours)

    def rotate_confirmation_token(self, save=True):
        """Пересоздаёт токен подтверждения (одноразовость)."""
        self.confirmation_token = uuid.uuid4()
        self.confirmation_token_created_at = timezone.now()
        if save:
            self.save(update_fields=['confirmation_token', 'confirmation_token_created_at'])