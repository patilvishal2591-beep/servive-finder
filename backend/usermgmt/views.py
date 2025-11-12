from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import login
from django.shortcuts import get_object_or_404

from .models import User, CustomerProfile, ServiceProviderProfile, ServiceCategory, ProviderService
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    CustomerProfileSerializer, ServiceProviderProfileSerializer,
    ServiceCategorySerializer, ProviderServiceSerializer, ChangePasswordSerializer
)
from .permissions import IsCustomer, IsProvider, IsOwnerOrReadOnly


class UserRegistrationView(APIView):
    """
    User registration endpoint for both customers and providers
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({
                'message': 'User registered successfully',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(access_token),
                }
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """
    User login endpoint
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            return Response({
                'message': 'Login successful',
                'user': UserProfileSerializer(user).data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(access_token),
                }
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Get and update user profile
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class CustomerDashboardView(APIView):
    """
    Customer dashboard with role-based access
    """
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def get(self, request):
        user = request.user
        try:
            customer_profile = user.customer_profile
            profile_data = CustomerProfileSerializer(customer_profile).data
        except CustomerProfile.DoesNotExist:
            # Create profile if it doesn't exist
            customer_profile = CustomerProfile.objects.create(user=user)
            profile_data = CustomerProfileSerializer(customer_profile).data

        # Get recent bookings (will be implemented in servicemgmt)
        dashboard_data = {
            'user': UserProfileSerializer(user).data,
            'profile': profile_data,
            'dashboard_type': 'customer',
            'stats': {
                'total_bookings': 0,  # Will be updated when booking model is implemented
                'pending_bookings': 0,
                'completed_bookings': 0,
                'total_reviews_given': 0,
            }
        }
        
        return Response(dashboard_data, status=status.HTTP_200_OK)


class ProviderDashboardView(APIView):
    """
    Service provider dashboard with role-based access
    """
    permission_classes = [permissions.IsAuthenticated, IsProvider]

    def get(self, request):
        user = request.user
        try:
            provider_profile = user.provider_profile
            profile_data = ServiceProviderProfileSerializer(provider_profile).data
        except ServiceProviderProfile.DoesNotExist:
            # Create profile if it doesn't exist
            provider_profile = ServiceProviderProfile.objects.create(user=user)
            profile_data = ServiceProviderProfileSerializer(provider_profile).data

        # Get provider services
        services = ProviderService.objects.filter(provider=user, is_active=True)
        services_data = ProviderServiceSerializer(services, many=True).data

        dashboard_data = {
            'user': UserProfileSerializer(user).data,
            'profile': profile_data,
            'services': services_data,
            'dashboard_type': 'provider',
            'stats': {
                'total_services': services.count(),
                'active_bookings': 0,  # Will be updated when booking model is implemented
                'completed_jobs': provider_profile.total_jobs_completed,
                'average_rating': float(provider_profile.average_rating),
                'total_reviews': provider_profile.total_reviews,
            }
        }
        
        return Response(dashboard_data, status=status.HTTP_200_OK)


class CustomerProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    Customer profile detail view
    """
    serializer_class = CustomerProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsCustomer]

    def get_object(self):
        profile, created = CustomerProfile.objects.get_or_create(user=self.request.user)
        return profile


class ProviderProfileDetailView(generics.RetrieveUpdateAPIView):
    """
    Provider profile detail view
    """
    serializer_class = ServiceProviderProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsProvider]

    def get_object(self):
        profile, created = ServiceProviderProfile.objects.get_or_create(user=self.request.user)
        return profile


class ServiceCategoryListView(generics.ListAPIView):
    """
    List all active service categories
    """
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]


class ProviderServiceListCreateView(generics.ListCreateAPIView):
    """
    List and create provider services
    """
    serializer_class = ProviderServiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsProvider]

    def get_queryset(self):
        return ProviderService.objects.filter(provider=self.request.user)


class ProviderServiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete provider services
    """
    serializer_class = ProviderServiceSerializer
    permission_classes = [permissions.IsAuthenticated, IsProvider, IsOwnerOrReadOnly]

    def get_queryset(self):
        return ProviderService.objects.filter(provider=self.request.user)


class ChangePasswordView(APIView):
    """
    Change user password
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """
    Logout user by blacklisting the refresh token
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Invalid token'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def health_check(request):
    """
    Health check endpoint
    """
    return Response({
        'status': 'healthy',
        'message': 'User management service is running'
    }, status=status.HTTP_200_OK)
