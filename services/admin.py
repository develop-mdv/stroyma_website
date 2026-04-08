from django.contrib import admin
from django.utils.html import format_html
from .models import Service, ServicePhoto, ServiceVideo
from django import forms


class ServicePhotoInline(admin.TabularInline):
    model = ServicePhoto
    extra = 1
    fields = ('image', 'title', 'description', 'order')


class ServiceVideoInline(admin.TabularInline):
    model = ServiceVideo
    extra = 1
    fields = ('video', 'title', 'description', 'order')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'title', 'photos_count', 'videos_count')
    list_display_links = ('image_preview', 'title')
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ('title', 'short_description')
    inlines = [ServicePhotoInline, ServiceVideoInline]
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'slug', 'short_description', 'description', 'image'),
            'description': 'Заполните название и описание услуги. URL заполнится автоматически.'
        }),
        ('Преимущества и SEO', {
            'fields': ('advantages', 'meta_title', 'meta_description'),
            'classes': ('collapse',),
            'description': 'Укажите преимущества (каждое с новой строки) и SEO данные.'
        }),
    )

    form = forms.modelform_factory(
        Service,
        fields='__all__',
        widgets={
            'slug': forms.TextInput(attrs={'class': 'slug-field'}),
        }
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" '
                'style="object-fit: cover; border-radius: 8px; '
                'border: 2px solid rgba(255,255,255,0.08);" />', obj.image.url
            )
        return format_html('<span style="color: rgba(255,255,255,0.2);">—</span>')
    image_preview.short_description = 'Фото'

    def photos_count(self, obj):
        count = obj.photos.count()
        if count:
            return format_html('<span style="font-weight:500;">{} фото</span>', count)
        return format_html('<span style="opacity:0.4;">—</span>')
    photos_count.short_description = 'Фотографии'

    def videos_count(self, obj):
        count = obj.videos.count()
        if count:
            return format_html('<span style="font-weight:500;">{} видео</span>', count)
        return format_html('<span style="opacity:0.4;">—</span>')
    videos_count.short_description = 'Видео'


@admin.register(ServicePhoto)
class ServicePhotoAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'service', 'title', 'order')
    list_display_links = ('image_preview', 'title')
    list_filter = ('service',)
    search_fields = ('title', 'description')
    ordering = ('service', 'order', 'id')

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" width="50" height="50" '
                'style="object-fit: cover; border-radius: 6px;" />', obj.image.url
            )
        return '—'
    image_preview.short_description = 'Превью'


@admin.register(ServiceVideo)
class ServiceVideoAdmin(admin.ModelAdmin):
    list_display = ('service', 'title', 'order')
    list_filter = ('service',)
    search_fields = ('title', 'description')
    ordering = ('service', 'order', 'id')
