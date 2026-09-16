from django.db import models
from django.conf import settings
from django.db.models import Sum


class Cart(models.Model):
    user        = models.OneToOneField(
                      settings.AUTH_USER_MODEL,
                      on_delete=models.CASCADE,
                      null=True, blank=True,
                      related_name='cart'
                  )
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Cart({self.user or self.session_key})'

    @property
    def total_items(self):
        result = self.items.aggregate(total=Sum('quantity'))
        return result['total'] or 0

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.select_related('product'))

    @property
    def total_savings(self):
        return sum(item.discount_amount for item in self.items.select_related('product'))


class CartItem(models.Model):
    cart      = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product   = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    quantity  = models.PositiveIntegerField(default=1)
    added_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'product']

    def __str__(self):
        return f'{self.quantity} × {self.product.name}'

    @property
    def unit_price(self):
        return self.product.discounted_price

    @property
    def original_unit_price(self):
        return self.product.price

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    @property
    def discount_amount(self):
        return (self.original_unit_price - self.unit_price) * self.quantity