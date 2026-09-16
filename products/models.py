from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from categories.models import Category
from .utils import unique_slug


class Brand(models.Model):
    name        = models.CharField(max_length=200)
    slug        = models.SlugField(unique=True, max_length=220)
    logo        = models.ImageField(upload_to='brands/', blank=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)


class Product(models.Model):
    name             = models.CharField(max_length=300)
    slug             = models.SlugField(unique=True, max_length=350)
    brand            = models.ForeignKey(
                           Brand, on_delete=models.SET_NULL,
                           null=True, blank=True, related_name='products'
                       )
    category         = models.ForeignKey(
                           Category, on_delete=models.SET_NULL,
                           null=True, related_name='products'
                       )
    description      = models.TextField()
    specifications   = models.JSONField(
                           default=dict, blank=True,
                           help_text='e.g. {"RAM": "8GB", "Storage": "128GB"}'
                       )
    price            = models.DecimalField(
                           max_digits=10, decimal_places=2,
                           validators=[MinValueValidator(0)]
                       )
    discount_percent = models.PositiveIntegerField(
                           default=0,
                           validators=[MaxValueValidator(100)]
                       )
    is_active        = models.BooleanField(default=True)
    is_featured      = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    # ── Computed properties ─────────────────────────────────────

    @property
    def discounted_price(self):
        if self.discount_percent:
            return self.price * (Decimal('100') - Decimal(self.discount_percent)) / Decimal('100')
        return self.price

    @property
    def savings(self):
        return self.price - self.discounted_price

    @property
    def primary_image(self):
        return self.images.filter(is_primary=True).first() or self.images.first()

    @property
    def in_stock(self):
        try:
            return self.inventory.quantity > 0
        except Inventory.DoesNotExist:
            return False

    @property
    def stock_status(self):
        try:
            inv = self.inventory
            if inv.quantity == 0:
                return 'out_of_stock'
            if inv.quantity <= inv.low_stock_threshold:
                return 'low_stock'
            return 'in_stock'
        except Inventory.DoesNotExist:
            return 'out_of_stock'

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('products:detail', kwargs={'slug': self.slug})


class ProductImage(models.Model):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image      = models.ImageField(upload_to='products/%Y/%m/')
    alt_text   = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-is_primary']

    def __str__(self):
        return f'{self.product.name} — image {self.order}'

    def save(self, *args, **kwargs):
        # Only one primary image per product
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class Inventory(models.Model):
    product             = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory')
    quantity            = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Inventories'

    def __str__(self):
        return f'{self.product.name} — {self.quantity} units'

    @property
    def is_low_stock(self):
        return 0 < self.quantity <= self.low_stock_threshold