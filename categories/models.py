from django.db import models
from mptt.models import MPTTModel, TreeForeignKey
from products.utils import unique_slug


class Category(MPTTModel):
    name        = models.CharField(max_length=200)
    slug        = models.SlugField(unique=True, max_length=220)
    parent      = TreeForeignKey(
                      'self', on_delete=models.CASCADE,
                      null=True, blank=True, related_name='children'
                  )
    image       = models.ImageField(upload_to='categories/', blank=True)
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class MPTTMeta:
        order_insertion_by = ['name']

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('products:by-category', kwargs={'slug': self.slug})