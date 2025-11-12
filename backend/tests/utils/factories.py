"""
Test data factories for ServiceFinder application.
Provides factory methods to create test data objects.
"""

from django.contrib.auth import get_user_model
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
import random

from usermgmt.models import ServiceCategory, ProviderService, CustomerProfile, ServiceProviderProfile
from servicemgmt.models import ServiceBooking, Review, Payment, ServiceAvailability, Notification

User = get_user_model()


class UserFactory:
    """Factory for creating test users"""
    
    @staticmethod
    def create_customer(username=None, email=None, **kwargs):
        """Create a test customer user"""
        username = username or f"customer_{random.randint(1000, 9999)}"
        email = email or f"{username}@test.com"
        
        defaults = {
            'username': username,
            'email': email,
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Customer',
            'role': 'customer',
            'phone_number': f'+123456{random.randint(1000, 9999)}',
            'latitude': Decimal('40.7128'),
            'longitude': Decimal('-74.0060'),
            'is_active': True
        }
        defaults.update(kwargs)
        
        user = User.objects.create_user(**defaults)
        return user
    
    @staticmethod
    def create_provider(username=None, email=None, **kwargs):
        """Create a test provider user"""
        username = username or f"provider_{random.randint(1000, 9999)}"
        email = email or f"{username}@test.com"
        
        defaults = {
            'username': username,
            'email': email,
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Provider',
            'role': 'provider',
            'phone_number': f'+123456{random.randint(1000, 9999)}',
            'latitude': Decimal('40.7589'),
            'longitude': Decimal('-73.9851'),
            'is_active': True
        }
        defaults.update(kwargs)
        
        user = User.objects.create_user(**defaults)
        return user


class ServiceCategoryFactory:
    """Factory for creating test service categories"""
    
    @staticmethod
    def create_category(name=None, **kwargs):
        """Create a test service category"""
        name = name or f"Test Category {random.randint(1, 100)}"
        
        defaults = {
            'name': name,
            'description': f'Description for {name}',
            'is_active': True
        }
        defaults.update(kwargs)
        
        return ServiceCategory.objects.create(**defaults)


class ProviderServiceFactory:
    """Factory for creating test provider services"""
    
    @staticmethod
    def create_service(provider=None, category=None, **kwargs):
        """Create a test provider service"""
        if not provider:
            provider = UserFactory.create_provider()
        if not category:
            category = ServiceCategoryFactory.create_category()
        
        defaults = {
            'provider': provider,
            'category': category,
            'name': f'Test Service {random.randint(1, 100)}',
            'description': 'Professional test service',
            'base_price': Decimal('100.00'),
            'price_unit': 'hour',
            'is_active': True,
            'years_of_experience': random.randint(1, 10)
        }
        defaults.update(kwargs)
        
        return ProviderService.objects.create(**defaults)


class ServiceBookingFactory:
    """Factory for creating test service bookings"""
    
    @staticmethod
    def create_booking(customer=None, provider=None, service=None, **kwargs):
        """Create a test service booking"""
        if not customer:
            customer = UserFactory.create_customer()
        if not provider:
            provider = UserFactory.create_provider()
        if not service:
            service = ProviderServiceFactory.create_service(provider=provider)
        
        defaults = {
            'customer': customer,
            'provider': provider,
            'service': service,
            'booking_date': timezone.now() + timedelta(days=1),
            'service_address': '123 Test Street, Test City, TC 12345',
            'service_latitude': Decimal('40.7128'),
            'service_longitude': Decimal('-74.0060'),
            'quoted_price': Decimal('150.00'),
            'status': 'pending',
            'payment_status': 'pending',
            'special_instructions': 'Test booking instructions'
        }
        defaults.update(kwargs)
        
        return ServiceBooking.objects.create(**defaults)


class ReviewFactory:
    """Factory for creating test reviews"""
    
    @staticmethod
    def create_review(booking=None, **kwargs):
        """Create a test review"""
        if not booking:
            booking = ServiceBookingFactory.create_booking(status='completed')
        
        defaults = {
            'booking': booking,
            'customer': booking.customer,
            'provider': booking.provider,
            'service': booking.service,
            'rating': random.randint(4, 5),
            'title': 'Great service!',
            'comment': 'Very professional and efficient work.',
            'quality_rating': random.randint(4, 5),
            'punctuality_rating': random.randint(4, 5),
            'communication_rating': random.randint(4, 5),
            'value_rating': random.randint(4, 5),
            'is_verified': True
        }
        defaults.update(kwargs)
        
        return Review.objects.create(**defaults)


class PaymentFactory:
    """Factory for creating test payments"""
    
    @staticmethod
    def create_payment(booking=None, **kwargs):
        """Create a test payment"""
        if not booking:
            booking = ServiceBookingFactory.create_booking(status='confirmed')
        
        defaults = {
            'booking': booking,
            'customer': booking.customer,
            'amount': booking.quoted_price,
            'payment_method': random.choice(['online', 'cash']),
            'status': 'pending'
        }
        defaults.update(kwargs)
        
        return Payment.objects.create(**defaults)


class NotificationFactory:
    """Factory for creating test notifications"""
    
    @staticmethod
    def create_notification(user=None, **kwargs):
        """Create a test notification"""
        if not user:
            user = UserFactory.create_provider()
        
        defaults = {
            'user': user,
            'notification_type': 'booking_request',
            'title': 'Test Notification',
            'message': 'This is a test notification message.',
            'is_read': False
        }
        defaults.update(kwargs)
        
        return Notification.objects.create(**defaults)


class ServiceAvailabilityFactory:
    """Factory for creating test service availability"""
    
    @staticmethod
    def create_availability(provider=None, **kwargs):
        """Create a test service availability"""
        if not provider:
            provider = UserFactory.create_provider()
        
        defaults = {
            'provider': provider,
            'day_of_week': random.randint(0, 6),
            'start_time': '09:00',
            'end_time': '17:00',
            'max_bookings_per_slot': 3,
            'is_available': True
        }
        defaults.update(kwargs)
        
        return ServiceAvailability.objects.create(**defaults)


class TestDataFactory:
    """Main factory class for creating complete test scenarios"""
    
    @staticmethod
    def create_complete_booking_scenario():
        """Create a complete booking scenario with all related objects"""
        # Create users
        customer = UserFactory.create_customer()
        provider = UserFactory.create_provider()
        
        # Create service category and service
        category = ServiceCategoryFactory.create_category(name='Plumbing')
        service = ProviderServiceFactory.create_service(
            provider=provider,
            category=category,
            name='Emergency Plumbing Repair'
        )
        
        # Create booking
        booking = ServiceBookingFactory.create_booking(
            customer=customer,
            provider=provider,
            service=service,
            status='completed'
        )
        
        # Create payment
        payment = PaymentFactory.create_payment(
            booking=booking,
            status='completed'
        )
        
        # Create review
        review = ReviewFactory.create_review(booking=booking)
        
        # Create notifications
        customer_notification = NotificationFactory.create_notification(
            user=customer,
            notification_type='booking_confirmed',
            title='Booking Confirmed'
        )
        
        provider_notification = NotificationFactory.create_notification(
            user=provider,
            notification_type='booking_request',
            title='New Booking Request'
        )
        
        return {
            'customer': customer,
            'provider': provider,
            'category': category,
            'service': service,
            'booking': booking,
            'payment': payment,
            'review': review,
            'customer_notification': customer_notification,
            'provider_notification': provider_notification
        }
    
    @staticmethod
    def create_multiple_providers_scenario(count=5):
        """Create multiple providers with services for testing search functionality"""
        providers = []
        services = []
        
        categories = [
            ServiceCategoryFactory.create_category(name='Plumbing'),
            ServiceCategoryFactory.create_category(name='Electrical'),
            ServiceCategoryFactory.create_category(name='Carpentry'),
            ServiceCategoryFactory.create_category(name='Painting'),
        ]
        
        for i in range(count):
            provider = UserFactory.create_provider(
                username=f'provider_{i}',
                latitude=Decimal(str(40.7128 + (i * 0.01))),  # Spread providers geographically
                longitude=Decimal(str(-74.0060 + (i * 0.01)))
            )
            providers.append(provider)
            
            # Create 2-3 services per provider
            for j in range(random.randint(2, 3)):
                service = ProviderServiceFactory.create_service(
                    provider=provider,
                    category=random.choice(categories),
                    name=f'Service {i}-{j}',
                    base_price=Decimal(str(random.randint(50, 200)))
                )
                services.append(service)
        
        return {
            'providers': providers,
            'services': services,
            'categories': categories
        }
