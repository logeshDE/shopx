from django.contrib import admin
from django.utils.html import mark_safe
from .models import Brand, Product, ProductImage, Inventory


class ProductImageInline(admin.TabularInline):
    model          = ProductImage
    extra          = 3
    readonly_fields = ['preview']
    fields         = ['image', 'preview', 'alt_text', 'is_primary', 'order']

    def preview(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" width="60" height="60" '
                f'style="object-fit:cover;border-radius:4px">'
            )
        return '—'
    preview.short_description = 'Preview'


class InventoryInline(admin.StackedInline):
    model      = Inventory
    can_delete = False
    fields     = ['quantity', 'low_stock_threshold']


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display        = ['name', 'slug', 'is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields       = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display        = ['thumb', 'name', 'brand', 'category',
                           'price', 'discount_percent', 'stock_badge',
                           'is_active', 'is_featured', 'created_at']
    list_filter         = ['is_active', 'is_featured', 'category', 'brand']
    search_fields       = ['name', 'brand__name', 'category__name']
    list_editable       = ['is_active', 'is_featured']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields     = ['created_at', 'updated_at', 'discounted_price_display']
    inlines             = [ProductImageInline, InventoryInline]
    list_per_page       = 25
    fieldsets = [
        ('Basic info',     {'fields': ['name', 'slug', 'brand', 'category', 'description']}),
        ('Pricing',        {'fields': ['price', 'discount_percent', 'discounted_price_display']}),
        ('Specifications', {'fields': ['specifications']}),
        ('Visibility',     {'fields': ['is_active', 'is_featured']}),
        ('Timestamps',     {'fields': ['created_at', 'updated_at'], 'classes': ['collapse']}),
    ]

    def thumb(self, obj):
        img = obj.primary_image
        if img:
            return mark_safe(
                f'<img src="{img.image.url}" width="42" height="42" '
                f'style="object-fit:cover;border-radius:4px">'
            )
        return '—'
    thumb.short_description = ''

    def stock_badge(self, obj):
        status = obj.stock_status
        colours = {
            'in_stock':    ('#238636', 'In stock'),
            'low_stock':   ('#9e6a03', 'Low stock'),
            'out_of_stock':('#b62324', 'Out of stock'),
        }
        colour, label = colours.get(status, ('#888', status))
        try:
            qty = obj.inventory.quantity
            label = f'{label} ({qty})'
        except Inventory.DoesNotExist:
            pass
        return mark_safe(
            f'<span style="color:{colour};font-weight:500">{label}</span>'
        )
    stock_badge.short_description = 'Stock'

    def discounted_price_display(self, obj):
        return f'₹{obj.discounted_price:.2f}'
    discounted_price_display.short_description = 'Effective price'


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display  = ['product', 'quantity', 'low_stock_threshold', 'is_low_stock', 'updated_at']
    list_filter   = ['updated_at']
    search_fields = ['product__name']
    list_editable = ['quantity', 'low_stock_threshold']