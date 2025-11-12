from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, CustomerProfile, ServiceProviderProfile, ServiceCategory, ProviderService


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin
    """
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_verified', 'is_active', 'date_joined')
    list_filter = ('role', 'is_verified', 'is_active', 'is_staff', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number')
    ordering = ('-date_joined',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone_number', 'address', 'latitude', 'longitude', 'profile_image', 'is_verified')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('role', 'phone_number', 'address', 'latitude', 'longitude', 'profile_image', 'is_verified')
        }),
    )


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """
    Customer Profile admin
    """
    list_display = ('user', 'preferred_contact_method', 'emergency_contact_name')
    list_filter = ('preferred_contact_method',)
    search_fields = ('user__username', 'user__email', 'emergency_contact_name')
    raw_id_fields = ('user',)


@admin.register(ServiceProviderProfile)
class ServiceProviderProfileAdmin(admin.ModelAdmin):
    """
    Service Provider Profile admin
    """
    list_display = ('user', 'business_name', 'years_of_experience', 'average_rating', 'total_reviews', 'is_background_verified')
    list_filter = ('is_background_verified', 'years_of_experience')
    search_fields = ('user__username', 'user__email', 'business_name', 'business_license')
    raw_id_fields = ('user',)
    readonly_fields = ('average_rating', 'total_reviews', 'total_jobs_completed')


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    """
    Service Category admin
    """
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'icon': ('name',)}


@admin.register(ProviderService)
class ProviderServiceAdmin(admin.ModelAdmin):
    """
    Provider Service admin
    """
    list_display = ('name', 'provider', 'category', 'base_price', 'price_unit', 'is_active', 'created_at')
    list_filter = ('category', 'price_unit', 'is_active', 'created_at')
    search_fields = ('name', 'provider__username', 'provider__email', 'description')
    raw_id_fields = ('provider',)
    list_select_related = ('provider', 'category')
