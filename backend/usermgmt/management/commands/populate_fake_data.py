from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from usermgmt.models import ServiceCategory, ProviderService, CustomerProfile, ServiceProviderProfile
from servicemgmt.models import ServiceBooking, Review, Payment
import random
from decimal import Decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with fake data for testing'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating fake data...'))
        
        # Create service categories first
        categories = [
            'Plumbing', 'Electrical', 'Painting', 'Carpentry', 
            'Cleaning', 'Gardening', 'Appliance Repair', 'HVAC'
        ]
        
        category_objects = []
        for cat_name in categories:
            category, created = ServiceCategory.objects.get_or_create(
                name=cat_name,
                defaults={'description': f'{cat_name} services'}
            )
            category_objects.append(category)
            if created:
                self.stdout.write(f'Created category: {cat_name}')
        
        # Create fake customers
        customers = []
        for i in range(10):
            username = f'customer{i+1}'
            email = f'customer{i+1}@example.com'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': f'Customer{i+1}',
                    'last_name': 'User',
                    'role': 'customer',
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                
                # Update user with location data
                user.phone_number = f'+1234567{i:03d}'
                user.address = f'{i+1}00 Main St, City, State'
                user.latitude = 40.7128 + (i * 0.01)
                user.longitude = -74.0060 + (i * 0.01)
                user.save()
                
                # Create customer profile
                CustomerProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'preferred_contact_method': 'both',
                    }
                )
                customers.append(user)
                self.stdout.write(f'Created customer: {username}')

        # Create fake service providers
        providers = []
        for i in range(5):
            username = f'provider{i+1}'
            email = f'provider{i+1}@example.com'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': f'Provider{i+1}',
                    'last_name': 'Service',
                    'role': 'provider',
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                
                # Update user with location data
                user.phone_number = f'+1234567{i+100:03d}'
                user.address = f'{i+1}00 Business Ave, City, State'
                user.latitude = 40.7128 + (i * 0.02)
                user.longitude = -74.0060 + (i * 0.02)
                user.save()
                
                # Create provider profile
                ServiceProviderProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'business_name': f'{user.first_name} Services',
                        'years_of_experience': random.randint(1, 15),
                        'description': f'Professional {categories[i]} services with {random.randint(1, 15)} years of experience.',
                        'hourly_rate': Decimal(str(random.randint(25, 100))),
                        'service_radius_km': random.randint(5, 20),
                    }
                )
                
                # Create services for each provider
                for j in range(random.randint(1, 3)):
                    category = random.choice(category_objects)
                    ProviderService.objects.get_or_create(
                        provider=user,
                        category=category,
                        defaults={
                            'name': f'{category.name} Service {j+1}',
                            'description': f'Professional {category.name.lower()} service',
                            'base_price': Decimal(str(random.randint(50, 200))),
                            'estimated_duration': f'{random.randint(1, 8)} hours',
                        }
                    )
                
                providers.append(user)
                self.stdout.write(f'Created provider: {username}')

        # Create some sample bookings and reviews
        if customers and providers:
            for i in range(5):
                customer = random.choice(customers)
                provider = random.choice(providers)
                service = ProviderService.objects.filter(provider=provider).first()
                
                if service:
                    booking, created = ServiceBooking.objects.get_or_create(
                        customer=customer,
                        service=service,
                        defaults={
                            'status': random.choice(['pending', 'confirmed', 'completed']),
                            'total_amount': service.base_price,
                            'notes': f'Sample booking {i+1}',
                        }
                    )
                    
                    if created and booking.status == 'completed':
                        # Create a review for completed bookings
                        Review.objects.get_or_create(
                            booking=booking,
                            defaults={
                                'rating': random.randint(3, 5),
                                'comment': f'Great service! Very professional and timely.',
                            }
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {len(customers)} customers, {len(providers)} providers, '
                f'{len(category_objects)} categories, and sample bookings with reviews'
            )
        )
