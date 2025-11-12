from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from .models import (
    ServiceBooking, Review, Payment, ServiceAvailability,
    ServiceImage, Notification
)
from usermgmt.models import ServiceCategory, ProviderService

User = get_user_model()


class ServiceManagementModelTests(TestCase):
    """
    Test cases for service management models
    """
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.customer = User.objects.create_user(
            username='customer1',
            email='customer@test.com',
            password='testpass123',
            role='customer',
            first_name='John',
            last_name='Doe',
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060')
        )
        
        self.provider = User.objects.create_user(
            username='provider1',
            email='provider@test.com',
            password='testpass123',
            role='provider',
            first_name='Jane',
            last_name='Smith',
            latitude=Decimal('40.7589'),
            longitude=Decimal('-73.9851')
        )
        
        # Create service category
        self.category = ServiceCategory.objects.create(
            name='Plumbing',
            description='Plumbing services'
        )
        
        # Create provider service
        self.service = ProviderService.objects.create(
            provider=self.provider,
            category=self.category,
            name='Emergency Plumbing',
            description='24/7 emergency plumbing service',
            base_price=Decimal('100.00'),
            price_unit='hour'
        )

    def test_service_booking_creation(self):
        """Test service booking creation"""
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            service_latitude=Decimal('40.7128'),
            service_longitude=Decimal('-74.0060'),
            quoted_price=Decimal('150.00')
        )
        
        self.assertEqual(booking.customer, self.customer)
        self.assertEqual(booking.provider, self.provider)
        self.assertEqual(booking.service, self.service)
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.payment_status, 'pending')
        self.assertTrue(booking.booking_id)
        self.assertTrue(booking.is_active)

    def test_service_booking_status_transitions(self):
        """Test booking status transitions"""
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00')
        )
        
        # Test confirmed status
        booking.status = 'confirmed'
        booking.save()
        booking.refresh_from_db()
        self.assertIsNotNone(booking.confirmed_at)
        
        # Test completed status
        booking.status = 'completed'
        booking.save()
        booking.refresh_from_db()
        self.assertIsNotNone(booking.completed_at)
        self.assertTrue(booking.can_be_reviewed)

    def test_review_creation(self):
        """Test review creation"""
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00'),
            status='completed'
        )
        
        review = Review.objects.create(
            booking=booking,
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            rating=5,
            title='Excellent service',
            comment='Very professional and quick',
            quality_rating=5,
            punctuality_rating=5,
            communication_rating=5,
            value_rating=4
        )
        
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.customer, self.customer)
        self.assertEqual(review.provider, self.provider)
        self.assertTrue(review.is_verified)

    def test_payment_creation(self):
        """Test payment creation"""
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00'),
            status='confirmed'
        )
        
        payment = Payment.objects.create(
            booking=booking,
            customer=self.customer,
            amount=Decimal('150.00'),
            payment_method='online'
        )
        
        self.assertEqual(payment.amount, Decimal('150.00'))
        self.assertEqual(payment.customer, self.customer)
        self.assertEqual(payment.booking, booking)
        self.assertEqual(payment.status, 'pending')
        self.assertTrue(payment.payment_id)

    def test_fake_payment_processing(self):
        """Test fake payment processing"""
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00'),
            status='confirmed'
        )
        
        payment = Payment.objects.create(
            booking=booking,
            customer=self.customer,
            amount=Decimal('150.00'),
            payment_method='online'
        )
        
        # Process payment
        success = payment.process_fake_payment()
        payment.refresh_from_db()
        
        # Payment should be processed (success rate is 90%)
        self.assertIn(payment.status, ['completed', 'failed'])
        self.assertIsNotNone(payment.transaction_id)
        self.assertIsNotNone(payment.gateway_response)

    def test_service_availability_creation(self):
        """Test service availability creation"""
        availability = ServiceAvailability.objects.create(
            provider=self.provider,
            day_of_week=1,  # Tuesday
            start_time='09:00',
            end_time='17:00',
            max_bookings_per_slot=3
        )
        
        self.assertEqual(availability.provider, self.provider)
        self.assertEqual(availability.day_of_week, 1)
        self.assertTrue(availability.is_available)

    def test_notification_creation(self):
        """Test notification creation"""
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00')
        )
        
        notification = Notification.objects.create(
            user=self.provider,
            notification_type='booking_request',
            title='New Booking Request',
            message='You have a new booking request',
            booking=booking
        )
        
        self.assertEqual(notification.user, self.provider)
        self.assertEqual(notification.notification_type, 'booking_request')
        self.assertFalse(notification.is_read)
        
        # Test mark as read
        notification.mark_as_read()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)


class ServiceManagementAPITests(APITestCase):
    """
    Test cases for service management APIs
    """
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.customer = User.objects.create_user(
            username='customer1',
            email='customer@test.com',
            password='testpass123',
            role='customer',
            first_name='John',
            last_name='Doe',
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060')
        )
        
        self.provider = User.objects.create_user(
            username='provider1',
            email='provider@test.com',
            password='testpass123',
            role='provider',
            first_name='Jane',
            last_name='Smith',
            latitude=Decimal('40.7589'),
            longitude=Decimal('-73.9851')
        )
        
        # Create service category
        self.category = ServiceCategory.objects.create(
            name='Plumbing',
            description='Plumbing services'
        )
        
        # Create provider service
        self.service = ProviderService.objects.create(
            provider=self.provider,
            category=self.category,
            name='Emergency Plumbing',
            description='24/7 emergency plumbing service',
            base_price=Decimal('100.00'),
            price_unit='hour'
        )
        
        # Create JWT tokens
        self.customer_token = RefreshToken.for_user(self.customer).access_token
        self.provider_token = RefreshToken.for_user(self.provider).access_token

    def test_service_search_api(self):
        """Test service search API"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        
        url = reverse('servicemgmt:service-search')
        data = {
            'latitude': '40.7128',
            'longitude': '-74.0060',
            'radius': 10
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('nearby_services', response.data)
        self.assertIn('distant_services', response.data)
        self.assertIn('search_params', response.data)

    def test_service_booking_creation_api(self):
        """Test service booking creation API"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        
        url = reverse('servicemgmt:booking-list-create')
        data = {
            'provider': self.provider.id,
            'service': self.service.id,
            'booking_date': (timezone.now() + timedelta(days=1)).isoformat(),
            'service_address': '123 Test St, New York, NY',
            'service_latitude': '40.7128',
            'service_longitude': '-74.0060',
            'quoted_price': '150.00'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['customer'], self.customer.id)
        self.assertEqual(response.data['provider'], self.provider.id)
        self.assertEqual(response.data['status'], 'pending')

    def test_service_booking_list_api(self):
        """Test service booking list API"""
        # Create a booking
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00')
        )
        
        # Test customer view
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        url = reverse('servicemgmt:booking-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], booking.id)

    def test_booking_status_update_api(self):
        """Test booking status update API"""
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00')
        )
        
        # Provider confirms booking
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.provider_token}')
        url = reverse('servicemgmt:booking-detail', kwargs={'pk': booking.id})
        data = {'status': 'confirmed'}
        
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'confirmed')

    def test_review_creation_api(self):
        """Test review creation API"""
        # Create completed booking
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00'),
            status='completed'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        url = reverse('servicemgmt:review-list-create')
        data = {
            'booking': booking.id,
            'rating': 5,
            'title': 'Excellent service',
            'comment': 'Very professional',
            'quality_rating': 5,
            'punctuality_rating': 5,
            'communication_rating': 5,
            'value_rating': 4
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], 5)
        self.assertEqual(response.data['customer'], self.customer.id)

    def test_payment_processing_api(self):
        """Test payment processing API"""
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00'),
            status='confirmed'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        url = reverse('servicemgmt:process-payment', kwargs={'booking_id': booking.id})
        data = {'payment_method': 'online'}
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['amount'], '150.00')
        self.assertIn(response.data['status'], ['completed', 'failed', 'processing'])

    def test_dashboard_stats_api(self):
        """Test dashboard statistics API"""
        # Create some test data
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00'),
            status='completed',
            payment_status='paid'
        )
        
        # Test customer stats
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        url = reverse('servicemgmt:dashboard-stats')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_bookings', response.data)
        self.assertIn('completed_bookings', response.data)
        self.assertIn('total_spent', response.data)

    def test_notification_list_api(self):
        """Test notification list API"""
        # Create notification
        notification = Notification.objects.create(
            user=self.provider,
            notification_type='booking_request',
            title='New Booking Request',
            message='You have a new booking request'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.provider_token}')
        url = reverse('servicemgmt:notification-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], notification.id)

    def test_mark_notification_read_api(self):
        """Test mark notification as read API"""
        notification = Notification.objects.create(
            user=self.provider,
            notification_type='booking_request',
            title='New Booking Request',
            message='You have a new booking request'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.provider_token}')
        url = reverse('servicemgmt:mark-notification-read', kwargs={'notification_id': notification.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_service_categories_api(self):
        """Test service categories API"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        url = reverse('servicemgmt:service-categories')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Plumbing')

    def test_cancel_booking_api(self):
        """Test cancel booking API"""
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00'),
            status='pending'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        url = reverse('servicemgmt:cancel-booking', kwargs={'booking_id': booking.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'cancelled')

    def test_provider_reviews_api(self):
        """Test provider reviews API"""
        # Create completed booking and review
        booking = ServiceBooking.objects.create(
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            booking_date=timezone.now() + timedelta(days=1),
            service_address='123 Test St, New York, NY',
            quoted_price=Decimal('150.00'),
            status='completed'
        )
        
        review = Review.objects.create(
            booking=booking,
            customer=self.customer,
            provider=self.provider,
            service=self.service,
            rating=5,
            title='Great service',
            quality_rating=5,
            punctuality_rating=5,
            communication_rating=5,
            value_rating=5
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        url = reverse('servicemgmt:provider-reviews', kwargs={'provider_id': self.provider.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['rating'], 5)

    def test_unauthorized_access(self):
        """Test unauthorized access to protected endpoints"""
        url = reverse('servicemgmt:booking-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_restrictions(self):
        """Test permission restrictions"""
        # Provider trying to create booking (should fail)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.provider_token}')
        url = reverse('servicemgmt:booking-list-create')
        data = {
            'provider': self.provider.id,
            'service': self.service.id,
            'booking_date': (timezone.now() + timedelta(days=1)).isoformat(),
            'service_address': '123 Test St, New York, NY',
            'quoted_price': '150.00'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
