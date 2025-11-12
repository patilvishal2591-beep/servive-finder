from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views, template_views

app_name = 'usermgmt'

urlpatterns = [
    # Template-based views (Frontend)
    path('', template_views.home_view, name='home'),
    path('register/', template_views.register_view, name='register'),
    path('login/', template_views.login_view, name='login'),
    path('logout/', template_views.logout_view, name='logout'),
    path('dashboard/', template_views.dashboard_view, name='dashboard'),
    path('profile/', template_views.profile_view, name='profile'),
    path('change-password/', template_views.change_password_view, name='change_password'),
    
    # Service-related template views
    path('services/', template_views.services_view, name='services'),
    path('services/<int:service_id>/', template_views.service_detail_view, name='service_detail'),
    path('my-services/', template_views.my_services_view, name='my_services'),
    path('add-service/', template_views.add_service_view, name='add_service'),
    path('edit-service/<int:service_id>/', template_views.edit_service_view, name='edit_service'),
    
    # Booking-related template views
    path('bookings/', template_views.bookings_view, name='bookings'),
    path('bookings/<int:booking_id>/', template_views.booking_detail_view, name='booking_detail'),
    
    # API endpoints (keep existing API structure)
    # Health check
    path('api/health/', views.health_check, name='api_health_check'),
    
    # Authentication endpoints
    path('api/auth/register/', views.UserRegistrationView.as_view(), name='api_register'),
    path('api/auth/login/', views.UserLoginView.as_view(), name='api_login'),
    path('api/auth/logout/', views.logout_view, name='api_logout'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('api/auth/change-password/', views.ChangePasswordView.as_view(), name='api_change_password'),
    
    # User profile API
    path('api/profile/', views.UserProfileView.as_view(), name='api_user_profile'),
    
    # Role-based dashboards API
    path('api/dashboard/customer/', views.CustomerDashboardView.as_view(), name='api_customer_dashboard'),
    path('api/dashboard/provider/', views.ProviderDashboardView.as_view(), name='api_provider_dashboard'),
    
    # Profile details API
    path('api/profile/customer/', views.CustomerProfileDetailView.as_view(), name='api_customer_profile_detail'),
    path('api/profile/provider/', views.ProviderProfileDetailView.as_view(), name='api_provider_profile_detail'),
    
    # Service categories API
    path('api/categories/', views.ServiceCategoryListView.as_view(), name='api_service_categories'),
    
    # Provider services API
    path('api/services/', views.ProviderServiceListCreateView.as_view(), name='api_provider_services'),
    path('api/services/<int:pk>/', views.ProviderServiceDetailView.as_view(), name='api_provider_service_detail'),
]
