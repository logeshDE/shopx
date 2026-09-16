from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile, Address

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False

class AddressInline(admin.TabularInline):
    model = Address
    extra = 0
    readonly_fields = ['created_at']

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ['email', 'first_name', 'last_name', 'is_email_verified', 'is_staff', 'date_joined']
    list_filter   = ['is_email_verified', 'is_staff', 'is_superuser']
    search_fields = ['email', 'first_name', 'last_name']
    ordering      = ['-date_joined']
    inlines       = [ProfileInline, AddressInline]
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra', {'fields': ('phone', 'is_email_verified')}),
    )

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display  = ['user', 'full_name', 'city', 'state', 'is_default']
    list_filter   = ['address_type', 'is_default', 'state']
    search_fields = ['user__email', 'full_name', 'city']