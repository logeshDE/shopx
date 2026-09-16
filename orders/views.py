from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from .models import Order, OrderStatusHistory


# ── Order list ─────────────────────────────────────────────────

@login_required
def order_list(request):
    orders = request.user.orders.prefetch_related('items', 'payment').all()

    # Optional status filter
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)

    return render(request, 'orders/order_list.html', {
        'orders':         orders,
        'status_filter':  status,
        'status_choices': Order.STATUS,
    })


# ── Order detail ───────────────────────────────────────────────

@login_required
def order_detail(request, order_number):
    order   = get_object_or_404(Order, order_number=order_number, user=request.user)
    items   = order.items.all()
    history = order.status_history.all()

    return render(request, 'orders/order_detail.html', {
        'order':       order,
        'items':       items,
        'history':     history,
        'order_steps': ['pending', 'processing', 'shipped', 'delivered'],
    })


# ── Cancel order ───────────────────────────────────────────────

@login_required
@require_POST
def cancel_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if not order.can_cancel:
        messages.error(request, 'This order cannot be cancelled.')
        return redirect('orders:detail', order_number=order_number)

    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Please provide a cancellation reason.')
        return redirect('orders:detail', order_number=order_number)

    # Restore inventory
    for item in order.items.select_related('product__inventory'):
        if item.product:
            try:
                inv           = item.product.inventory
                inv.quantity += item.quantity
                inv.save(update_fields=['quantity', 'updated_at'])
            except Exception:
                pass

    order.status        = 'cancelled'
    order.cancel_reason = reason
    order.save(update_fields=['status', 'cancel_reason', 'updated_at'])

    OrderStatusHistory.objects.create(
        order      = order,
        status     = 'cancelled',
        note       = f'Cancelled by customer. Reason: {reason}',
        created_by = request.user,
    )

    # Mark for refund if already paid (handled manually / via M6 notification)
    if order.payment_status == 'paid':
        messages.success(
            request,
            f'Order #{order_number} cancelled. '
            'A refund will be processed within 5–7 business days.'
        )
    else:
        messages.success(request, f'Order #{order_number} has been cancelled.')

    return redirect('orders:detail', order_number=order_number)


# ── Return order ───────────────────────────────────────────────

@login_required
@require_POST
def return_order(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    if not order.can_return:
        messages.error(request, 'This order is not eligible for return.')
        return redirect('orders:detail', order_number=order_number)

    reason = request.POST.get('reason', '').strip()
    if not reason:
        messages.error(request, 'Please provide a return reason.')
        return redirect('orders:detail', order_number=order_number)

    order.status        = 'returned'
    order.return_reason = reason
    order.save(update_fields=['status', 'return_reason', 'updated_at'])

    OrderStatusHistory.objects.create(
        order      = order,
        status     = 'returned',
        note       = f'Return requested by customer. Reason: {reason}',
        created_by = request.user,
    )

    messages.success(
        request,
        f'Return request for #{order_number} submitted. '
        'Our team will contact you within 24 hours.'
    )
    return redirect('orders:detail', order_number=order_number)


# ── Invoice PDF ────────────────────────────────────────────────

@login_required
def download_invoice(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, user=request.user)
    items = order.items.all()

    html = render_to_string('orders/invoice.html', {
        'order': order,
        'items': items,
    }, request=request)

    try:
        from xhtml2pdf import pisa
        buffer   = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=buffer)
        if not pisa_status.err:
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="ShopX-Invoice-{order_number}.pdf"'
            )
            return response
    except ImportError:
        pass

    # Fallback: return printable HTML if xhtml2pdf fails or is not installed
    return HttpResponse(html)