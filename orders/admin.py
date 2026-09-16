from django.contrib import admin
from .models import Order, OrderItem, Coupon, CouponUsage, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model           = OrderItem
    extra           = 0
    readonly_fields = ['product_name', 'brand_name', 'price', 'quantity', 'total_price']
    fields          = readonly_fields

    def total_price(self, obj):
        return f'₹{obj.total_price:,.0f}'


class OrderStatusHistoryInline(admin.TabularInline):
    model           = OrderStatusHistory
    extra           = 0
    readonly_fields = ['status', 'note', 'created_by', 'created_at']
    fields          = readonly_fields
    can_delete      = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display    = ['order_number', 'user', 'status', 'payment_status',
                       'address_city', 'total', 'created_at']
    list_filter     = ['status', 'payment_status', 'created_at']
    search_fields   = ['order_number', 'user__email', 'address_full_name']
    list_editable   = ['status', 'payment_status']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    inlines         = [OrderItemInline, OrderStatusHistoryInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display  = ['code', 'discount_type', 'discount_value', 'min_purchase',
                     'used_count', 'max_uses', 'valid_to', 'is_active']
    list_editable = ['is_active']
    search_fields = ['code']


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display  = ['coupon', 'user', 'order', 'created_at']
    search_fields = ['coupon__code', 'user__email', 'order__order_number']
    readonly_fields = ['created_at']


@admin.register(OrderStatusHistory)
class OrderStatusHistoryAdmin(admin.ModelAdmin):
    list_display  = ['order', 'status', 'created_by', 'created_at']
    list_filter   = ['status']
    search_fields = ['order__order_number']
    readonly_fields = ['created_at']