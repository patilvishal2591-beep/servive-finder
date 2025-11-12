from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count, Sum, F
from django.utils import timezone
from django.shortcuts import get_object_or_404
from decimal import Decimal
import math

from .models import (
    ServiceBooking, Review, Payment, ServiceAvailability,
    ServiceImage, Notification
)
from .serializers import (
    ServiceBookingSerializer, ReviewSerializer, PaymentSerializer,
    ServiceAvailabilitySerializer, ServiceImageSerializer,
    NotificationSerializer, ServiceSearchSerializer,
    ServiceWithDistanceSerializer, BookingStatsSerializer,
    DashboardStatsSerializer
)
from usermgmt.models import ProviderService, ServiceCategory
from usermgmt.permissions import IsCustomer, IsProvider, IsOwnerOrReadOnly

User = get_user_model()


class ServiceSearchView(APIView):
    """
    Search for services based on location and filters
    """
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def post(self, request):
        serializer = ServiceSearchSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            latitude = float(data['latitude'])
            longitude = float(data['longitude'])
            radius = data.get('radius', 10)
            category = data.get('category')
            min_rating = data.get('min_rating')
            max_price = data.get('max_price')
            sort_by = data.get('sort_by', 'distance')

            # Get all active services
            services = ProviderService.objects.filter(
                is_active=True,
                provider__is_active=True,
                provider__latitude__isnull=False,
                provider__longitude__isnull=False
            ).select_related('provider', 'category', 'provider__provider_profile')

            # Filter by category
            if category:
                services = services.filter(category__name__icontains=category)

            # Filter by rating
            if min_rating:
                services = services.filter(
                    provider__provider_profile__average_rating__gte=min_rating
                )

            # Filter by price
            if max_price:
                services = services.filter(base_price__lte=max_price)

            # Calculate distances and filter by radius
            nearby_services = []
            distant_services = []

            for service in services:
                distance = self.calculate_distance(
                    latitude, longitude,
                    float(service.provider.latitude),
                    float(service.provider.longitude)
                )
                
                # Add distance to service object
                service.distance_km = distance
                service.is_nearby = distance <= radius

                if distance <= radius:
                    nearby_services.append(service)
                elif distance <= 50:  # Show distant services up to 50km
                    distant_services.append(service)

            # Sort services
            def sort_key(service):
                if sort_by == 'distance':
                    return service.distance_km
                elif sort_by == 'rating':
                    return -service.provider.provider_profile.average_rating
                elif sort_by == 'price':
                    return service.base_price
                elif sort_by == 'reviews':
                    return -service.provider.provider_profile.total_reviews
                return service.distance_km

            nearby_services.sort(key=sort_key)
            distant_services.sort(key=sort_key)

            # Serialize results
            nearby_serializer = ServiceWithDistanceSerializer(nearby_services, many=True)
            distant_serializer = ServiceWithDistanceSerializer(distant_services, many=True)

            return Response({
                'nearby_services': nearby_serializer.data,
                'distant_services': distant_serializer.data,
                'search_params': {
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius': radius,
                    'total_nearby': len(nearby_services),
                    'total_distant': len(distant_services)
                }
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def calculate_distance(self, lat1, lng1, lat2, lng2):
        """
        Calculate distance using Haversine formula
        """
        # Convert to radians
        lat1, lng1, lat2, lng2 = map(math.radians, [lat1, lng1, lat2, lng2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Earth's radius in kilometers
        
        return round(c * r, 2)


class ServiceBookingListCreateView(generics.ListCreateAPIView):
    """
    List and create service bookings
    """
    serializer_class = ServiceBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_customer:
            return ServiceBooking.objects.filter(customer=user).order_by('-created_at')
        elif user.is_provider:
            return ServiceBooking.objects.filter(provider=user).order_by('-created_at')
        return ServiceBooking.objects.none()

    def perform_create(self, serializer):
        # Only customers can create bookings
        if not self.request.user.is_customer:
            raise permissions.PermissionDenied("Only customers can create bookings")
        
        booking = serializer.save(customer=self.request.user)
        
        # Create notification for provider
        Notification.objects.create(
            user=booking.provider,
            notification_type='booking_request',
            title='New Booking Request',
            message=f'You have a new booking request from {booking.customer.get_full_name()}',
            booking=booking
        )


class ServiceBookingDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update service booking
    """
    serializer_class = ServiceBookingSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_customer:
            return ServiceBooking.objects.filter(customer=user)
        elif user.is_provider:
            return ServiceBooking.objects.filter(provider=user)
        return ServiceBooking.objects.none()

    def perform_update(self, serializer):
        booking = self.get_object()
        old_status = booking.status
        new_status = serializer.validated_data.get('status', old_status)
        
        # Update booking
        booking = serializer.save()
        
        # Send notifications on status change
        if old_status != new_status:
            if new_status == 'confirmed':
                Notification.objects.create(
                    user=booking.customer,
                    notification_type='booking_confirmed',
                    title='Booking Confirmed',
                    message=f'Your booking with {booking.provider.get_full_name()} has been confirmed',
                    booking=booking
                )
            elif new_status == 'completed':
                Notification.objects.create(
                    user=booking.customer,
                    notification_type='booking_completed',
                    title='Booking Completed',
                    message=f'Your booking with {booking.provider.get_full_name()} has been completed',
                    booking=booking
                )
            elif new_status == 'cancelled':
                Notification.objects.create(
                    user=booking.customer,
                    notification_type='booking_cancelled',
                    title='Booking Cancelled',
                    message=f'Your booking with {booking.provider.get_full_name()} has been cancelled',
                    booking=booking
                )


class ReviewListCreateView(generics.ListCreateAPIView):
    """
    List and create reviews
    """
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_customer:
            return Review.objects.filter(customer=user).order_by('-created_at')
        elif user.is_provider:
            return Review.objects.filter(provider=user).order_by('-created_at')
        return Review.objects.none()

    def perform_create(self, serializer):
        # Only customers can create reviews
        if not self.request.user.is_customer:
            raise permissions.PermissionDenied("Only customers can create reviews")
        
        serializer.save(customer=self.request.user)


class PaymentListCreateView(generics.ListCreateAPIView):
    """
    List and create payments
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def get_queryset(self):
        return Payment.objects.filter(customer=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        payment = serializer.save(customer=self.request.user)
        
        # Process fake payment
        success = payment.process_fake_payment()
        
        if success:
            # Create notification for provider
            Notification.objects.create(
                user=payment.booking.provider,
                notification_type='payment_received',
                title='Payment Received',
                message=f'Payment of ${payment.amount} received from {payment.customer.get_full_name()}',
                booking=payment.booking
            )


class ProcessPaymentView(APIView):
    """
    Process payment for a booking
    """
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def post(self, request, booking_id):
        try:
            booking = ServiceBooking.objects.get(
                id=booking_id,
                customer=request.user,
                status__in=['confirmed', 'completed']
            )
        except ServiceBooking.DoesNotExist:
            return Response(
                {'error': 'Booking not found or not eligible for payment'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if payment already exists
        if Payment.objects.filter(booking=booking, status='completed').exists():
            return Response(
                {'error': 'Payment already completed for this booking'},
                status=status.HTTP_400_BAD_REQUEST
            )

        payment_method = request.data.get('payment_method', 'online')
        
        # Create payment
        payment = Payment.objects.create(
            booking=booking,
            customer=request.user,
            amount=booking.quoted_price,
            payment_method=payment_method
        )

        # Process payment
        if payment_method == 'cash':
            # For cash payments, mark as completed immediately
            payment.status = 'completed'
            payment.transaction_id = f"CASH_{payment.payment_id.hex[:12].upper()}"
            payment.gateway_response = {
                'status': 'success',
                'message': 'Cash payment recorded',
                'payment_method': 'cash'
            }
            payment.save()
        else:
            # Process online payment
            payment.process_fake_payment()

        serializer = PaymentSerializer(payment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ServiceAvailabilityListCreateView(generics.ListCreateAPIView):
    """
    List and create service availability
    """
    serializer_class = ServiceAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated, IsProvider]

    def get_queryset(self):
        return ServiceAvailability.objects.filter(provider=self.request.user)

    def perform_create(self, serializer):
        serializer.save(provider=self.request.user)


class NotificationListView(generics.ListAPIView):
    """
    List user notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class MarkNotificationReadView(APIView):
    """
    Mark notification as read
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            notification.mark_as_read()
            return Response({'status': 'marked as read'})
        except Notification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class DashboardStatsView(APIView):
    """
    Get dashboard statistics for users
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        stats = {}

        if user.is_customer:
            # Customer statistics
            bookings = ServiceBooking.objects.filter(customer=user)
            stats = {
                'total_bookings': bookings.count(),
                'active_bookings': bookings.filter(status__in=['pending', 'confirmed', 'in_progress']).count(),
                'completed_bookings': bookings.filter(status='completed').count(),
                'total_spent': bookings.filter(
                    status='completed',
                    payment_status='paid'
                ).aggregate(total=Sum('quoted_price'))['total'] or Decimal('0.00'),
                'unread_notifications': Notification.objects.filter(
                    user=user, is_read=False
                ).count(),
                'recent_activity': self.get_recent_activity(user)
            }

        elif user.is_provider:
            # Provider statistics
            bookings = ServiceBooking.objects.filter(provider=user)
            reviews = Review.objects.filter(provider=user)
            
            stats = {
                'total_services': ProviderService.objects.filter(provider=user, is_active=True).count(),
                'pending_requests': bookings.filter(status='pending').count(),
                'total_earnings': bookings.filter(
                    status='completed',
                    payment_status='paid'
                ).aggregate(total=Sum('quoted_price'))['total'] or Decimal('0.00'),
                'average_rating': reviews.aggregate(avg=Avg('rating'))['avg'] or Decimal('0.00'),
                'total_reviews': reviews.count(),
                'unread_notifications': Notification.objects.filter(
                    user=user, is_read=False
                ).count(),
                'recent_activity': self.get_recent_activity(user)
            }

        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)

    def get_recent_activity(self, user):
        """
        Get recent activity for the user
        """
        activities = []
        
        # Recent bookings
        if user.is_customer:
            recent_bookings = ServiceBooking.objects.filter(
                customer=user
            ).order_by('-created_at')[:5]
            
            for booking in recent_bookings:
                activities.append({
                    'type': 'booking',
                    'message': f'Booked {booking.service.name} with {booking.provider.get_full_name()}',
                    'date': booking.created_at,
                    'status': booking.status
                })
        
        elif user.is_provider:
            recent_bookings = ServiceBooking.objects.filter(
                provider=user
            ).order_by('-created_at')[:5]
            
            for booking in recent_bookings:
                activities.append({
                    'type': 'booking_request',
                    'message': f'Booking request from {booking.customer.get_full_name()}',
                    'date': booking.created_at,
                    'status': booking.status
                })

        # Recent reviews
        recent_reviews = Review.objects.filter(
            provider=user if user.is_provider else None,
            customer=user if user.is_customer else None
        ).order_by('-created_at')[:3]
        
        for review in recent_reviews:
            if user.is_provider:
                activities.append({
                    'type': 'review_received',
                    'message': f'Received {review.rating}-star review from {review.customer.get_full_name()}',
                    'date': review.created_at,
                    'rating': review.rating
                })
            else:
                activities.append({
                    'type': 'review_given',
                    'message': f'Reviewed {review.provider.get_full_name()} - {review.rating} stars',
                    'date': review.created_at,
                    'rating': review.rating
                })

        # Sort by date and return latest 10
        activities.sort(key=lambda x: x['date'], reverse=True)
        return activities[:10]


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def service_categories(request):
    """
    Get all service categories
    """
    categories = ServiceCategory.objects.filter(is_active=True).order_by('name')
    data = [{'id': cat.id, 'name': cat.name, 'description': cat.description} for cat in categories]
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsProvider])
def booking_stats(request):
    """
    Get booking statistics for providers
    """
    user = request.user
    bookings = ServiceBooking.objects.filter(provider=user)
    
    stats = {
        'total_bookings': bookings.count(),
        'pending_bookings': bookings.filter(status='pending').count(),
        'confirmed_bookings': bookings.filter(status='confirmed').count(),
        'completed_bookings': bookings.filter(status='completed').count(),
        'cancelled_bookings': bookings.filter(status='cancelled').count(),
        'total_revenue': bookings.filter(
            status='completed',
            payment_status='paid'
        ).aggregate(total=Sum('quoted_price'))['total'] or Decimal('0.00'),
        'average_rating': Review.objects.filter(
            provider=user
        ).aggregate(avg=Avg('rating'))['avg'] or Decimal('0.00')
    }
    
    serializer = BookingStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsCustomer])
def cancel_booking(request, booking_id):
    """
    Cancel a booking
    """
    try:
        booking = ServiceBooking.objects.get(
            id=booking_id,
            customer=request.user,
            status__in=['pending', 'confirmed']
        )
        
        booking.status = 'cancelled'
        booking.save()
        
        # Create notification for provider
        Notification.objects.create(
            user=booking.provider,
            notification_type='booking_cancelled',
            title='Booking Cancelled',
            message=f'Booking from {booking.customer.get_full_name()} has been cancelled',
            booking=booking
        )
        
        serializer = ServiceBookingSerializer(booking)
        return Response(serializer.data)
        
    except ServiceBooking.DoesNotExist:
        return Response(
            {'error': 'Booking not found or cannot be cancelled'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def provider_reviews(request, provider_id):
    """
    Get reviews for a specific provider
    """
    try:
        provider = User.objects.get(id=provider_id, role='provider')
        reviews = Review.objects.filter(provider=provider).order_by('-created_at')
        serializer = ReviewSerializer(reviews, many=True)
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response(
            {'error': 'Provider not found'},
            status=status.HTTP_404_NOT_FOUND
        )
