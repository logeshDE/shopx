from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from .models import Order


# ── Capture original values before save ───────────────────────

@receiver(pre_save, sender=Order)
def capture_original_order(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        orig = Order.objects.get(pk=instance.pk)
        instance._original_status         = orig.status
        instance._original_payment_status = orig.payment_status
    except Order.DoesNotExist:
        instance._original_status         = None
        instance._original_payment_status = None


# ── React to changes after save ───────────────────────────────

@receiver(post_save, sender=Order)
def handle_order_changes(sender, instance, created, **kwargs):
    from notifications.utils import create_notification
    from notifications.tasks import send_order_email

    def _dispatch(task_type):
        try:
            send_order_email.delay(instance.pk, task_type)
        except Exception:
            pass

    if created:
        create_notification(
            user    = instance.user,
            type    = 'order_placed',
            title   = f'Order #{instance.order_number} placed!',
            message = (
                f'Your order for ₹{instance.total:,.0f} is confirmed. '
                f'We\'ll notify you once payment clears.'
            ),
            link    = instance.get_absolute_url(),
        )
        _dispatch('order_placed')
        return

    orig_status  = getattr(instance, '_original_status',         None)
    orig_payment = getattr(instance, '_original_payment_status', None)

    # Payment confirmed
    if (orig_payment != instance.payment_status
            and instance.payment_status == 'paid'):
        create_notification(
            user    = instance.user,
            type    = 'payment_confirmed',
            title   = f'Payment confirmed — #{instance.order_number}',
            message = f'₹{instance.total:,.0f} received. Your order is now being processed.',
            link    = instance.get_absolute_url(),
        )
        _dispatch('payment_confirmed')

    # Order status changed
    if orig_status != instance.status:
        if instance.status == 'shipped':
            create_notification(
                user    = instance.user,
                type    = 'order_shipped',
                title   = f'Order #{instance.order_number} shipped!',
                message = f'Your order is on its way to {instance.address_city}.',
                link    = instance.get_absolute_url(),
            )
            _dispatch('order_shipped')

        elif instance.status == 'delivered':
            create_notification(
                user    = instance.user,
                type    = 'order_delivered',
                title   = f'Order #{instance.order_number} delivered!',
                message = 'Your order has been delivered. How was it? Leave a review!',
                link    = instance.get_absolute_url(),
            )
            _dispatch('order_delivered')

        elif instance.status == 'cancelled':
            refund_note = (
                ' A refund will be processed within 5–7 business days.'
                if instance.payment_status == 'paid' else ''
            )
            create_notification(
                user    = instance.user,
                type    = 'order_cancelled',
                title   = f'Order #{instance.order_number} cancelled',
                message = f'Your order has been cancelled.{refund_note}',
                link    = instance.get_absolute_url(),
            )
            _dispatch('order_cancelled')