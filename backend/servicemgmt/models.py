from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

User = get_user_model()


class ServiceBooking(models.Model):
    """
    Model for service bookings
    """
    BOOKING_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    )

    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )

    booking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_bookings')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='provider_bookings')
    service = models.ForeignKey('usermgmt.ProviderService', on_delete=models.CASCADE, related_name='bookings')
    
    # Booking details
    booking_date = models.DateTimeField()
    estimated_duration = models.CharField(max_length=50, blank=True, null=True)
    special_instructions = models.TextField(blank=True, null=True)
    
    # Location details
    service_address = models.TextField()
    service_latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    service_longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    distance_km = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    estimated_travel_time = models.CharField(max_length=50, blank=True, null=True)
    
    # Status and pricing
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='pending')
    quoted_price = models.DecimalField(max_digits=10, decimal_places=2)
    final_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    
    # Provider response
    provider_notes = models.TextField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Booking {self.booking_id} - {self.customer.username} -> {self.provider.username}"

    def save(self, *args, **kwargs):
        # Set timestamps based on status changes
        if self.status == 'confirmed' and not self.confirmed_at:
            self.confirmed_at = timezone.now()
        elif self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status == 'cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        
        super().save(*args, **kwargs)

    @property
    def can_be_reviewed(self):
        """Check if booking can be reviewed by customer"""
        return self.status == 'completed' and not hasattr(self, 'review')

    @property
    def is_active(self):
        """Check if booking is in active state"""
        return self.status in ['pending', 'confirmed', 'in_progress']


class Review(models.Model):
    """
    Model for customer reviews and ratings
    """
    booking = models.OneToOneField(ServiceBooking, on_delete=models.CASCADE, related_name='review')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    service = models.ForeignKey('usermgmt.ProviderService', on_delete=models.CASCADE, related_name='reviews')
    
    # Rating and review content
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(max_length=200, blank=True, null=True)
    comment = models.TextField(blank=True, null=True)
    
    # Review categories
    quality_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Quality of work rating"
    )
    punctuality_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Punctuality rating"
    )
    communication_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Communication rating"
    )
    value_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Value for money rating"
    )
    
    # Metadata
    is_verified = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    helpful_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['booking', 'customer']

    def __str__(self):
        return f"Review by {self.customer.username} for {self.provider.username} - {self.rating} stars"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update provider's average rating
        if hasattr(self.provider, 'provider_profile'):
            self.provider.provider_profile.update_rating()


class Payment(models.Model):
    """
    Model for payment transactions (fake payment gateway)
    """
    PAYMENT_METHODS = (
        ('cash', 'Cash'),
        ('online', 'Online Payment'),
        ('card', 'Credit/Debit Card'),
        ('wallet', 'Digital Wallet'),
    )

    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    )

    payment_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    booking = models.ForeignKey(ServiceBooking, on_delete=models.CASCADE, related_name='payments')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Transaction details (fake gateway simulation)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    gateway_response = models.JSONField(blank=True, null=True)
    failure_reason = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    failed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.payment_id} - {self.amount} ({self.status})"

    def save(self, *args, **kwargs):
        # Set timestamps based on status changes
        if self.status == 'processing' and not self.processed_at:
            self.processed_at = timezone.now()
        elif self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
            # Update booking payment status
            self.booking.payment_status = 'paid'
            self.booking.save()
        elif self.status == 'failed' and not self.failed_at:
            self.failed_at = timezone.now()
            # Update booking payment status
            self.booking.payment_status = 'failed'
            self.booking.save()
        
        super().save(*args, **kwargs)

    def process_fake_payment(self):
        """
        Simulate payment processing with fake gateway
        """
        import random
        import time
        
        self.status = 'processing'
        self.transaction_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
        self.save()
        
        # Simulate processing delay
        time.sleep(1)
        
        # Simulate success/failure (90% success rate)
        if random.random() < 0.9:
            self.status = 'completed'
            self.gateway_response = {
                'status': 'success',
                'transaction_id': self.transaction_id,
                'message': 'Payment processed successfully',
                'gateway': 'FakePaymentGateway',
                'timestamp': timezone.now().isoformat()
            }
        else:
            self.status = 'failed'
            self.failure_reason = 'Insufficient funds or card declined'
            self.gateway_response = {
                'status': 'failed',
                'error_code': 'CARD_DECLINED',
                'message': self.failure_reason,
                'gateway': 'FakePaymentGateway',
                'timestamp': timezone.now().isoformat()
            }
        
        self.save()
        return self.status == 'completed'


class ServiceAvailability(models.Model):
    """
    Model for provider availability slots
    """
    DAYS_OF_WEEK = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availability_slots')
    day_of_week = models.IntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    max_bookings_per_slot = models.PositiveIntegerField(default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['provider', 'day_of_week', 'start_time']
        ordering = ['day_of_week', 'start_time']

    def __str__(self):
        return f"{self.provider.username} - {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"


class ServiceImage(models.Model):
    """
    Model for service-related images
    """
    service = models.ForeignKey('usermgmt.ProviderService', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='service_images/')
    caption = models.CharField(max_length=200, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_primary', '-uploaded_at']

    def __str__(self):
        return f"Image for {self.service.name}"

    def save(self, *args, **kwargs):
        # Ensure only one primary image per service
        if self.is_primary:
            ServiceImage.objects.filter(service=self.service, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class Notification(models.Model):
    """
    Model for user notifications
    """
    NOTIFICATION_TYPES = (
        ('booking_request', 'Booking Request'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('booking_completed', 'Booking Completed'),
        ('payment_received', 'Payment Received'),
        ('review_received', 'Review Received'),
        ('system', 'System Notification'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects
    booking = models.ForeignKey(ServiceBooking, on_delete=models.CASCADE, blank=True, null=True)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, blank=True, null=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
