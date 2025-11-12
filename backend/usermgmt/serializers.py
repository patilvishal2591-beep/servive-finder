from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, CustomerProfile, ServiceProviderProfile, ServiceCategory, ProviderService


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 
                 'last_name', 'role', 'phone_number', 'address', 'latitude', 'longitude')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        
        # Create role-specific profile
        if user.role == 'customer':
            CustomerProfile.objects.create(user=user)
        elif user.role == 'provider':
            ServiceProviderProfile.objects.create(user=user)
        
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Invalid credentials')
            if not user.is_active:
                raise serializers.ValidationError('User account is disabled')
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError('Must include username and password')


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 
                 'role_display', 'phone_number', 'address', 'latitude', 'longitude',
                 'profile_image', 'is_verified', 'date_joined', 'last_login')
        read_only_fields = ('id', 'username', 'date_joined', 'last_login', 'is_verified')


class CustomerProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for customer profile
    """
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = CustomerProfile
        fields = '__all__'


class ServiceProviderProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for service provider profile
    """
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = ServiceProviderProfile
        fields = '__all__'
        read_only_fields = ('average_rating', 'total_reviews', 'total_jobs_completed')


class ServiceCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for service categories
    """
    class Meta:
        model = ServiceCategory
        fields = '__all__'
        read_only_fields = ('created_at',)


class ProviderServiceSerializer(serializers.ModelSerializer):
    """
    Serializer for provider services
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    provider_name = serializers.CharField(source='provider.get_full_name', read_only=True)
    
    class Meta:
        model = ProviderService
        fields = '__all__'
        read_only_fields = ('provider', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['provider'] = self.context['request'].user
        return super().create(validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing password
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match")
        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
