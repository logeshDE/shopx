from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator

from categories.models import Category
from reviews.models import Review
from .filters import ProductFilter
from .models import Brand, Product


VALID_SORTS = {
    'newest':     '-created_at',
    'price_asc':  'price',
    'price_desc': '-price',
    'name':       'name',
    'top_rated':  '-avg_rating',    # NEW
}

REVIEW_FILTER = Q(reviews__is_approved=True)


def _annotate(qs):
    """Add avg_rating and review_count to any Product queryset."""
    return qs.annotate(
        avg_rating   = Avg('reviews__rating', filter=REVIEW_FILTER),
        review_count = Count('reviews',        filter=REVIEW_FILTER),
    )


def _filter_context(request, base_qs):
    f        = ProductFilter(request.GET, queryset=base_qs)
    products = _annotate(f.qs)

    if request.GET.get('in_stock'):
        products = products.filter(inventory__quantity__gt=0)

    sort_key    = request.GET.get('sort', 'newest')
    order_field = VALID_SORTS.get(sort_key, '-created_at')
    products    = products.order_by(order_field)

    paginator = Paginator(products, 12)
    page      = paginator.get_page(request.GET.get('page', 1))

    all_brands = (
        Brand.objects
        .filter(is_active=True)
        .annotate(product_count=Count(
            'products',
            filter=Q(products__is_active=True)
        ))
        .filter(product_count__gt=0)
    )

    return {
        'products':           page,
        'product_filter':     f,
        'all_brands':         all_brands,
        'all_categories':     Category.objects.filter(is_active=True, level=0)
                                              .prefetch_related('children'),
        'selected_brand_ids': request.GET.getlist('brand'),
        'sort_key':           sort_key,
        'total':              paginator.count,
        'q':                  request.GET.get('q', '').strip(),
        'in_stock':           request.GET.get('in_stock', ''),
        'min_price':          request.GET.get('min_price', ''),
        'max_price':          request.GET.get('max_price', ''),
        'discount':           request.GET.get('discount', ''),
        'discount_options':   [10, 20, 30, 50],
    }


def home_view(request):
    base_qs = _annotate(
        Product.objects.filter(is_active=True)
               .select_related('brand', 'category')
               .prefetch_related('images')
    )
    return render(request, 'home.html', {
        'featured':     base_qs.filter(is_featured=True)[:8],
        'new_arrivals': base_qs.order_by('-created_at')[:8],
        'deals':        base_qs.filter(discount_percent__gte=20)
                               .order_by('-discount_percent')[:8],
        'categories':   Category.objects.filter(is_active=True, level=0)
                                        .prefetch_related('children')[:8],
    })


def product_list(request):
    base_qs = Product.objects.filter(is_active=True).select_related(
        'brand', 'category'
    ).prefetch_related('images')
    ctx = _filter_context(request, base_qs)
    return render(request, 'products/list.html', ctx)


def product_by_category(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    desc_ids = category.get_descendants(include_self=True).values_list('id', flat=True)
    base_qs  = Product.objects.filter(
        is_active=True, category__in=desc_ids
    ).select_related('brand', 'category').prefetch_related('images')
    ctx = _filter_context(request, base_qs)
    ctx.update({
        'current_category': category,
        'breadcrumbs':      list(category.get_ancestors()) + [category],
    })
    return render(request, 'products/list.html', ctx)


def product_detail(request, slug):
    product = get_object_or_404(
        _annotate(Product.objects.filter(is_active=True)),
        slug=slug
    )
    images  = list(product.images.all())
    related = _annotate(
        Product.objects.filter(is_active=True, category=product.category)
                       .exclude(pk=product.pk)
                       .prefetch_related('images')
    )[:4]
    specs   = product.specifications if isinstance(product.specifications, dict) else {}

    reviews = Review.objects.filter(
        product=product, is_approved=True
    ).select_related('user').prefetch_related('images')

    # Rating breakdown: {5: 12, 4: 8, 3: 2, 2: 1, 1: 0}
    breakdown = {i: 0 for i in range(1, 6)}
    for r in reviews.values('rating').annotate(count=Count('rating')):
        breakdown[r['rating']] = r['count']

    # What the current user can do
    user_review  = None
    can_review   = False
    in_wishlist  = False

    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()
        if not user_review:
            from reviews.views import _has_purchased
            can_review = _has_purchased(request.user, product)

        try:
            in_wishlist = request.user.wishlist.items.filter(product=product).exists()
        except Exception:
            pass

    user_wishlist_ids = set()
    if request.user.is_authenticated:
        try:
            user_wishlist_ids = {product.pk} if in_wishlist else set()
        except Exception:
            pass

    return render(request, 'products/detail.html', {
        'product':          product,
        'images':           images,
        'related':          related,
        'specs':            specs,
        'reviews':          reviews,
        'breakdown':        breakdown,
        'user_review':      user_review,
        'can_review':       can_review,
        'in_wishlist':      in_wishlist,
        'user_wishlist_ids': user_wishlist_ids,
    })


def autocomplete_view(request):
    q    = request.GET.get('q', '').strip()
    data = {'products': [], 'categories': []}

    if len(q) < 2:
        return JsonResponse(data)

    products = _annotate(
        Product.objects.filter(is_active=True)
               .filter(Q(name__icontains=q) | Q(brand__name__icontains=q))
               .select_related('brand')
               .prefetch_related('images')
    )[:6]

    for p in products:
        img = p.primary_image
        data['products'].append({
            'name':           p.name,
            'url':            p.get_absolute_url(),
            'price':          f'₹{int(p.discounted_price):,}',
            'original_price': f'₹{int(p.price):,}' if p.discount_percent else '',
            'brand':          p.brand.name if p.brand else '',
            'image':          img.image.url if img else '',
            'discount':       p.discount_percent,
            'avg_rating':     round(float(p.avg_rating or 0), 1),
            'review_count':   p.review_count or 0,
        })

    for cat in Category.objects.filter(is_active=True, name__icontains=q)[:3]:
        data['categories'].append({'name': cat.name, 'url': cat.get_absolute_url()})

    return JsonResponse(data)