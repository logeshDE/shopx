import django_filters
from django.db.models import Q
from .models import Product, Brand


class ProductFilter(django_filters.FilterSet):
    q = django_filters.CharFilter(
        method='search_filter',
        label='Search',
    )
    min_price = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='gte',
        label='Min Price',
    )
    max_price = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='lte',
        label='Max Price',
    )
    brand = django_filters.ModelMultipleChoiceFilter(
        queryset=Brand.objects.filter(is_active=True),
        label='Brand',
    )
    discount = django_filters.NumberFilter(
        field_name='discount_percent',
        lookup_expr='gte',
        label='Min Discount %',
    )

    class Meta:
        model  = Product
        fields = []

    def search_filter(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value)        |
            Q(description__icontains=value) |
            Q(brand__name__icontains=value) |
            Q(category__name__icontains=value)
        ).distinct()