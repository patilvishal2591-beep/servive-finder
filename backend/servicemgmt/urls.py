from django.urls import path
from . import views

app_name = 'servicemgmt'

urlpatterns = [
    # Service search and discovery
    path('search/', views.ServiceSearchView.as_view(), name='service-search'),
    path('categories/', views.service_categories, name='service-categories'),
    
    # Service bookings
    path('bookings/', views.ServiceBookingListCreateView.as_view(), name='booking-list-create'),
    path('bookings/<int:pk>/', views.ServiceBookingDetailView.as_view(), name='booking-detail'),
    path('bookings/<int:booking_id>/cancel/', views.cancel_booking, name='cancel-booking'),
    
    # Reviews and ratings
    path('reviews/', views.ReviewListCreateView.as_view(), name='review-list-create'),
    path('providers/<int:provider_id>/reviews/', views.provider_reviews, name='provider-reviews'),
    
    # Payments
    path('payments/', views.PaymentListCreateView.as_view(), name='payment-list-create'),
    path('bookings/<int:booking_id>/pay/', views.ProcessPaymentView.as_view(), name='process-payment'),
    
    # Provider availability
    path('availability/', views.ServiceAvailabilityListCreateView.as_view(), name='availability-list-create'),
    
    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:notification_id>/read/', views.MarkNotificationReadView.as_view(), name='mark-notification-read'),
    
    # Dashboard and statistics
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('booking-stats/', views.booking_stats, name='booking-stats'),
]
