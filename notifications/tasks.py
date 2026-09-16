from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


def _html_email(heading, body_html, action_url='', action_label=''):
    """Minimal branded HTML email layout."""
    action_block = ''
    if action_url and action_label:
        action_block = f'''
        <div style="text-align:center;margin:24px 0">
          <a href="{action_url}"
             style="background:#238636;color:#fff;padding:10px 24px;
                    border-radius:6px;text-decoration:none;font-weight:500">
            {action_label}
          </a>
        </div>'''
    return f'''
    <div style="font-family:system-ui,sans-serif;max-width:520px;
                margin:0 auto;background:#0d1117;color:#e6edf3;
                border-radius:8px;overflow:hidden">
      <div style="background:#238636;padding:20px 24px">
        <h1 style="margin:0;font-size:22px;color:#fff">ShopX</h1>
      </div>
      <div style="padding:24px">
        <h2 style="font-size:18px;margin:0 0 12px;color:#e6edf3">{heading}</h2>
        {body_html}
        {action_block}
        <p style="font-size:12px;color:#8b949e;margin-top:24px;border-top:1px solid #30363d;padding-top:12px">
          This email was sent by ShopX. If you have questions, contact support@shopx.com.
        </p>
      </div>
    </div>'''


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_order_email(self, order_id, event_type):
    """
    Sends a transactional email for order lifecycle events.
    event_type: order_placed | payment_confirmed | order_shipped |
                order_delivered | order_cancelled
    """
    try:
        from orders.models import Order
        order = Order.objects.select_related('user').get(pk=order_id)
    except Exception as exc:
        raise self.retry(exc=exc)

    user  = order.user
    email = user.email
    name  = user.first_name or email

    subjects = {
        'order_placed':      f'Order #{order.order_number} placed — ShopX',
        'payment_confirmed': f'Payment confirmed for #{order.order_number} — ShopX',
        'order_shipped':     f'Your order #{order.order_number} is on its way! — ShopX',
        'order_delivered':   f'Order #{order.order_number} delivered — ShopX',
        'order_cancelled':   f'Order #{order.order_number} cancelled — ShopX',
    }

    bodies = {
        'order_placed': (
            f'Order placed!',
            f'<p>Hi {name},</p>'
            f'<p>We\'ve received your order <strong>#{order.order_number}</strong> for '
            f'<strong>₹{order.total:,.0f}</strong>. We\'ll notify you once payment is confirmed.</p>'
            f'<p style="color:#8b949e;font-size:13px">Items: {order.items.count()} | '
            f'Shipping to: {order.address_city}, {order.address_state}</p>',
            f'/orders/{order.order_number}/', 'View Order',
        ),
        'payment_confirmed': (
            'Payment confirmed!',
            f'<p>Hi {name},</p>'
            f'<p>Your payment of <strong>₹{order.total:,.0f}</strong> for order '
            f'<strong>#{order.order_number}</strong> has been confirmed. '
            f'We\'re now processing your order.</p>',
            f'/orders/{order.order_number}/', 'Track Order',
        ),
        'order_shipped': (
            'Your order is on its way!',
            f'<p>Hi {name},</p>'
            f'<p>Great news! Order <strong>#{order.order_number}</strong> has been shipped '
            f'and is on its way to <strong>{order.address_city}</strong>.</p>'
            f'<p style="color:#8b949e;font-size:13px">Shipping method: {order.shipping_method}</p>',
            f'/orders/{order.order_number}/', 'Track Order',
        ),
        'order_delivered': (
            'Order delivered!',
            f'<p>Hi {name},</p>'
            f'<p>Your order <strong>#{order.order_number}</strong> has been delivered. '
            f'We hope you love your purchase! Please take a moment to leave a review.</p>',
            f'/orders/{order.order_number}/', 'Leave a Review',
        ),
        'order_cancelled': (
            'Order cancelled',
            f'<p>Hi {name},</p>'
            f'<p>Your order <strong>#{order.order_number}</strong> has been cancelled.</p>'
            f'{"<p>A refund will be processed within 5–7 business days.</p>" if order.payment_status == "paid" else ""}',
            '/', 'Continue Shopping',
        ),
    }

    if event_type not in bodies:
        return

    heading, body_html, action_url, action_label = bodies[event_type]
    html_message = _html_email(heading, body_html, action_url, action_label)

    try:
        send_mail(
            subject      = subjects[event_type],
            message      = f'{heading}\n\nHi {name},\nYour order #{order.order_number}.',
            from_email   = settings.DEFAULT_FROM_EMAIL,
            recipient_list = [email],
            html_message = html_message,
            fail_silently = False,
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_price_drop_alert(self, product_id, old_price, new_price):
    """
    Sends price-drop emails to all users who have wishlisted the product.
    """
    try:
        from products.models import Product
        from wishlist.models import WishlistItem

        product  = Product.objects.get(pk=product_id)
        w_items  = WishlistItem.objects.filter(
                       product=product
                   ).select_related('wishlist__user')

        if not w_items.exists():
            return

        savings_pct = round((float(old_price) - float(new_price)) / float(old_price) * 100)
        subject     = f'Price drop! {product.name} is now ₹{int(new_price):,} — ShopX'
        body_html   = (
            f'<p>An item on your wishlist just dropped in price!</p>'
            f'<div style="background:#161b22;border:1px solid #30363d;'
            f'border-radius:8px;padding:16px;margin:12px 0">'
            f'<p style="margin:0;font-weight:500;color:#e6edf3">{product.name}</p>'
            f'<p style="margin:6px 0 0;font-size:13px;color:#8b949e">'
            f'<span style="text-decoration:line-through">₹{int(old_price):,}</span> → '
            f'<span style="color:#3fb950;font-weight:bold">₹{int(new_price):,}</span> '
            f'<span style="background:#3d2b00;color:#d29922;padding:1px 6px;'
            f'border-radius:4px;font-size:11px">-{savings_pct}% off</span></p>'
            f'</div>'
        )
        html_message = _html_email(
            '🏷️ Price drop alert!', body_html,
            product.get_absolute_url(), 'Grab It Now',
        )

        from notifications.utils import create_notification
        for item in w_items:
            user = item.wishlist.user
            try:
                send_mail(
                    subject        = subject,
                    message        = f'Price drop on {product.name}: ₹{int(new_price):,}',
                    from_email     = settings.DEFAULT_FROM_EMAIL,
                    recipient_list = [user.email],
                    html_message   = html_message,
                    fail_silently  = False,
                )
            except Exception:
                pass  # Don't retry the whole task if one email fails

            create_notification(
                user    = user,
                type    = 'price_drop',
                title   = f'Price drop: {product.name[:50]}',
                message = f'Now ₹{int(new_price):,} (was ₹{int(old_price):,}) — {savings_pct}% off!',
                link    = product.get_absolute_url(),
            )

    except Exception as exc:
        raise self.retry(exc=exc)