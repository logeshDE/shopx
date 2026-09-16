from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Review(models.Model):
    product           = models.ForeignKey(
                            'products.Product',
                            on_delete=models.CASCADE,
                            related_name='reviews'
                        )
    user              = models.ForeignKey(
                            settings.AUTH_USER_MODEL,
                            on_delete=models.CASCADE,
                            related_name='reviews'
                        )
    rating            = models.PositiveSmallIntegerField(
                            validators=[MinValueValidator(1), MaxValueValidator(5)]
                        )
    title             = models.CharField(max_length=200)
    body              = models.TextField()
    verified_purchase = models.BooleanField(default=False)
    is_approved       = models.BooleanField(default=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['product', 'user']
        ordering        = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.product.name} ({self.rating}★)'


class ReviewImage(models.Model):
    review   = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image    = models.ImageField(upload_to='reviews/%Y/%m/')
    order    = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f'Image for review #{self.review.pk}'