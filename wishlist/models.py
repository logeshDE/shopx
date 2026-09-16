from django.db import models
from django.conf import settings


class Wishlist(models.Model):
    user       = models.OneToOneField(
                     settings.AUTH_USER_MODEL,
                     on_delete=models.CASCADE,
                     related_name='wishlist'
                 )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.email}\'s wishlist'


class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name='items')
    product  = models.ForeignKey('products.Product', on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['wishlist', 'product']
        ordering        = ['-added_at']

    def __str__(self):
        return f'{self.product.name} in {self.wishlist}'