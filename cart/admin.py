from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model          = CartItem
    extra          = 0
    readonly_fields = ['unit_price', 'total_price']
    raw_id_fields  = ['product']

    def unit_price(self, obj):
        return f'₹{obj.unit_price}'

    def total_price(self, obj):
        return f'₹{obj.total_price}'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display   = ['id', 'user', 'session_key', 'total_items', 'created_at']
    list_filter    = ['created_at']
    search_fields  = ['user__email', 'session_key']
    inlines        = [CartItemInline]
    readonly_fields = ['total_items', 'created_at', 'updated_at']