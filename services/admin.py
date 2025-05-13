from django.contrib import admin
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
    list_display = ('title', 'slug')
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ('title', 'short_description')
    inlines = [ServicePhotoInline, ServiceVideoInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'short_description', 'description', 'image')
        }),
        ('Преимущества и SEO', {
            'fields': ('advantages', 'meta_title', 'meta_description')
        }),
    )
    
    form = forms.modelform_factory(
        Service,
        fields='__all__',
        widgets={
            'slug': forms.TextInput(attrs={'class': 'slug-field'}),
        }
    )

@admin.register(ServicePhoto)
class ServicePhotoAdmin(admin.ModelAdmin):
    list_display = ('service', 'title', 'order')
    list_filter = ('service',)
    search_fields = ('title', 'description')
    ordering = ('service', 'order', 'id')

@admin.register(ServiceVideo)
class ServiceVideoAdmin(admin.ModelAdmin):
    list_display = ('service', 'title', 'order')
    list_filter = ('service',)
    search_fields = ('title', 'description')
    ordering = ('service', 'order', 'id')
