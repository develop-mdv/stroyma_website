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

class ServiceExample(models.Model):
    service = models.ForeignKey(Service, related_name='examples', on_delete=models.CASCADE, verbose_name='Услуга')
    image = models.ImageField(upload_to='service_examples/', verbose_name='Фото примера работы')
    video = models.FileField(upload_to='service_examples/videos/', blank=True, null=True, verbose_name='Видео примера работы')

    def __str__(self):
        return f"Пример для {self.service.title}"
