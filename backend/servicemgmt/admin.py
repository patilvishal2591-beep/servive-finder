from django.contrib import admin
from .models import (
    ServiceBooking, Review, Payment, ServiceAvailability,
    ServiceImage, Notification
)


@admin.register(ServiceBooking)
class ServiceBookingAdmin(admin.ModelAdmin):
    list_display = [
        'booking_id', 'customer', 'provider', 'service', 'status',
        'booking_date', 'quoted_price', 'payment_status', 'created_at'
    ]
    list_filter = [
        'status', 'payment_status', 'created_at', 'booking_date',
        'service__category'
    ]
    search_fields = [
        'booking_id', 'customer__username', 'provider__username',
        'service__name', 'service_address'
    ]
    readonly_fields = [
        'booking_id', 'created_at', 'updated_at', 'confirmed_at',
        'completed_at', 'cancelled_at', 'distance_km', 'estimated_travel_time'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'booking_id', 'customer', 'provider', 'service', 'status'
            )
        }),
        ('Booking Details', {
            'fields': (
                'booking_date', 'estimated_duration', 'special_instructions'
            )
        }),
        ('Location', {
            'fields': (
                'service_address', 'service_latitude', 'service_longitude',
                'distance_km', 'estimated_travel_time'
            )
        }),
        ('Pricing & Payment', {
            'fields': (
                'quoted_price', 'final_price', 'payment_status'
            )
        }),
        ('Provider Response', {
            'fields': (
                'provider_notes', 'rejection_reason'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at', 'confirmed_at',
                'completed_at', 'cancelled_at'
            )
        })
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'customer', 'provider', 'service', 'rating',
        'quality_rating', 'is_verified', 'created_at'
    ]
    list_filter = [
        'rating', 'quality_rating', 'punctuality_rating',
        'communication_rating', 'value_rating', 'is_verified',
        'is_featured', 'created_at'
    ]
    search_fields = [
        'customer__username', 'provider__username', 'service__name',
        'title', 'comment'
    ]
    readonly_fields = ['created_at', 'updated_at', 'helpful_count']
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'booking', 'customer', 'provider', 'service'
            )
        }),
        ('Review Content', {
            'fields': (
                'rating', 'title', 'comment'
            )
        }),
        ('Detailed Ratings', {
            'fields': (
                'quality_rating', 'punctuality_rating',
                'communication_rating', 'value_rating'
            )
        }),
        ('Metadata', {
            'fields': (
                'is_verified', 'is_featured', 'helpful_count',
                'created_at', 'updated_at'
            )
        })
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'payment_id', 'customer', 'booking', 'amount',
        'payment_method', 'status', 'created_at'
    ]
    list_filter = [
        'payment_method', 'status', 'created_at'
    ]
    search_fields = [
        'payment_id', 'transaction_id', 'customer__username',
        'booking__booking_id'
    ]
    readonly_fields = [
        'payment_id', 'transaction_id', 'gateway_response',
        'created_at', 'processed_at', 'completed_at', 'failed_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'payment_id', 'booking', 'customer', 'amount'
            )
        }),
        ('Payment Details', {
            'fields': (
                'payment_method', 'status'
            )
        }),
        ('Transaction Details', {
            'fields': (
                'transaction_id', 'gateway_response', 'failure_reason'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'processed_at', 'completed_at', 'failed_at'
            )
        })
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']


@admin.register(ServiceAvailability)
class ServiceAvailabilityAdmin(admin.ModelAdmin):
    list_display = [
        'provider', 'get_day_of_week_display', 'start_time',
        'end_time', 'is_available', 'max_bookings_per_slot'
    ]
    list_filter = [
        'day_of_week', 'is_available', 'provider'
    ]
    search_fields = ['provider__username']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'provider', 'day_of_week', 'start_time', 'end_time'
            )
        }),
        ('Availability Settings', {
            'fields': (
                'is_available', 'max_bookings_per_slot'
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at', 'updated_at'
            )
        })
    )
    ordering = ['provider', 'day_of_week', 'start_time']


@admin.register(ServiceImage)
class ServiceImageAdmin(admin.ModelAdmin):
    list_display = [
        'service', 'caption', 'is_primary', 'uploaded_at'
    ]
    list_filter = [
        'is_primary', 'uploaded_at', 'service__category'
    ]
    search_fields = [
        'service__name', 'service__provider__username', 'caption'
    ]
    readonly_fields = ['uploaded_at']
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'service', 'image', 'caption'
            )
        }),
        ('Settings', {
            'fields': (
                'is_primary', 'uploaded_at'
            )
        })
    )
    date_hierarchy = 'uploaded_at'
    ordering = ['-uploaded_at']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'notification_type', 'title', 'is_read',
        'is_sent', 'created_at'
    ]
    list_filter = [
        'notification_type', 'is_read', 'is_sent', 'created_at'
    ]
    search_fields = [
        'user__username', 'title', 'message'
    ]
    readonly_fields = ['created_at', 'read_at']
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'user', 'notification_type', 'title', 'message'
            )
        }),
        ('Related Objects', {
            'fields': (
                'booking', 'review'
            )
        }),
        ('Status', {
            'fields': (
                'is_read', 'is_sent', 'created_at', 'read_at'
            )
        })
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = "Mark selected notifications as read"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = "Mark selected notifications as unread"
