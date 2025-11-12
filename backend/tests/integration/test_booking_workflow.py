"""
Integration tests for the complete booking workflow.
Tests the end-to-end process from service search to payment completion.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from tests.utils.factories import TestDataFactory, UserFactory, ServiceCategoryFactory, ProviderServiceFactory
from servicemgmt.models import ServiceBooking, Payment, Review, Notification


class BookingWorkflowIntegrationTest(APITestCase):
    """
    Integration test for complete booking workflow:
    1. Customer searches for services
    2. Customer creates booking
    3. Provider receives notification
    4. Provider confirms booking
    5. Customer makes payment
    6. Service is completed
    7. Customer leaves review
    """
    
    def setUp(self):
        """Set up test data"""
        self.customer = UserFactory.create_customer(
            username='test_customer',
            latitude=Decimal('40.7128'),
            longitude=Decimal('-74.0060')
        )
        
        self.provider = UserFactory.create_provider(
            username='test_provider',
            latitude=Decimal('40.7589'),
            longitude=Decimal('-73.9851')
        )
        
        self.category = ServiceCategoryFactory.create_category(name='Plumbing')
        self.service = ProviderServiceFactory.create_service(
            provider=self.provider,
            category=self.category,
            name='Emergency Plumbing',
            base_price=Decimal('100.00')
        )
        
        # Create JWT tokens
        self.customer_token = RefreshToken.for_user(self.customer).access_token
        self.provider_token = RefreshToken.for_user(self.provider).access_token

    def test_complete_booking_workflow(self):
        """Test the complete booking workflow from search to review"""
        
        # Step 1: Customer searches for services
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        search_url = reverse('servicemgmt:service-search')
        search_data = {
            'latitude': '40.7128',
            'longitude': '-74.0060',
            'radius': 10,
            'category': self.category.id
        }
        
        search_response = self.client.post(search_url, search_data, format='json')
        self.assertEqual(search_response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(search_response.data['nearby_services']), 0)
        
        # Step 2: Customer creates booking
        booking_url = reverse('servicemgmt:booking-list-create')
        booking_data = {
            'provider': self.provider.id,
            'service': self.service.id,
            'booking_date': (timezone.now() + timedelta(days=1)).isoformat(),
            'service_address': '123 Test Street, New York, NY',
            'service_latitude': '40.7128',
            'service_longitude': '-74.0060',
            'quoted_price': '150.00',
            'special_instructions': 'Please call before arriving'
        }
        
        booking_response = self.client.post(booking_url, booking_data, format='json')
        self.assertEqual(booking_response.status_code, status.HTTP_201_CREATED)
        booking_id = booking_response.data['id']
        
        # Verify booking was created
        booking = ServiceBooking.objects.get(id=booking_id)
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.customer, self.customer)
        self.assertEqual(booking.provider, self.provider)
        
        # Step 3: Verify provider received notification
        notifications = Notification.objects.filter(
            user=self.provider,
            notification_type='booking_request'
        )
        self.assertGreater(notifications.count(), 0)
        
        # Step 4: Provider confirms booking
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.provider_token}')
        booking_detail_url = reverse('servicemgmt:booking-detail', kwargs={'pk': booking_id})
        confirm_data = {'status': 'confirmed'}
        
        confirm_response = self.client.patch(booking_detail_url, confirm_data, format='json')
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)
        self.assertEqual(confirm_response.data['status'], 'confirmed')
        
        # Verify booking status updated
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')
        self.assertIsNotNone(booking.confirmed_at)
        
        # Step 5: Customer makes payment
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        payment_url = reverse('servicemgmt:process-payment', kwargs={'booking_id': booking_id})
        payment_data = {'payment_method': 'online'}
        
        payment_response = self.client.post(payment_url, payment_data, format='json')
        self.assertEqual(payment_response.status_code, status.HTTP_201_CREATED)
        
        # Verify payment was created
        payment = Payment.objects.get(booking=booking)
        self.assertEqual(payment.customer, self.customer)
        self.assertEqual(payment.amount, Decimal('150.00'))
        
        # Step 6: Provider marks service as completed
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.provider_token}')
        complete_data = {'status': 'completed'}
        
        complete_response = self.client.patch(booking_detail_url, complete_data, format='json')
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        self.assertEqual(complete_response.data['status'], 'completed')
        
        # Verify booking completed
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'completed')
        self.assertIsNotNone(booking.completed_at)
        self.assertTrue(booking.can_be_reviewed)
        
        # Step 7: Customer leaves review
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        review_url = reverse('servicemgmt:review-list-create')
        review_data = {
            'booking': booking_id,
            'rating': 5,
            'title': 'Excellent service!',
            'comment': 'Very professional and quick response.',
            'quality_rating': 5,
            'punctuality_rating': 5,
            'communication_rating': 5,
            'value_rating': 4
        }
        
        review_response = self.client.post(review_url, review_data, format='json')
        self.assertEqual(review_response.status_code, status.HTTP_201_CREATED)
        
        # Verify review was created
        review = Review.objects.get(booking=booking)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.customer, self.customer)
        self.assertEqual(review.provider, self.provider)
        self.assertTrue(review.is_verified)

    def test_booking_cancellation_workflow(self):
        """Test booking cancellation workflow"""
        
        # Create booking
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        booking_url = reverse('servicemgmt:booking-list-create')
        booking_data = {
            'provider': self.provider.id,
            'service': self.service.id,
            'booking_date': (timezone.now() + timedelta(days=1)).isoformat(),
            'service_address': '123 Test Street, New York, NY',
            'quoted_price': '150.00'
        }
        
        booking_response = self.client.post(booking_url, booking_data, format='json')
        booking_id = booking_response.data['id']
        
        # Cancel booking
        cancel_url = reverse('servicemgmt:cancel-booking', kwargs={'booking_id': booking_id})
        cancel_response = self.client.post(cancel_url)
        
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_response.data['status'], 'cancelled')
        
        # Verify booking was cancelled
        booking = ServiceBooking.objects.get(id=booking_id)
        self.assertEqual(booking.status, 'cancelled')
        self.assertIsNotNone(booking.cancelled_at)

    def test_provider_rejection_workflow(self):
        """Test provider rejection workflow"""
        
        # Create booking
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        booking_url = reverse('servicemgmt:booking-list-create')
        booking_data = {
            'provider': self.provider.id,
            'service': self.service.id,
            'booking_date': (timezone.now() + timedelta(days=1)).isoformat(),
            'service_address': '123 Test Street, New York, NY',
            'quoted_price': '150.00'
        }
        
        booking_response = self.client.post(booking_url, booking_data, format='json')
        booking_id = booking_response.data['id']
        
        # Provider rejects booking
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.provider_token}')
        booking_detail_url = reverse('servicemgmt:booking-detail', kwargs={'pk': booking_id})
        reject_data = {
            'status': 'rejected',
            'rejection_reason': 'Not available on that date'
        }
        
        reject_response = self.client.patch(booking_detail_url, reject_data, format='json')
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reject_response.data['status'], 'rejected')
        
        # Verify booking was rejected
        booking = ServiceBooking.objects.get(id=booking_id)
        self.assertEqual(booking.status, 'rejected')
        self.assertEqual(booking.rejection_reason, 'Not available on that date')

    def test_payment_failure_workflow(self):
        """Test payment failure handling"""
        
        # Create confirmed booking
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        booking_url = reverse('servicemgmt:booking-list-create')
        booking_data = {
            'provider': self.provider.id,
            'service': self.service.id,
            'booking_date': (timezone.now() + timedelta(days=1)).isoformat(),
            'service_address': '123 Test Street, New York, NY',
            'quoted_price': '150.00'
        }
        
        booking_response = self.client.post(booking_url, booking_data, format='json')
        booking_id = booking_response.data['id']
        
        # Provider confirms
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.provider_token}')
        booking_detail_url = reverse('servicemgmt:booking-detail', kwargs={'pk': booking_id})
        self.client.patch(booking_detail_url, {'status': 'confirmed'}, format='json')
        
        # Attempt payment (may fail due to fake payment gateway)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        payment_url = reverse('servicemgmt:process-payment', kwargs={'booking_id': booking_id})
        payment_data = {'payment_method': 'online'}
        
        payment_response = self.client.post(payment_url, payment_data, format='json')
        self.assertEqual(payment_response.status_code, status.HTTP_201_CREATED)
        
        # Check payment status (could be completed or failed)
        payment = Payment.objects.get(booking_id=booking_id)
        self.assertIn(payment.status, ['completed', 'failed', 'processing'])

    def test_multiple_bookings_same_provider(self):
        """Test multiple bookings with the same provider"""
        
        # Create multiple services for the same provider
        service2 = ProviderServiceFactory.create_service(
            provider=self.provider,
            category=self.category,
            name='Regular Plumbing Maintenance'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        booking_url = reverse('servicemgmt:booking-list-create')
        
        # Create first booking
        booking_data1 = {
            'provider': self.provider.id,
            'service': self.service.id,
            'booking_date': (timezone.now() + timedelta(days=1)).isoformat(),
            'service_address': '123 Test Street, New York, NY',
            'quoted_price': '150.00'
        }
        
        response1 = self.client.post(booking_url, booking_data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        
        # Create second booking
        booking_data2 = {
            'provider': self.provider.id,
            'service': service2.id,
            'booking_date': (timezone.now() + timedelta(days=2)).isoformat(),
            'service_address': '456 Another Street, New York, NY',
            'quoted_price': '200.00'
        }
        
        response2 = self.client.post(booking_url, booking_data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        
        # Verify both bookings exist
        customer_bookings = ServiceBooking.objects.filter(customer=self.customer)
        self.assertEqual(customer_bookings.count(), 2)
        
        provider_bookings = ServiceBooking.objects.filter(provider=self.provider)
        self.assertEqual(provider_bookings.count(), 2)


class GeolocationIntegrationTest(APITestCase):
    """
    Integration tests for geolocation-based service search
    """
    
    def setUp(self):
        """Set up test data with multiple providers at different locations"""
        self.customer = UserFactory.create_customer(
            latitude=Decimal('40.7128'),  # New York City
            longitude=Decimal('-74.0060')
        )
        
        # Create providers at different distances
        self.nearby_provider = UserFactory.create_provider(
            username='nearby_provider',
            latitude=Decimal('40.7589'),  # ~5km away
            longitude=Decimal('-73.9851')
        )
        
        self.distant_provider = UserFactory.create_provider(
            username='distant_provider',
            latitude=Decimal('40.8176'),  # ~15km away
            longitude=Decimal('-73.9782')
        )
        
        self.category = ServiceCategoryFactory.create_category(name='Plumbing')
        
        # Create services for both providers
        self.nearby_service = ProviderServiceFactory.create_service(
            provider=self.nearby_provider,
            category=self.category,
            name='Nearby Plumbing Service'
        )
        
        self.distant_service = ProviderServiceFactory.create_service(
            provider=self.distant_provider,
            category=self.category,
            name='Distant Plumbing Service'
        )
        
        self.customer_token = RefreshToken.for_user(self.customer).access_token

    def test_geolocation_search_separation(self):
        """Test that services are properly separated by distance"""
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        search_url = reverse('servicemgmt:service-search')
        search_data = {
            'latitude': '40.7128',
            'longitude': '-74.0060',
            'radius': 10  # 10km radius
        }
        
        response = self.client.post(search_url, search_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Nearby service should be in nearby_services
        nearby_services = response.data['nearby_services']
        nearby_service_ids = [service['service']['id'] for service in nearby_services]
        self.assertIn(self.nearby_service.id, nearby_service_ids)
        
        # Distant service should be in distant_services
        distant_services = response.data['distant_services']
        distant_service_ids = [service['service']['id'] for service in distant_services]
        self.assertIn(self.distant_service.id, distant_service_ids)

    def test_category_filtering_with_geolocation(self):
        """Test category filtering combined with geolocation"""
        
        # Create a different category service
        electrical_category = ServiceCategoryFactory.create_category(name='Electrical')
        electrical_service = ProviderServiceFactory.create_service(
            provider=self.nearby_provider,
            category=electrical_category,
            name='Electrical Service'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.customer_token}')
        search_url = reverse('servicemgmt:service-search')
        search_data = {
            'latitude': '40.7128',
            'longitude': '-74.0060',
            'radius': 10,
            'category': self.category.id  # Only plumbing services
        }
        
        response = self.client.post(search_url, search_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should only return plumbing services
        all_services = response.data['nearby_services'] + response.data['distant_services']
        for service_data in all_services:
            self.assertEqual(service_data['service']['category']['id'], self.category.id)
        
        # Electrical service should not be included
        all_service_ids = [service['service']['id'] for service in all_services]
        self.assertNotIn(electrical_service.id, all_service_ids)


class NotificationIntegrationTest(APITestCase):
    """
    Integration tests for notification system
    """
    
    def setUp(self):
        """Set up test data"""
        scenario = TestDataFactory.create_complete_booking_scenario()
        self.customer = scenario['customer']
        self.provider = scenario['provider']
        self.booking = scenario['booking']
        
        self.customer_token = RefreshToken.for_user(self.customer).access_token
        self.provider_token = RefreshToken.for_user(self.provider).access_token

    def test_notification_creation_on_booking_events(self):
        """Test that notifications are created for booking events"""
        
        # Initial booking should create notification for provider
        provider_notifications = Notification.objects.filter(
            user=self.provider,
            notification_type='booking_request'
        )
        self.assertGreater(provider_notifications.count(), 0)
        
        # Confirm booking (should create notification for customer)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.provider_token}')
        booking_url = reverse('servicemgmt:booking-detail', kwargs={'pk': self.booking.id})
        self.client.patch(booking_url, {'status': 'confirmed'}, format='json')
        
        # Check for customer notification
        customer_notifications = Notification.objects.filter(
            user=self.customer,
            notification_type='booking_confirmed'
        )
        self.assertGreater(customer_notifications.count(), 0)

    def test_notification_marking_as_read(self):
        """Test marking notifications as read"""
        
        # Get a notification
        notification = Notification.objects.filter(user=self.provider).first()
        self.assertFalse(notification.is_read)
        
        # Mark as read
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.provider_token}')
        mark_read_url = reverse('servicemgmt:mark-notification-read', 
                               kwargs={'notification_id': notification.id})
        
        response = self.client.post(mark_read_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify notification is marked as read
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
