from decimal import Decimal

SHIPPING_OPTIONS = {
    'standard': {
        'name':        'Standard Delivery',
        'description': '5–7 business days',
        'price':       Decimal('49.00'),
        'icon':        'bi-truck',
    },
    'express': {
        'name':        'Express Delivery',
        'description': '2–3 business days',
        'price':       Decimal('99.00'),
        'icon':        'bi-lightning-charge',
    },
    'overnight': {
        'name':        'Overnight Delivery',
        'description': 'Next business day',
        'price':       Decimal('199.00'),
        'icon':        'bi-rocket-takeoff',
    },
}

FREE_SHIPPING_ABOVE = Decimal('999.00')
GST_RATE            = Decimal('0.18')   # 18% GST