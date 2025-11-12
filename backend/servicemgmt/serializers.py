from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from .models import (
    ServiceBooking, Review, Payment, ServiceAvailability, 
    ServiceImage, Notification
)
from usermgmt.models import ProviderService, ServiceCategory
from usermgmt.serializers import UserProfileSerializer, ProviderServiceSerializer
from decimal import Decimal
import math

User = get_user_model()


class ServiceBookingSerializer(serializers.ModelSerializer):
    """
    Serializer for service bookings
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    service_category = serializers.CharField(source='service.category.name', read_only=True)
    booking_id = serializers.UUIDField(read_only=True)
    can_be_reviewed = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = ServiceBooking
        fields = [
            'id', 'booking_id', 'customer', 'provider', 'service',
            'customer_name', 'provider_name', 'service_name', 'service_category',
            'booking_date', 'estimated_duration', 'special_instructions',
            'service_address', 'service_latitude', 'service_longitude',
            'distance_km', 'estimated_travel_time', 'status', 'quoted_price',
            'final_price', 'payment_status', 'created_at', 'updated_at',
            'confirmed_at', 'completed_at', 'cancelled_at', 'provider_notes',
            'rejection_reason', 'can_be_reviewed', 'is_active'
        ]
        read_only_fields = [
            'id', 'booking_id', 'created_at', 'updated_at', 'confirmed_at',
            'completed_at', 'cancelled_at', 'can_be_reviewed', 'is_active'
        ]

    def validate(self, data):
        """
        Validate booking data
        """
        # Ensure customer is not booking their own service
        if data.get('customer') == data.get('provider'):
            raise serializers.ValidationError("Cannot book your own service")
        
        # Ensure customer has customer role
        if data.get('customer') and not data.get('customer').is_customer:
            raise serializers.ValidationError("Only customers can make bookings")
        
        # Ensure provider has provider role
        if data.get('provider') and not data.get('provider').is_provider:
            raise serializers.ValidationError("Invalid service provider")
        
        # Validate booking date is in the future
        if data.get('booking_date') and data.get('booking_date') <= timezone.now():
            raise serializers.ValidationError("Booking date must be in the future")
        
        return data

    def calculate_distance(self, customer_lat, customer_lng, provider_lat, provider_lng):
        """
        Calculate distance between customer and provider using Haversine formula
        """
        if not all([customer_lat, customer_lng, provider_lat, provider_lng]):
            return None
        
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [customer_lat, customer_lng, provider_lat, provider_lng])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth's radius in kilometers
        
        return round(c * r, 2)

    def create(self, validated_data):
        """
        Create booking with distance calculation
        """
        # Calculate distance if coordinates are provided
        if all([
            validated_data.get('service_latitude'),
            validated_data.get('service_longitude'),
            validated_data.get('provider').latitude,
            validated_data.get('provider').longitude
        ]):
            distance = self.calculate_distance(
                float(validated_data['service_latitude']),
                float(validated_data['service_longitude']),
                float(validated_data['provider'].latitude),
                float(validated_data['provider'].longitude)
            )
            validated_data['distance_km'] = distance
            
            # Estimate travel time (assuming 30 km/h average speed)
            if distance:
                travel_time_hours = distance / 30
                travel_time_minutes = int(travel_time_hours * 60)
                validated_data['estimated_travel_time'] = f"{travel_time_minutes} minutes"
        
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for reviews and ratings
    """
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    service_name = serializers.CharField(source='service.name', read_only=True)
    booking_id = serializers.UUIDField(source='booking.booking_id', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'booking', 'customer', 'provider', 'service',
            'customer_name', 'provider_name', 'service_name', 'booking_id',
            'rating', 'title', 'comment', 'quality_rating', 'punctuality_rating',
            'communication_rating', 'value_rating', 'is_verified', 'is_featured',
            'helpful_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'provider', 'service', 'customer_name', 'provider_name',
            'service_name', 'booking_id', 'is_verified', 'is_featured',
            'helpful_count', 'created_at', 'updated_at'
        ]

    def validate(self, data):
        """
        Validate review data
        """
        booking = data.get('booking')
        
        # Ensure booking is completed
        if booking and booking.status != 'completed':
            raise serializers.ValidationError("Can only review completed bookings")
        
        # Ensure customer is the one who made the booking
        if booking and data.get('customer') != booking.customer:
            raise serializers.ValidationError("Can only review your own bookings")
        
        # Ensure booking doesn't already have a review
        if booking and hasattr(booking, 'review'):
            raise serializers.ValidationError("Booking already has a review")
        
        return data

    def create(self, validated_data):
        """
        Create review and update provider rating
        """
        booking = validated_data['booking']
        validated_data['provider'] = booking.provider
        validated_data['service'] = booking.service
        
        with transaction.atomic():
            review = super().create(validated_data)
            
            # Create notification for provider
            Notification.objects.create(
                user=review.provider,
                notification_type='review_received',
                title='New Review Received',
                message=f'You received a {review.rating}-star review from {review.customer.get_full_name()}',
                review=review
            )
            
            return review


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for payments
    """
    payment_id = serializers.UUIDField(read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    booking_id = serializers.UUIDField(source='booking.booking_id', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'booking', 'customer', 'customer_name', 'booking_id',
            'amount', 'payment_method', 'status', 'transaction_id',
            'gateway_response', 'failure_reason', 'created_at', 'processed_at',
            'completed_at', 'failed_at'
        ]
        read_only_fields = [
            'id', 'payment_id', 'customer_name', 'booking_id', 'status',
            'transaction_id', 'gateway_response', 'failure_reason',
            'created_at', 'processed_at', 'completed_at', 'failed_at'
        ]

    def validate(self, data):
        """
        Validate payment data
        """
        booking = data.get('booking')
        
        # Ensure booking exists and belongs to customer
        if booking and data.get('customer') != booking.customer:
            raise serializers.ValidationError("Can only pay for your own bookings")
        
        # Ensure booking is confirmed
        if booking and booking.status not in ['confirmed', 'completed']:
            raise serializers.ValidationError("Can only pay for confirmed bookings")
        
        # Ensure amount matches booking price
        if booking and data.get('amount') != booking.quoted_price:
            raise serializers.ValidationError("Payment amount must match booking price")
        
        return data


class ServiceAvailabilitySerializer(serializers.ModelSerializer):
    """
    Serializer for provider availability
    """
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)

    class Meta:
        model = ServiceAvailability
        fields = [
            'id', 'provider', 'day_of_week', 'day_name', 'start_time',
            'end_time', 'is_available', 'max_bookings_per_slot',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'day_name', 'created_at', 'updated_at']

    def validate(self, data):
        """
        Validate availability data
        """
        # Ensure end time is after start time
        if data.get('start_time') and data.get('end_time'):
            if data['end_time'] <= data['start_time']:
                raise serializers.ValidationError("End time must be after start time")
        
        return data


class ServiceImageSerializer(serializers.ModelSerializer):
    """
    Serializer for service images
    """
    class Meta:
        model = ServiceImage
        fields = [
            'id', 'service', 'image', 'caption', 'is_primary', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for notifications
    """
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'notification_type', 'title', 'message',
            'booking', 'review', 'is_read', 'is_sent', 'created_at', 'read_at'
        ]
        read_only_fields = [
            'id', 'user', 'notification_type', 'title', 'message',
            'booking', 'review', 'is_sent', 'created_at', 'read_at'
        ]


class ServiceSearchSerializer(serializers.Serializer):
    """
    Serializer for service search parameters
    """
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=True)
    radius = serializers.IntegerField(default=10, min_value=1, max_value=50)
    category = serializers.CharField(required=False)
    min_rating = serializers.DecimalField(max_digits=3, decimal_places=2, required=False, min_value=0, max_value=5)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=0)
    sort_by = serializers.ChoiceField(
        choices=['distance', 'rating', 'price', 'reviews'],
        default='distance'
    )


class ServiceWithDistanceSerializer(ProviderServiceSerializer):
    """
    Service serializer with distance information
    """
    distance_km = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    provider_rating = serializers.DecimalField(
        source='provider.provider_profile.average_rating',
        max_digits=3, decimal_places=2, read_only=True
    )
    provider_reviews = serializers.IntegerField(
        source='provider.provider_profile.total_reviews',
        read_only=True
    )
    is_nearby = serializers.BooleanField(read_only=True)

    class Meta:
        model = ProviderService
        fields = '__all__'
        read_only_fields = ('provider', 'created_at', 'updated_at')


class BookingStatsSerializer(serializers.Serializer):
    """
    Serializer for booking statistics
    """
    total_bookings = serializers.IntegerField()
    pending_bookings = serializers.IntegerField()
    confirmed_bookings = serializers.IntegerField()
    completed_bookings = serializers.IntegerField()
    cancelled_bookings = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)


class DashboardStatsSerializer(serializers.Serializer):
    """
    Serializer for dashboard statistics
    """
    # Customer stats
    total_bookings = serializers.IntegerField(required=False)
    active_bookings = serializers.IntegerField(required=False)
    completed_bookings = serializers.IntegerField(required=False)
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    
    # Provider stats
    total_services = serializers.IntegerField(required=False)
    pending_requests = serializers.IntegerField(required=False)
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2, required=False)
    total_reviews = serializers.IntegerField(required=False)
    
    # Common stats
    unread_notifications = serializers.IntegerField(required=False)
    recent_activity = serializers.ListField(required=False)
