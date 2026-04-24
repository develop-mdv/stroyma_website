from django.db import models
from django.utils.text import slugify
from django.core.exceptions import ValidationError

class Service(models.Model):
    title = models.CharField(max_length=255, verbose_name='Название услуги')
    slug = models.SlugField(unique=True, verbose_name='URL', blank=True)
    short_description = models.TextField(verbose_name='Краткое описание')
    description = models.TextField(verbose_name='Подробное описание')
    image = models.ImageField(upload_to='services/', verbose_name='Изображение/иконка')
    advantages = models.TextField(blank=True, verbose_name='Преимущества (по одному на строку)')
    meta_title = models.CharField(max_length=255, blank=True, verbose_name='SEO Title')
    meta_description = models.CharField(max_length=255, blank=True, verbose_name='SEO Description')
    created_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, null=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = "Услуга"
        verbose_name_plural = "Услуги"

    def clean(self):
        if not self.slug:
            self.slug = slugify(self.title)
            
        # Проверяем, существует ли уже услуга с таким slug
        if Service.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError({
                'slug': f'Услуга с URL "{self.slug}" уже существует. Пожалуйста, измените URL-имя.'
            })
        super().clean()

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
            
        # Добавляем суффикс, если slug уже существует
        original_slug = self.slug
        counter = 1
        while Service.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class ServicePhoto(models.Model):
    service = models.ForeignKey(Service, related_name='photos', on_delete=models.CASCADE, verbose_name='Услуга')
    image = models.ImageField(upload_to='service_photos/', verbose_name='Фото примера работы')
    title = models.CharField(max_length=255, blank=True, verbose_name='Название фото')
    description = models.TextField(blank=True, verbose_name='Описание фото')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок отображения')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Фото услуги'
        verbose_name_plural = 'Фото услуг'

    def __str__(self):
        return f"Фото для {self.service.title} - {self.title or 'Без названия'}"

class ServiceVideo(models.Model):
    service = models.ForeignKey(Service, related_name='videos', on_delete=models.CASCADE, verbose_name='Услуга')
    video = models.FileField(upload_to='service_videos/', verbose_name='Видео примера работы')
    title = models.CharField(max_length=255, blank=True, verbose_name='Название видео')
    description = models.TextField(blank=True, verbose_name='Описание видео')
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок отображения')

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Видео услуги'
        verbose_name_plural = 'Видео услуг'

    def __str__(self):
        return f"Видео для {self.service.title} - {self.title or 'Без названия'}"
