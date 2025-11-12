"""
Frontend tests for Django template views.
Tests the template-based views and frontend functionality.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

from tests.utils.factories import (
    UserFactory, ServiceCategoryFactory, ProviderServiceFactory,
    ServiceBookingFactory, TestDataFactory
)
from servicemgmt.models import ServiceBooking

User = get_user_model()


class HomePageTest(TestCase):
    """
    Test cases for home page template view
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.home_url = reverse('usermgmt:home')
        
        # Create some test data for the home page
        self.category = ServiceCategoryFactory.create_category(name='Plumbing')
        self.provider = UserFactory.create_provider()
        self.service = ProviderServiceFactory.create_service(
            provider=self.provider,
            category=self.category
        )

    def test_home_page_loads(self):
        """Test that home page loads successfully"""
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ServiceFinder')
        self.assertContains(response, 'Find Local Services')

    def test_home_page_shows_categories(self):
        """Test that home page displays service categories"""
        response = self.client.get(self.home_url)
        self.assertContains(response, self.category.name)

    def test_home_page_context(self):
        """Test home page context data"""
        response = self.client.get(self.home_url)
        self.assertIn('categories', response.context)
        self.assertIn('featured_services', response.context)
        self.assertEqual(len(response.context['categories']), 1)

    def test_home_page_responsive_elements(self):
        """Test that home page contains responsive elements"""
        response = self.client.get(self.home_url)
        # Check for Bootstrap classes
        self.assertContains(response, 'container')
        self.assertContains(response, 'row')
        self.assertContains(response, 'col-')


class AuthenticationTemplateTest(TestCase):
    """
    Test cases for authentication template views
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.login_url = reverse('usermgmt:login_page')
        self.register_url = reverse('usermgmt:register_page')
        
        self.customer = UserFactory.create_customer(
            username='testcustomer',
            password='testpass123'
        )

    def test_login_page_loads(self):
        """Test that login page loads successfully"""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login')
        self.assertContains(response, 'form')

    def test_login_page_form_elements(self):
        """Test login page contains required form elements"""
        response = self.client.get(self.login_url)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'type="submit"')

    def test_register_page_loads(self):
        """Test that register page loads successfully"""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Register')
        self.assertContains(response, 'form')

    def test_register_page_form_elements(self):
        """Test register page contains required form elements"""
        response = self.client.get(self.register_url)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'name="role"')
        self.assertContains(response, 'type="submit"')

    def test_login_form_submission_success(self):
        """Test successful login form submission"""
        login_data = {
            'username': 'testcustomer',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, login_data)
        
        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

    def test_login_form_submission_failure(self):
        """Test failed login form submission"""
        login_data = {
            'username': 'testcustomer',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, login_data)
        
        # Should stay on login page with error
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Invalid credentials' in str(message) for message in messages))

    def test_register_form_submission_success(self):
        """Test successful registration form submission"""
        register_data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'first_name': 'New',
            'last_name': 'User',
            'role': 'customer',
            'phone_number': '+1234567890'
        }
        response = self.client.post(self.register_url, register_data)
        
        # Should redirect after successful registration
        self.assertEqual(response.status_code, 302)
        
        # Verify user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())


class DashboardTemplateTest(TestCase):
    """
    Test cases for dashboard template views
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.customer = UserFactory.create_customer(username='customer')
        self.provider = UserFactory.create_provider(username='provider')
        
        self.customer_dashboard_url = reverse('usermgmt:customer_dashboard_page')
        self.provider_dashboard_url = reverse('usermgmt:provider_dashboard_page')

    def test_customer_dashboard_requires_login(self):
        """Test that customer dashboard requires authentication"""
        response = self.client.get(self.customer_dashboard_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_provider_dashboard_requires_login(self):
        """Test that provider dashboard requires authentication"""
        response = self.client.get(self.provider_dashboard_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_customer_dashboard_loads_for_customer(self):
        """Test customer dashboard loads for customer user"""
        self.client.force_login(self.customer)
        response = self.client.get(self.customer_dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Customer Dashboard')

    def test_provider_dashboard_loads_for_provider(self):
        """Test provider dashboard loads for provider user"""
        self.client.force_login(self.provider)
        response = self.client.get(self.provider_dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Provider Dashboard')

    def test_customer_cannot_access_provider_dashboard(self):
        """Test customer cannot access provider dashboard"""
        self.client.force_login(self.customer)
        response = self.client.get(self.provider_dashboard_url)
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_provider_cannot_access_customer_dashboard(self):
        """Test provider cannot access customer dashboard"""
        self.client.force_login(self.provider)
        response = self.client.get(self.customer_dashboard_url)
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_customer_dashboard_context(self):
        """Test customer dashboard context data"""
        # Create some bookings for the customer
        scenario = TestDataFactory.create_complete_booking_scenario()
        customer = scenario['customer']
        
        self.client.force_login(customer)
        response = self.client.get(self.customer_dashboard_url)
        
        self.assertIn('recent_bookings', response.context)
        self.assertIn('stats', response.context)

    def test_provider_dashboard_context(self):
        """Test provider dashboard context data"""
        # Create some bookings for the provider
        scenario = TestDataFactory.create_complete_booking_scenario()
        provider = scenario['provider']
        
        self.client.force_login(provider)
        response = self.client.get(self.provider_dashboard_url)
        
        self.assertIn('recent_bookings', response.context)
        self.assertIn('stats', response.context)
        self.assertIn('services', response.context)


class ServiceTemplateTest(TestCase):
    """
    Test cases for service-related template views
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.customer = UserFactory.create_customer()
        self.provider = UserFactory.create_provider()
        
        self.category = ServiceCategoryFactory.create_category(name='Plumbing')
        self.service = ProviderServiceFactory.create_service(
            provider=self.provider,
            category=self.category,
            name='Test Service'
        )
        
        self.services_url = reverse('usermgmt:services_page')
        self.service_detail_url = reverse('usermgmt:service_detail_page', 
                                         kwargs={'service_id': self.service.id})

    def test_services_page_loads(self):
        """Test services page loads successfully"""
        response = self.client.get(self.services_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Services')

    def test_services_page_shows_services(self):
        """Test services page displays available services"""
        response = self.client.get(self.services_url)
        self.assertContains(response, self.service.name)
        self.assertContains(response, self.category.name)

    def test_service_detail_page_loads(self):
        """Test service detail page loads successfully"""
        response = self.client.get(self.service_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.service.name)
        self.assertContains(response, self.service.description)

    def test_service_detail_page_context(self):
        """Test service detail page context data"""
        response = self.client.get(self.service_detail_url)
        self.assertIn('service', response.context)
        self.assertIn('provider', response.context)
        self.assertIn('reviews', response.context)
        self.assertEqual(response.context['service'], self.service)

    def test_service_search_functionality(self):
        """Test service search functionality"""
        search_data = {
            'q': 'Test',
            'category': self.category.id,
            'latitude': '40.7128',
            'longitude': '-74.0060'
        }
        response = self.client.get(self.services_url, search_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.service.name)


class BookingTemplateTest(TestCase):
    """
    Test cases for booking-related template views
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        scenario = TestDataFactory.create_complete_booking_scenario()
        self.customer = scenario['customer']
        self.provider = scenario['provider']
        self.booking = scenario['booking']
        
        self.bookings_url = reverse('usermgmt:bookings_page')
        self.booking_detail_url = reverse('usermgmt:booking_detail_page', 
                                         kwargs={'booking_id': self.booking.id})

    def test_bookings_page_requires_login(self):
        """Test bookings page requires authentication"""
        response = self.client.get(self.bookings_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_customer_bookings_page_loads(self):
        """Test customer bookings page loads successfully"""
        self.client.force_login(self.customer)
        response = self.client.get(self.bookings_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Bookings')

    def test_provider_bookings_page_loads(self):
        """Test provider bookings page loads successfully"""
        self.client.force_login(self.provider)
        response = self.client.get(self.bookings_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Bookings')

    def test_bookings_page_shows_user_bookings(self):
        """Test bookings page shows user's bookings"""
        self.client.force_login(self.customer)
        response = self.client.get(self.bookings_url)
        self.assertContains(response, self.booking.service.name)

    def test_booking_detail_page_loads(self):
        """Test booking detail page loads successfully"""
        self.client.force_login(self.customer)
        response = self.client.get(self.booking_detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Booking Details')

    def test_booking_detail_page_context(self):
        """Test booking detail page context data"""
        self.client.force_login(self.customer)
        response = self.client.get(self.booking_detail_url)
        self.assertIn('booking', response.context)
        self.assertIn('can_cancel', response.context)
        self.assertIn('can_review', response.context)
        self.assertEqual(response.context['booking'], self.booking)

    def test_unauthorized_booking_access(self):
        """Test unauthorized access to booking details"""
        other_customer = UserFactory.create_customer(username='other_customer')
        self.client.force_login(other_customer)
        response = self.client.get(self.booking_detail_url)
        self.assertEqual(response.status_code, 404)  # Not found for unauthorized user


class ProfileTemplateTest(TestCase):
    """
    Test cases for profile template views
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.customer = UserFactory.create_customer(username='customer')
        self.provider = UserFactory.create_provider(username='provider')
        
        self.profile_url = reverse('usermgmt:profile_page')

    def test_profile_page_requires_login(self):
        """Test profile page requires authentication"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_customer_profile_page_loads(self):
        """Test customer profile page loads successfully"""
        self.client.force_login(self.customer)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profile')
        self.assertContains(response, self.customer.username)

    def test_provider_profile_page_loads(self):
        """Test provider profile page loads successfully"""
        self.client.force_login(self.provider)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Profile')
        self.assertContains(response, self.provider.username)

    def test_profile_page_context(self):
        """Test profile page context data"""
        self.client.force_login(self.customer)
        response = self.client.get(self.profile_url)
        self.assertIn('user', response.context)
        self.assertIn('profile', response.context)
        self.assertEqual(response.context['user'], self.customer)

    def test_profile_update_form(self):
        """Test profile update form submission"""
        self.client.force_login(self.customer)
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone_number': '+9876543210',
            'bio': 'Updated bio'
        }
        response = self.client.post(self.profile_url, update_data)
        
        # Should redirect after successful update
        self.assertEqual(response.status_code, 302)
        
        # Verify profile was updated
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.first_name, 'Updated')


class ResponsiveDesignTest(TestCase):
    """
    Test cases for responsive design elements
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.customer = UserFactory.create_customer()

    def test_bootstrap_css_loaded(self):
        """Test that Bootstrap CSS is loaded"""
        response = self.client.get(reverse('usermgmt:home'))
        self.assertContains(response, 'bootstrap')

    def test_responsive_meta_tag(self):
        """Test that responsive meta tag is present"""
        response = self.client.get(reverse('usermgmt:home'))
        self.assertContains(response, 'viewport')
        self.assertContains(response, 'width=device-width')

    def test_mobile_friendly_navigation(self):
        """Test mobile-friendly navigation elements"""
        response = self.client.get(reverse('usermgmt:home'))
        self.assertContains(response, 'navbar-toggler')
        self.assertContains(response, 'navbar-collapse')

    def test_responsive_grid_classes(self):
        """Test responsive grid classes are used"""
        response = self.client.get(reverse('usermgmt:home'))
        self.assertContains(response, 'col-md-')
        self.assertContains(response, 'col-lg-')

    def test_dark_theme_classes(self):
        """Test dark theme CSS classes"""
        response = self.client.get(reverse('usermgmt:home'))
        self.assertContains(response, 'dark-theme')
        self.assertContains(response, 'bg-dark')


class JavaScriptFunctionalityTest(TestCase):
    """
    Test cases for JavaScript functionality
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.customer = UserFactory.create_customer()

    def test_main_js_loaded(self):
        """Test that main.js is loaded"""
        response = self.client.get(reverse('usermgmt:home'))
        self.assertContains(response, 'main.js')

    def test_leaflet_map_scripts(self):
        """Test that Leaflet map scripts are loaded"""
        response = self.client.get(reverse('usermgmt:home'))
        self.assertContains(response, 'leaflet')

    def test_geolocation_functionality_elements(self):
        """Test elements required for geolocation functionality"""
        response = self.client.get(reverse('usermgmt:services_page'))
        self.assertContains(response, 'id="map"')
        self.assertContains(response, 'get-location')

    def test_ajax_endpoints_referenced(self):
        """Test that AJAX endpoints are properly referenced"""
        self.client.force_login(self.customer)
        response = self.client.get(reverse('usermgmt:customer_dashboard_page'))
        # Check for data attributes or script tags that reference API endpoints
        self.assertContains(response, 'api/')


class FormValidationTest(TestCase):
    """
    Test cases for form validation in templates
    """
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.customer = UserFactory.create_customer()

    def test_login_form_validation(self):
        """Test login form client-side validation attributes"""
        response = self.client.get(reverse('usermgmt:login_page'))
        self.assertContains(response, 'required')
        self.assertContains(response, 'minlength')

    def test_register_form_validation(self):
        """Test register form client-side validation attributes"""
        response = self.client.get(reverse('usermgmt:register_page'))
        self.assertContains(response, 'required')
        self.assertContains(response, 'type="email"')
        self.assertContains(response, 'pattern')

    def test_booking_form_validation(self):
        """Test booking form validation elements"""
        self.client.force_login(self.customer)
        # Assuming there's a booking form page
        service = ProviderServiceFactory.create_service()
        response = self.client.get(reverse('usermgmt:service_detail_page', 
                                          kwargs={'service_id': service.id}))
        self.assertContains(response, 'booking-form')

    def test_error_message_display(self):
        """Test error message display in forms"""
        # Submit invalid login data
        response = self.client.post(reverse('usermgmt:login_page'), {
            'username': '',
            'password': ''
        })
        self.assertContains(response, 'error')
