from django.contrib import admin
from .models import Product, Order, OrderItem

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock')
    search_fields = ('name',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'created_at', 'total_cost')
    list_filter = ('status',)
    ordering = ['-created_at']
    fields = ['user', 'status', 'created_at']
    readonly_fields = ['created_at']

    def total_cost(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())
    total_cost.short_description = 'Сумма'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity')
    list_filter = ('order',)
