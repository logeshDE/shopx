from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('order_placed',      'Order Placed'),
        ('payment_confirmed', 'Payment Confirmed'),
        ('order_shipped',     'Order Shipped'),
        ('order_delivered',   'Order Delivered'),
        ('order_cancelled',   'Order Cancelled'),
        ('price_drop',        'Price Drop'),
        ('offer',             'Special Offer'),
        ('system',            'System'),
    ]

    ICON_MAP = {
        'order_placed':      'bi-bag-check',
        'payment_confirmed': 'bi-shield-check',
        'order_shipped':     'bi-truck',
        'order_delivered':   'bi-box-seam',
        'order_cancelled':   'bi-x-circle',
        'price_drop':        'bi-tags',
        'offer':             'bi-percent',
        'system':            'bi-info-circle',
    }

    COLOR_MAP = {
        'order_placed':      '#238636',
        'payment_confirmed': '#388bfd',
        'order_shipped':     '#79c0ff',
        'order_delivered':   '#3fb950',
        'order_cancelled':   '#f85149',
        'price_drop':        '#d29922',
        'offer':             '#d2a8ff',
        'system':            '#8b949e',
    }

    user       = models.ForeignKey(
                     settings.AUTH_USER_MODEL,
                     on_delete=models.CASCADE,
                     related_name='notifications'
                 )
    type       = models.CharField(max_length=25, choices=TYPE_CHOICES)
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    link       = models.CharField(max_length=500, blank=True)
    is_read    = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.title}'

    @property
    def icon(self):
        return self.ICON_MAP.get(self.type, 'bi-bell')

    @property
    def color(self):
        return self.COLOR_MAP.get(self.type, '#8b949e')