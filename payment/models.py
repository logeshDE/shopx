from django.db import models


class Payment(models.Model):
    GATEWAY_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('cod',      'Cash on Delivery'),
    ]
    STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('completed', 'Completed'),
        ('failed',    'Failed'),
        ('refunded',  'Refunded'),
    ]

    order              = models.OneToOneField(
                             'orders.Order',
                             on_delete=models.CASCADE,
                             related_name='payment'
                         )
    gateway            = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    gateway_order_id   = models.CharField(max_length=200, blank=True)
    gateway_payment_id = models.CharField(max_length=200, blank=True)
    gateway_signature  = models.CharField(max_length=500, blank=True)
    amount             = models.DecimalField(max_digits=10, decimal_places=2)
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    raw_response       = models.JSONField(default=dict, blank=True)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.get_gateway_display()} — {self.get_status_display()} — ₹{self.amount}'