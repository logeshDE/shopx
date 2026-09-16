from django.utils.text import slugify

def unique_slug(instance, value, slug_field='slug'):
    slug  = slugify(value)
    Model = instance.__class__
    candidate = slug
    count = 1
    while Model.objects.filter(**{slug_field: candidate}).exclude(pk=instance.pk).exists():
        candidate = f'{slug}-{count}'
        count += 1
    return candidate