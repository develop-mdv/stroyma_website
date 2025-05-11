from django.contrib import admin
from .models import Product, Order, OrderItem, Cart, CartItem, FacadeColor, BaseTexture, ProductImage

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'rating')
    search_fields = ('name', 'description')
    list_filter = ('stock',)
    ordering = ['name']
    inlines = [ProductImageInline]

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'created_at', 'total_cost')
    list_filter = ('status',)
    search_fields = ('user__username',)
    ordering = ['-created_at']
    fields = ['user', 'status', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']

    def total_cost(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())
    total_cost.short_description = 'Сумма'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity')
    list_filter = ('order',)
    search_fields = ('product__name',)

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'total_items')
    search_fields = ('user__username',)

    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = 'Товаров в корзине'

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity')
    list_filter = ('cart',)
    search_fields = ('product__name',)

@admin.register(FacadeColor)
class FacadeColorAdmin(admin.ModelAdmin):
    list_display = ('name', 'hex_code')
    search_fields = ('name', 'hex_code')
    ordering = ['name']

@admin.register(BaseTexture)
class BaseTextureAdmin(admin.ModelAdmin):
    list_display = ('name', 'image')
    search_fields = ('name',)
    ordering = ['name']