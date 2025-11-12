from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    USER_ROLES = (
        ('customer', 'Customer'),
        ('provider', 'Service Provider'),
    )
    
    role = models.CharField(max_length=20, choices=USER_ROLES, default='customer')
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")],
        blank=True,
        null=True
    )
    address = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_customer(self):
        return self.role == 'customer'

    @property
    def is_provider(self):
        return self.role == 'provider'


class CustomerProfile(models.Model):
    """
    Extended profile for customers
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    date_of_birth = models.DateField(blank=True, null=True)
    preferred_contact_method = models.CharField(
        max_length=20,
        choices=[('email', 'Email'), ('phone', 'Phone'), ('both', 'Both')],
        default='email'
    )
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=15, blank=True, null=True)
    
    def __str__(self):
        return f"Customer Profile: {self.user.username}"


class ServiceProviderProfile(models.Model):
    """
    Extended profile for service providers
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='provider_profile')
    business_name = models.CharField(max_length=200, blank=True, null=True)
    business_license = models.CharField(max_length=100, blank=True, null=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    description = models.TextField(blank=True, null=True)
    service_radius_km = models.PositiveIntegerField(default=10, help_text="Service radius in kilometers")
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    availability_hours = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="e.g., Mon-Fri 9AM-5PM"
    )
    documents = models.FileField(upload_to='provider_documents/', blank=True, null=True)
    is_background_verified = models.BooleanField(default=False)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    total_reviews = models.PositiveIntegerField(default=0)
    total_jobs_completed = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Provider Profile: {self.user.username} - {self.business_name or 'No Business Name'}"

    def update_rating(self):
        """
        Update average rating based on reviews
        """
        from servicemgmt.models import Review
        reviews = Review.objects.filter(service__provider=self.user)
        if reviews.exists():
            self.average_rating = reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0.00
            self.total_reviews = reviews.count()
        else:
            self.average_rating = 0.00
            self.total_reviews = 0
        self.save()


class ServiceCategory(models.Model):
    """
    Categories for services (e.g., Plumbing, Electrical, etc.)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="CSS class or icon name")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Service Categories"

    def __str__(self):
        return self.name


class ProviderService(models.Model):
    """
    Services offered by providers
    """
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField()
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    price_unit = models.CharField(
        max_length=20,
        choices=[('hour', 'Per Hour'), ('job', 'Per Job'), ('day', 'Per Day')],
        default='hour'
    )
    estimated_duration = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., 2-3 hours")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['provider', 'category', 'name']

    def __str__(self):
        return f"{self.provider.username} - {self.name}"
