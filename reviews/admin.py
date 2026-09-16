from django.contrib import admin
from django.utils.html import mark_safe
from .models import Review, ReviewImage


class ReviewImageInline(admin.TabularInline):
    model          = ReviewImage
    extra          = 0
    readonly_fields = ['preview']
    fields         = ['image', 'preview', 'order']

    def preview(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" width="60" height="60" '
                f'style="object-fit:cover;border-radius:4px">'
            )
        return '—'
    preview.short_description = 'Preview'


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display    = ['user', 'product', 'rating', 'title',
                       'verified_purchase', 'is_approved', 'created_at']
    list_filter     = ['rating', 'is_approved', 'verified_purchase', 'created_at']
    search_fields   = ['user__email', 'product__name', 'title']
    list_editable   = ['is_approved']
    readonly_fields = ['verified_purchase', 'created_at', 'updated_at']
    inlines         = [ReviewImageInline]
    raw_id_fields   = ['user', 'product']