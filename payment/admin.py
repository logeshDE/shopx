from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display   = ['order', 'gateway', 'status', 'amount',
                      'gateway_payment_id', 'created_at']
    list_filter    = ['gateway', 'status', 'created_at']
    search_fields  = ['order__order_number', 'gateway_payment_id', 'gateway_order_id']
    readonly_fields = ['created_at', 'updated_at']