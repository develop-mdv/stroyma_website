from django.contrib import admin
from mptt.admin import MPTTModelAdmin
from .models import Product, Category, Order, OrderItem, Cart, CartItem, FacadeColor, BaseTexture, ProductImage

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    list_display = ('name', 'parent', 'slug', 'get_products_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    list_filter = ('parent',)
    mptt_level_indent = 20
    expand_tree_by_default = True

    def get_products_count(self, obj):
        return obj.products.count()
    get_products_count.short_description = 'Количество товаров'

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock', 'rating')
    list_filter = ('categories', 'rating')
    search_fields = ('name', 'description')
    filter_horizontal = ('categories',)
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