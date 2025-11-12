from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
import json

from .models import User, CustomerProfile, ServiceProviderProfile, ServiceCategory, ProviderService
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, 
    CustomerProfileSerializer, ServiceProviderProfileSerializer,
    ProviderServiceSerializer, ChangePasswordSerializer
)
from servicemgmt.models import ServiceBooking, Review


def home_view(request):
    """
    Home page view with featured services and categories
    """
    # Get featured service categories
    categories = ServiceCategory.objects.filter(is_active=True)[:6]
    
    # Get top-rated services
    top_services = ProviderService.objects.filter(
        is_active=True,
        provider__provider_profile__average_rating__gte=4.0
    ).select_related('provider', 'category')[:6]
    
    # Get statistics
    stats = {
        'total_providers': User.objects.filter(role='provider').count(),
        'total_services': ProviderService.objects.filter(is_active=True).count(),
        'total_bookings': ServiceBooking.objects.count(),
        'total_reviews': Review.objects.count(),
    }
    
    context = {
        'categories': categories,
        'top_services': top_services,
        'stats': stats,
    }
    
    return render(request, 'home.html', context)


def register_view(request):
    """
    User registration view
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        serializer = UserRegistrationSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user)
            messages.success(request, f'Welcome to ServiceFinder! Your {user.role} account has been created.')
            return redirect('dashboard')
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    categories = ServiceCategory.objects.filter(is_active=True)
    context = {
        'categories': categories,
    }
    
    return render(request, 'auth/register.html', context)


def login_view(request):
    """
    User login view
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        serializer = UserLoginSerializer(data=request.POST)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            
            # Redirect to next page or dashboard
            next_page = request.GET.get('next', 'dashboard')
            return redirect(next_page)
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, error)
    
    return render(request, 'auth/login.html')


@login_required
def logout_view(request):
    """
    User logout view
    """
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required
def dashboard_view(request):
    """
    Role-based dashboard view
    """
    user = request.user
    
    if user.role == 'customer':
        return customer_dashboard(request)
    elif user.role == 'provider':
        return provider_dashboard(request)
    else:
        messages.error(request, 'Invalid user role.')
        return redirect('home')


def customer_dashboard(request):
    """
    Customer dashboard
    """
    user = request.user
    
    # Get or create customer profile
    customer_profile, created = CustomerProfile.objects.get_or_create(user=user)
    
    # Get recent bookings
    recent_bookings = ServiceBooking.objects.filter(
        customer=user
    ).select_related('service', 'provider').order_by('-created_at')[:5]
    
    # Get booking statistics
    booking_stats = {
        'total_bookings': ServiceBooking.objects.filter(customer=user).count(),
        'pending_bookings': ServiceBooking.objects.filter(customer=user, status='pending').count(),
        'completed_bookings': ServiceBooking.objects.filter(customer=user, status='completed').count(),
        'total_reviews_given': Review.objects.filter(customer=user).count(),
    }
    
    context = {
        'user': user,
        'profile': customer_profile,
        'recent_bookings': recent_bookings,
        'stats': booking_stats,
        'dashboard_type': 'customer',
    }
    
    return render(request, 'dashboard/customer.html', context)


def provider_dashboard(request):
    """
    Service provider dashboard
    """
    user = request.user
    
    # Get or create provider profile
    provider_profile, created = ServiceProviderProfile.objects.get_or_create(user=user)
    
    # Get provider services
    services = ProviderService.objects.filter(provider=user, is_active=True)
    
    # Get recent bookings
    recent_bookings = ServiceBooking.objects.filter(
        provider=user
    ).select_related('service', 'customer').order_by('-created_at')[:5]
    
    # Get provider statistics
    provider_stats = {
        'total_services': services.count(),
        'active_bookings': ServiceBooking.objects.filter(
            provider=user, 
            status__in=['pending', 'confirmed', 'in_progress']
        ).count(),
        'completed_jobs': provider_profile.total_jobs_completed,
        'average_rating': float(provider_profile.average_rating),
        'total_reviews': provider_profile.total_reviews,
    }
    
    context = {
        'user': user,
        'profile': provider_profile,
        'services': services,
        'recent_bookings': recent_bookings,
        'stats': provider_stats,
        'dashboard_type': 'provider',
    }
    
    return render(request, 'dashboard/provider.html', context)


@login_required
def profile_view(request):
    """
    User profile view and update
    """
    user = request.user
    
    if request.method == 'POST':
        # Update basic user info
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone_number = request.POST.get('phone_number', '')
        user.save()
        
        # Update role-specific profile
        if user.role == 'customer':
            profile, created = CustomerProfile.objects.get_or_create(user=user)
            profile.address = request.POST.get('address', '')
            profile.city = request.POST.get('city', '')
            profile.state = request.POST.get('state', '')
            profile.zip_code = request.POST.get('zip_code', '')
            if request.POST.get('latitude'):
                profile.latitude = float(request.POST.get('latitude'))
            if request.POST.get('longitude'):
                profile.longitude = float(request.POST.get('longitude'))
            profile.save()
            
        elif user.role == 'provider':
            profile, created = ServiceProviderProfile.objects.get_or_create(user=user)
            profile.business_name = request.POST.get('business_name', '')
            profile.bio = request.POST.get('bio', '')
            profile.address = request.POST.get('address', '')
            profile.city = request.POST.get('city', '')
            profile.state = request.POST.get('state', '')
            profile.zip_code = request.POST.get('zip_code', '')
            profile.experience_years = int(request.POST.get('experience_years', 0))
            if request.POST.get('latitude'):
                profile.latitude = float(request.POST.get('latitude'))
            if request.POST.get('longitude'):
                profile.longitude = float(request.POST.get('longitude'))
            profile.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('profile')
    
    # Get profile data
    if user.role == 'customer':
        profile, created = CustomerProfile.objects.get_or_create(user=user)
    elif user.role == 'provider':
        profile, created = ServiceProviderProfile.objects.get_or_create(user=user)
    else:
        profile = None
    
    context = {
        'user': user,
        'profile': profile,
    }
    
    return render(request, 'profile/edit.html', context)


@login_required
def change_password_view(request):
    """
    Change password view
    """
    if request.method == 'POST':
        serializer = ChangePasswordSerializer(data=request.POST, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            messages.success(request, 'Password changed successfully!')
            return redirect('login')
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, error)
    
    return render(request, 'profile/change_password.html')


def services_view(request):
    """
    Service search and listing view
    """
    # Get search parameters
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    min_rating = request.GET.get('min_rating', '')
    max_price = request.GET.get('max_price', '')
    experience_years = request.GET.get('experience_years', '')
    
    # Base queryset
    services = ProviderService.objects.filter(is_active=True).select_related(
        'provider', 'category', 'provider__provider_profile'
    )
    
    # Apply filters
    if query:
        services = services.filter(name__icontains=query)
    
    if category_id:
        services = services.filter(category_id=category_id)
    
    if min_rating:
        services = services.filter(provider__provider_profile__average_rating__gte=float(min_rating))
    
    if max_price:
        services = services.filter(price_per_hour__lte=float(max_price))
    
    if experience_years:
        services = services.filter(experience_years__gte=int(experience_years))
    
    # Pagination
    paginator = Paginator(services, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get categories for filter
    categories = ServiceCategory.objects.filter(is_active=True)
    
    context = {
        'services': page_obj,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
        'min_rating': min_rating,
        'max_price': max_price,
        'experience_years': experience_years,
    }
    
    return render(request, 'services/list.html', context)


def service_detail_view(request, service_id):
    """
    Service detail view
    """
    service = get_object_or_404(ProviderService, id=service_id, is_active=True)
    
    # Get reviews for this service
    reviews = Review.objects.filter(
        service=service
    ).select_related('customer').order_by('-created_at')[:10]
    
    # Get related services
    related_services = ProviderService.objects.filter(
        category=service.category,
        is_active=True
    ).exclude(id=service.id)[:4]
    
    context = {
        'service': service,
        'reviews': reviews,
        'related_services': related_services,
    }
    
    return render(request, 'services/detail.html', context)


@login_required
def my_services_view(request):
    """
    Provider's service management view
    """
    if request.user.role != 'provider':
        messages.error(request, 'Access denied. Provider account required.')
        return redirect('dashboard')
    
    services = ProviderService.objects.filter(provider=request.user)
    categories = ServiceCategory.objects.filter(is_active=True)
    
    context = {
        'services': services,
        'categories': categories,
    }
    
    return render(request, 'services/my_services.html', context)


@login_required
def add_service_view(request):
    """
    Add new service view
    """
    if request.user.role != 'provider':
        messages.error(request, 'Access denied. Provider account required.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        data = request.POST.copy()
        data['provider'] = request.user.id
        
        serializer = ProviderServiceSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            messages.success(request, 'Service added successfully!')
            return redirect('my_services')
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    categories = ServiceCategory.objects.filter(is_active=True)
    context = {
        'categories': categories,
    }
    
    return render(request, 'services/add.html', context)


@login_required
def edit_service_view(request, service_id):
    """
    Edit service view
    """
    service = get_object_or_404(ProviderService, id=service_id, provider=request.user)
    
    if request.method == 'POST':
        serializer = ProviderServiceSerializer(service, data=request.POST, partial=True)
        if serializer.is_valid():
            serializer.save()
            messages.success(request, 'Service updated successfully!')
            return redirect('my_services')
        else:
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    
    categories = ServiceCategory.objects.filter(is_active=True)
    context = {
        'service': service,
        'categories': categories,
    }
    
    return render(request, 'services/edit.html', context)


@login_required
def bookings_view(request):
    """
    User bookings view (customer or provider)
    """
    user = request.user
    
    if user.role == 'customer':
        bookings = ServiceBooking.objects.filter(
            customer=user
        ).select_related('service', 'provider').order_by('-created_at')
        template = 'bookings/customer_bookings.html'
    elif user.role == 'provider':
        bookings = ServiceBooking.objects.filter(
            provider=user
        ).select_related('service', 'customer').order_by('-created_at')
        template = 'bookings/provider_bookings.html'
    else:
        messages.error(request, 'Invalid user role.')
        return redirect('dashboard')
    
    # Pagination
    paginator = Paginator(bookings, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'bookings': page_obj,
    }
    
    return render(request, template, context)


@login_required
def booking_detail_view(request, booking_id):
    """
    Booking detail view
    """
    user = request.user
    
    if user.role == 'customer':
        booking = get_object_or_404(ServiceBooking, id=booking_id, customer=user)
    elif user.role == 'provider':
        booking = get_object_or_404(ServiceBooking, id=booking_id, provider=user)
    else:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')
    
    context = {
        'booking': booking,
    }
    
    return render(request, 'bookings/detail.html', context)
