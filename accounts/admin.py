from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'delivery_address')
    search_fields = ('user__username', 'phone', 'delivery_address')