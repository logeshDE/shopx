import random
import string
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


# ── Coupon ─────────────────────────────────────────────────────

class Coupon(models.Model):
    DISCOUNT_TYPE = [
        ('percent', 'Percentage'),
        ('fixed',   'Fixed Amount'),
    ]

    code           = models.CharField(max_length=50, unique=True)
    discount_type  = models.CharField(max_length=10, choices=DISCOUNT_TYPE, default='percent')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_purchase   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_discount   = models.DecimalField(
                         max_digits=10, decimal_places=2,
                         null=True, blank=True,
                         help_text='Cap on percentage discounts. Leave blank for no cap.'
                     )
    valid_from     = models.DateTimeField(null=True, blank=True)
    valid_to       = models.DateTimeField(null=True, blank=True)
    max_uses       = models.PositiveIntegerField(
                         null=True, blank=True,
                         help_text='Leave blank for unlimited uses.'
                     )
    used_count     = models.PositiveIntegerField(default=0)
    per_user_limit = models.PositiveIntegerField(
                         default=1,
                         help_text='Max times one user can use this coupon.'
                     )
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        symbol = '%' if self.discount_type == 'percent' else '₹'
        return f'{self.code} ({symbol}{self.discount_value})'

    def validate(self, user=None, subtotal=None):
        """
        Returns (is_valid: bool, error_message: str).
        Pass user and subtotal for complete validation.
        """
        now = timezone.now()

        if not self.is_active:
            return False, 'This coupon is inactive.'
        if self.valid_from and now < self.valid_from:
            return False, 'This coupon is not yet active.'
        if self.valid_to and now > self.valid_to:
            return False, 'This coupon has expired.'
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False, 'This coupon has reached its usage limit.'

        if subtotal is not None and subtotal < self.min_purchase:
            return False, f'Minimum purchase of ₹{self.min_purchase:,.0f} required.'

        if user is not None:
            user_uses = CouponUsage.objects.filter(coupon=self, user=user).count()
            if user_uses >= self.per_user_limit:
                return False, f'You have already used this coupon {self.per_user_limit} time(s).'

        return True, ''

    def calculate_discount(self, subtotal):
        if self.discount_type == 'percent':
            discount = (subtotal * self.discount_value / 100).quantize(Decimal('0.01'))
            if self.max_discount:
                discount = min(discount, self.max_discount)
            return discount
        return min(self.discount_value, subtotal).quantize(Decimal('0.01'))


class CouponUsage(models.Model):
    coupon     = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    order      = models.ForeignKey('Order', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['coupon', 'user', 'order']

    def __str__(self):
        return f'{self.user.email} used {self.coupon.code} on {self.order.order_number}'


# ── Order ──────────────────────────────────────────────────────

class Order(models.Model):
    STATUS = [
        ('pending',    'Pending'),
        ('processing', 'Processing'),
        ('shipped',    'Shipped'),
        ('delivered',  'Delivered'),
        ('cancelled',  'Cancelled'),
        ('returned',   'Returned'),
    ]
    PAYMENT_STATUS = [
        ('pending',  'Payment Pending'),
        ('paid',     'Paid'),
        ('failed',   'Payment Failed'),
        ('refunded', 'Refunded'),
    ]

    user           = models.ForeignKey(
                         settings.AUTH_USER_MODEL,
                         on_delete=models.SET_NULL,
                         null=True, related_name='orders'
                     )
    order_number   = models.CharField(max_length=20, unique=True)
    status         = models.CharField(max_length=20, choices=STATUS,         default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')

    # Address snapshot — locked at order time
    address_full_name = models.CharField(max_length=100)
    address_phone     = models.CharField(max_length=15)
    address_line1     = models.CharField(max_length=255)
    address_line2     = models.CharField(max_length=255, blank=True)
    address_city      = models.CharField(max_length=100)
    address_state     = models.CharField(max_length=100)
    address_pincode   = models.CharField(max_length=10)
    address_country   = models.CharField(max_length=100)

    # Financials
    subtotal        = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total           = models.DecimalField(max_digits=10, decimal_places=2)

    shipping_method  = models.CharField(max_length=50, blank=True)
    coupon_code      = models.CharField(max_length=50, blank=True)
    payment_id       = models.CharField(max_length=200, blank=True)

    # Cancel / Return
    cancel_reason = models.TextField(blank=True)
    return_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order {self.order_number}'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_number()
        super().save(*args, **kwargs)

    def _generate_number(self):
        while True:
            num = 'SX' + ''.join(random.choices(string.digits, k=8))
            if not Order.objects.filter(order_number=num).exists():
                return num

    @property
    def can_cancel(self):
        return self.status in ('pending', 'processing') and self.payment_status != 'refunded'

    @property
    def can_return(self):
        return self.status == 'delivered'

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('orders:detail', kwargs={'order_number': self.order_number})


class OrderItem(models.Model):
    order        = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product      = models.ForeignKey(
                       'products.Product',
                       on_delete=models.SET_NULL,
                       null=True
                   )
    # Price snapshot
    product_name = models.CharField(max_length=300)
    product_slug = models.SlugField(max_length=350)
    brand_name   = models.CharField(max_length=200, blank=True)
    image_url    = models.CharField(max_length=500, blank=True)
    price        = models.DecimalField(max_digits=10, decimal_places=2)
    quantity     = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.quantity} × {self.product_name}'

    @property
    def total_price(self):
        return self.price * self.quantity


# ── Order status history ───────────────────────────────────────

class OrderStatusHistory(models.Model):
    order      = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_history')
    status     = models.CharField(max_length=20, choices=Order.STATUS)
    note       = models.TextField(blank=True)
    created_by = models.ForeignKey(
                     settings.AUTH_USER_MODEL,
                     on_delete=models.SET_NULL,
                     null=True, blank=True
                 )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.order.order_number} → {self.status} at {self.created_at:%d %b %Y %H:%M}'