from django.db import models
from django.utils.text import slugify

class Service(models.Model):
    title = models.CharField(max_length=255, verbose_name='Название услуги')
    slug = models.SlugField(unique=True, verbose_name='URL', blank=True)
    short_description = models.TextField(verbose_name='Краткое описание')
    description = models.TextField(verbose_name='Подробное описание')
    image = models.ImageField(upload_to='services/', verbose_name='Изображение/иконка')
    advantages = models.TextField(blank=True, verbose_name='Преимущества (по одному на строку)')
    meta_title = models.CharField(max_length=255, blank=True, verbose_name='SEO Title')
    meta_description = models.CharField(max_length=255, blank=True, verbose_name='SEO Description')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
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
