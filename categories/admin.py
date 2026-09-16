from django.contrib import admin
from django.utils.html import mark_safe
from mptt.admin import MPTTModelAdmin
from .models import Category


@admin.register(Category)
class CategoryAdmin(MPTTModelAdmin):
    mptt_level_indent   = 24
    list_display        = ['tree_name', 'slug', 'parent', 'is_active', 'preview']
    list_editable       = ['is_active']
    prepopulated_fields = {'slug': ('name',)}
    search_fields       = ['name']

    def tree_name(self, obj):
        indent = '— ' * obj.level
        return f'{indent}{obj.name}'
    tree_name.short_description = 'Name'

    def preview(self, obj):
        if obj.image:
            return mark_safe(
                f'<img src="{obj.image.url}" width="40" height="40" '
                f'style="object-fit:cover;border-radius:4px">'
            )
        return '—'
    preview.short_description = 'Image'