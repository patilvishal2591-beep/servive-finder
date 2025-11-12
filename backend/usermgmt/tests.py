from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomerProfile, ServiceProviderProfile, ServiceCategory, ProviderService

User = get_user_model()


class UserModelTest(TestCase):
    """
    Test cases for User model
    """
    
    def setUp(self):
        self.customer_data = {
            'username': 'testcustomer',
            'email': 'customer@test.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Customer',
            'role': 'customer'
        }
        
        self.provider_data = {
            'username': 'testprovider',
            'email': 'provider@test.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Provider',
            'role': 'provider'
        }

    def test_create_customer_user(self):
        """Test creating a customer user"""
        user = User.objects.create_user(**self.customer_data)
        self.assertEqual(user.username, 'testcustomer')
        self.assertEqual(user.role, 'customer')
        self.assertTrue(user.is_customer)
        self.assertFalse(user.is_provider)
        self.assertTrue(user.check_password('testpass123'))

    def test_create_provider_user(self):
        """Test creating a provider user"""
        user = User.objects.create_user(**self.provider_data)
        self.assertEqual(user.username, 'testprovider')
        self.assertEqual(user.role, 'provider')
        self.assertTrue(user.is_provider)
        self.assertFalse(user.is_customer)

    def test_user_string_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(**self.customer_data)
        expected_str = f"{user.username} ({user.get_role_display()})"
        self.assertEqual(str(user), expected_str)


class UserRegistrationTest(APITestCase):
    """
    Test cases for user registration
    """
    
    def setUp(self):
        self.register_url = reverse('usermgmt:register')
        self.valid_customer_data = {
            'username': 'newcustomer',
            'email': 'newcustomer@test.com',
            'password': 'strongpass123',
            'password_confirm': 'strongpass123',
            'first_name': 'New',
            'last_name': 'Customer',
            'role': 'customer',
            'phone_number': '+1234567890'
        }
        
        self.valid_provider_data = {
            'username': 'newprovider',
            'email': 'newprovider@test.com',
            'password': 'strongpass123',
            'password_confirm': 'strongpass123',
            'first_name': 'New',
            'last_name': 'Provider',
            'role': 'provider',
            'phone_number': '+1234567891'
        }

    def test_register_customer_success(self):
        """Test successful customer registration"""
        response = self.client.post(self.register_url, self.valid_customer_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['role'], 'customer')
        
        # Check if customer profile was created
        user = User.objects.get(username='newcustomer')
        self.assertTrue(hasattr(user, 'customer_profile'))

    def test_register_provider_success(self):
        """Test successful provider registration"""
        response = self.client.post(self.register_url, self.valid_provider_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['role'], 'provider')
        
        # Check if provider profile was created
        user = User.objects.get(username='newprovider')
        self.assertTrue(hasattr(user, 'provider_profile'))

    def test_register_password_mismatch(self):
        """Test registration with password mismatch"""
        data = self.valid_customer_data.copy()
        data['password_confirm'] = 'differentpass'
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username(self):
        """Test registration with duplicate username"""
        User.objects.create_user(username='newcustomer', email='existing@test.com', password='pass123')
        response = self.client.post(self.register_url, self.valid_customer_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        """Test registration with duplicate email"""
        User.objects.create_user(username='existing', email='newcustomer@test.com', password='pass123')
        response = self.client.post(self.register_url, self.valid_customer_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserLoginTest(APITestCase):
    """
    Test cases for user login
    """
    
    def setUp(self):
        self.login_url = reverse('usermgmt:login')
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='customer'
        )

    def test_login_success(self):
        """Test successful login"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('user', response.data)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        data = {
            'username': 'testuser',
            'password': 'wrongpass'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_inactive_user(self):
        """Test login with inactive user"""
        self.user.is_active = False
        self.user.save()
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class DashboardAccessTest(APITestCase):
    """
    Test cases for role-based dashboard access
    """
    
    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='pass123',
            role='customer'
        )
        self.provider = User.objects.create_user(
            username='provider',
            email='provider@test.com',
            password='pass123',
            role='provider'
        )
        
        self.customer_dashboard_url = reverse('usermgmt:customer_dashboard')
        self.provider_dashboard_url = reverse('usermgmt:provider_dashboard')

    def test_customer_dashboard_access(self):
        """Test customer can access customer dashboard"""
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.customer_dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['dashboard_type'], 'customer')

    def test_provider_dashboard_access(self):
        """Test provider can access provider dashboard"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.provider_dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['dashboard_type'], 'provider')

    def test_customer_cannot_access_provider_dashboard(self):
        """Test customer cannot access provider dashboard"""
        self.client.force_authenticate(user=self.customer)
        response = self.client.get(self.provider_dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_provider_cannot_access_customer_dashboard(self):
        """Test provider cannot access customer dashboard"""
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.customer_dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_dashboard_access(self):
        """Test unauthenticated user cannot access dashboards"""
        response = self.client.get(self.customer_dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        response = self.client.get(self.provider_dashboard_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ServiceCategoryTest(APITestCase):
    """
    Test cases for service categories
    """
    
    def setUp(self):
        self.category = ServiceCategory.objects.create(
            name='Plumbing',
            description='Plumbing services',
            is_active=True
        )
        self.categories_url = reverse('usermgmt:service_categories')

    def test_list_active_categories(self):
        """Test listing active service categories"""
        response = self.client.get(self.categories_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Plumbing')

    def test_inactive_categories_not_listed(self):
        """Test inactive categories are not listed"""
        self.category.is_active = False
        self.category.save()
        response = self.client.get(self.categories_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class ProviderServiceTest(APITestCase):
    """
    Test cases for provider services
    """
    
    def setUp(self):
        self.provider = User.objects.create_user(
            username='provider',
            email='provider@test.com',
            password='pass123',
            role='provider'
        )
        self.customer = User.objects.create_user(
            username='customer',
            email='customer@test.com',
            password='pass123',
            role='customer'
        )
        self.category = ServiceCategory.objects.create(
            name='Plumbing',
            description='Plumbing services'
        )
        self.services_url = reverse('usermgmt:provider_services')

    def test_provider_can_create_service(self):
        """Test provider can create a service"""
        self.client.force_authenticate(user=self.provider)
        data = {
            'category': self.category.id,
            'name': 'Pipe Repair',
            'description': 'Professional pipe repair service',
            'base_price': '50.00',
            'price_unit': 'hour'
        }
        response = self.client.post(self.services_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Pipe Repair')

    def test_customer_cannot_create_service(self):
        """Test customer cannot create a service"""
        self.client.force_authenticate(user=self.customer)
        data = {
            'category': self.category.id,
            'name': 'Pipe Repair',
            'description': 'Professional pipe repair service',
            'base_price': '50.00',
            'price_unit': 'hour'
        }
        response = self.client.post(self.services_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_provider_can_list_own_services(self):
        """Test provider can list their own services"""
        ProviderService.objects.create(
            provider=self.provider,
            category=self.category,
            name='Test Service',
            description='Test description',
            base_price=100.00
        )
        self.client.force_authenticate(user=self.provider)
        response = self.client.get(self.services_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class ChangePasswordTest(APITestCase):
    """
    Test cases for password change
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='oldpass123',
            role='customer'
        )
        self.change_password_url = reverse('usermgmt:change_password')

    def test_change_password_success(self):
        """Test successful password change"""
        self.client.force_authenticate(user=self.user)
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))

    def test_change_password_wrong_old_password(self):
        """Test password change with wrong old password"""
        self.client.force_authenticate(user=self.user)
        data = {
            'old_password': 'wrongpass',
            'new_password': 'newpass123',
            'new_password_confirm': 'newpass123'
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_mismatch(self):
        """Test password change with new password mismatch"""
        self.client.force_authenticate(user=self.user)
        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123',
            'new_password_confirm': 'differentpass'
        }
        response = self.client.post(self.change_password_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LogoutTest(APITestCase):
    """
    Test cases for user logout
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='pass123',
            role='customer'
        )
        self.logout_url = reverse('usermgmt:logout')

    def test_logout_success(self):
        """Test successful logout"""
        refresh = RefreshToken.for_user(self.user)
        self.client.force_authenticate(user=self.user)
        data = {'refresh_token': str(refresh)}
        response = self.client.post(self.logout_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class HealthCheckTest(APITestCase):
    """
    Test cases for health check endpoint
    """
    
    def test_health_check(self):
        """Test health check endpoint"""
        health_url = reverse('usermgmt:health_check')
        response = self.client.get(health_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'healthy')
