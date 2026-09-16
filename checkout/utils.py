from decimal import Decimal
from .constants import SHIPPING_OPTIONS, FREE_SHIPPING_ABOVE, GST_RATE


def calculate_totals(cart, shipping_method='standard', coupon_discount=Decimal('0')):
    subtotal = cart.subtotal

    free_shipping = subtotal >= FREE_SHIPPING_ABOVE
    shipping_cost = Decimal('0') if free_shipping else SHIPPING_OPTIONS[shipping_method]['price']

    taxable_amount  = max(subtotal - coupon_discount, Decimal('0'))
    tax             = (taxable_amount * GST_RATE).quantize(Decimal('0.01'))
    total           = taxable_amount + shipping_cost + tax

    return {
        'subtotal':        subtotal,
        'coupon_discount': coupon_discount,
        'shipping_cost':   shipping_cost,
        'tax':             tax,
        'total':           total,
        'free_shipping':   free_shipping,
        'free_remaining':  max(FREE_SHIPPING_ABOVE - subtotal, Decimal('0')),
    }