from django.contrib import admin
from .models import Service, ServiceExample

class ServiceExampleInline(admin.TabularInline):
    model = ServiceExample
    extra = 1

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug')
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ('title', 'short_description')
    inlines = [ServiceExampleInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'short_description', 'description', 'image')
        }),
        ('Преимущества и SEO', {
            'fields': ('advantages', 'meta_title', 'meta_description')
        }),
    )

@admin.register(ServiceExample)
class ServiceExampleAdmin(admin.ModelAdmin):
    list_display = ('service', 'image', 'video')
