from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Product


@receiver(pre_save, sender=Product)
def capture_original_price(sender, instance, **kwargs):
    """Store the price before the save so post_save can compare."""
    if not instance.pk:
        return
    try:
        instance._original_price = Product.objects.get(pk=instance.pk).price
    except Product.DoesNotExist:
        instance._original_price = None


@receiver(post_save, sender=Product)
def check_price_drop(sender, instance, created, **kwargs):
    """If the price dropped, notify wishlisted users via Celery."""
    if created:
        return
    original = getattr(instance, '_original_price', None)
    if original is None:
        return
    if instance.price < original:
        from notifications.tasks import send_price_drop_alert
        try:
            send_price_drop_alert.delay(
                instance.pk,
                float(original),
                float(instance.price),
            )
        except Exception:
            pass