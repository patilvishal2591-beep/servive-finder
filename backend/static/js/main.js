// ServiceFinder Main JavaScript

// Global variables
let userLocation = null;
let map = null;
let markers = [];

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

// Main initialization function
function initializeApp() {
    // Initialize geolocation
    initializeGeolocation();
    
    // Initialize forms
    initializeForms();
    
    // Initialize maps if map container exists
    if (document.getElementById('map')) {
        initializeMap();
    }
    
    // Initialize service search
    initializeServiceSearch();
    
    // Initialize rating systems
    initializeRatings();
    
    // Initialize booking functionality
    initializeBookings();
    
    // Initialize notifications
    initializeNotifications();
}

// Geolocation functionality
function initializeGeolocation() {
    const locationBtn = document.getElementById('get-location-btn');
    if (locationBtn) {
        locationBtn.addEventListener('click', getCurrentLocation);
    }
    
    // Auto-detect location on service search page
    if (document.getElementById('services-page')) {
        getCurrentLocation();
    }
}

function getCurrentLocation() {
    const locationBtn = document.getElementById('get-location-btn');
    const locationStatus = document.getElementById('location-status');
    
    if (locationBtn) {
        locationBtn.innerHTML = '<span class="loading-spinner"></span> Getting location...';
        locationBtn.disabled = true;
    }
    
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(position) {
                userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                
                // Update UI
                if (locationStatus) {
                    locationStatus.innerHTML = `<i class="bi bi-geo-alt-fill text-success"></i> Location detected`;
                }
                
                if (locationBtn) {
                    locationBtn.innerHTML = '<i class="bi bi-geo-alt"></i> Location Detected';
                    locationBtn.classList.remove('btn-outline-primary');
                    locationBtn.classList.add('btn-success');
                }
                
                // Update hidden form fields
                const latField = document.getElementById('user-lat');
                const lngField = document.getElementById('user-lng');
                if (latField) latField.value = userLocation.lat;
                if (lngField) lngField.value = userLocation.lng;
                
                // Update map if exists
                if (map) {
                    map.setView([userLocation.lat, userLocation.lng], 13);
                    addUserLocationMarker();
                }
                
                // Trigger service search if on services page
                if (document.getElementById('services-page')) {
                    searchServices();
                }
            },
            function(error) {
                console.error('Geolocation error:', error);
                if (locationStatus) {
                    locationStatus.innerHTML = `<i class="bi bi-exclamation-triangle text-warning"></i> Location access denied`;
                }
                
                if (locationBtn) {
                    locationBtn.innerHTML = '<i class="bi bi-geo-alt"></i> Get Location';
                    locationBtn.disabled = false;
                }
                
                showAlert('Unable to get your location. Please enter your address manually.', 'warning');
            }
        );
    } else {
        showAlert('Geolocation is not supported by this browser.', 'error');
        if (locationBtn) {
            locationBtn.innerHTML = '<i class="bi bi-geo-alt"></i> Get Location';
            locationBtn.disabled = false;
        }
    }
}

// Map functionality
function initializeMap() {
    const mapContainer = document.getElementById('map');
    if (!mapContainer) return;
    
    // Initialize Leaflet map
    map = L.map('map').setView([40.7128, -74.0060], 10); // Default to NYC
    
    // Add OpenStreetMap tiles
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Add dark theme tiles for better integration
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '© OpenStreetMap contributors © CARTO',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);
}

function addUserLocationMarker() {
    if (!map || !userLocation) return;
    
    // Remove existing user marker
    markers.forEach(marker => {
        if (marker.options.isUser) {
            map.removeLayer(marker);
        }
    });
    
    // Add user location marker
    const userMarker = L.marker([userLocation.lat, userLocation.lng], {
        isUser: true
    }).addTo(map);
    
    userMarker.bindPopup('<strong>Your Location</strong>').openPopup();
    markers.push(userMarker);
}

function addServiceMarkers(services) {
    if (!map) return;
    
    // Clear existing service markers
    markers.forEach(marker => {
        if (!marker.options.isUser) {
            map.removeLayer(marker);
        }
    });
    
    // Add service markers
    services.forEach(service => {
        if (service.provider_latitude && service.provider_longitude) {
            const marker = L.marker([service.provider_latitude, service.provider_longitude])
                .addTo(map);
            
            const popupContent = `
                <div class="service-popup">
                    <h6>${service.name}</h6>
                    <p class="mb-1">${service.category_name}</p>
                    <p class="mb-1">Rating: ${generateStars(service.average_rating)}</p>
                    <p class="mb-1 text-success">$${service.price_per_hour}/hour</p>
                    <p class="mb-0 text-info">${service.distance}km away</p>
                </div>
            `;
            
            marker.bindPopup(popupContent);
            markers.push(marker);
        }
    });
}

// Form handling
function initializeForms() {
    // Add form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });
    
    // Handle AJAX forms
    const ajaxForms = document.querySelectorAll('.ajax-form');
    ajaxForms.forEach(form => {
        form.addEventListener('submit', handleAjaxForm);
    });
}

function handleAjaxForm(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const submitBtn = form.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    
    // Show loading state
    submitBtn.innerHTML = '<span class="loading-spinner"></span> Processing...';
    submitBtn.disabled = true;
    
    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert(data.message, 'success');
            if (data.redirect) {
                setTimeout(() => {
                    window.location.href = data.redirect;
                }, 1500);
            }
        } else {
            showAlert(data.message || 'An error occurred', 'error');
        }
    })
    .catch(error => {
        console.error('Form submission error:', error);
        showAlert('An error occurred while processing your request', 'error');
    })
    .finally(() => {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    });
}

// Service search functionality
function initializeServiceSearch() {
    const searchForm = document.getElementById('service-search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(event) {
            event.preventDefault();
            searchServices();
        });
    }
    
    // Initialize filter changes
    const filterInputs = document.querySelectorAll('.filter-input');
    filterInputs.forEach(input => {
        input.addEventListener('change', debounce(searchServices, 500));
    });
}

function searchServices() {
    const searchForm = document.getElementById('service-search-form');
    if (!searchForm) return;
    
    const formData = new FormData(searchForm);
    const searchResults = document.getElementById('search-results');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    // Add user location to form data
    if (userLocation) {
        formData.append('user_lat', userLocation.lat);
        formData.append('user_lng', userLocation.lng);
    }
    
    // Show loading
    if (loadingIndicator) {
        loadingIndicator.style.display = 'block';
    }
    if (searchResults) {
        searchResults.style.opacity = '0.5';
    }
    
    fetch('/api/services/search/', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displaySearchResults(data.services);
            addServiceMarkers(data.services);
        } else {
            showAlert('Error searching services', 'error');
        }
    })
    .catch(error => {
        console.error('Search error:', error);
        showAlert('Error searching services', 'error');
    })
    .finally(() => {
        if (loadingIndicator) {
            loadingIndicator.style.display = 'none';
        }
        if (searchResults) {
            searchResults.style.opacity = '1';
        }
    });
}

function displaySearchResults(services) {
    const resultsContainer = document.getElementById('search-results');
    if (!resultsContainer) return;
    
    if (services.length === 0) {
        resultsContainer.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-search display-1 text-muted"></i>
                <h4 class="mt-3">No services found</h4>
                <p class="text-muted">Try adjusting your search criteria or location</p>
            </div>
        `;
        return;
    }
    
    const nearbyServices = services.filter(s => s.distance <= 10);
    const distantServices = services.filter(s => s.distance > 10);
    
    let html = '';
    
    if (nearbyServices.length > 0) {
        html += '<h4 class="mb-3"><i class="bi bi-geo-alt text-primary"></i> Nearby Services</h4>';
        html += '<div class="row">';
        nearbyServices.forEach(service => {
            html += generateServiceCard(service);
        });
        html += '</div>';
    }
    
    if (distantServices.length > 0) {
        html += '<h4 class="mb-3 mt-5"><i class="bi bi-geo text-warning"></i> Services Further Away</h4>';
        html += '<div class="row">';
        distantServices.forEach(service => {
            html += generateServiceCard(service);
        });
        html += '</div>';
    }
    
    resultsContainer.innerHTML = html;
    
    // Initialize booking buttons
    initializeBookingButtons();
}

function generateServiceCard(service) {
    return `
        <div class="col-md-6 col-lg-4 mb-4">
            <div class="card service-card h-100">
                ${service.image ? `<img src="${service.image}" class="card-img-top" style="height: 200px; object-fit: cover;" alt="${service.name}">` : ''}
                <div class="card-body">
                    <h5 class="card-title">${service.name}</h5>
                    <p class="card-text text-muted">${service.description}</p>
                    <div class="mb-2">
                        <span class="badge bg-secondary">${service.category_name}</span>
                        <span class="badge bg-info">${service.experience_years} years exp.</span>
                    </div>
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div class="rating-stars">
                            ${generateStars(service.average_rating)}
                            <small class="text-muted">(${service.total_reviews})</small>
                        </div>
                        <div class="service-price">$${service.price_per_hour}/hr</div>
                    </div>
                    <div class="service-distance mb-3">
                        <i class="bi bi-geo-alt"></i> ${service.distance}km away
                        ${service.estimated_time ? `• ${service.estimated_time} mins` : ''}
                    </div>
                </div>
                <div class="card-footer bg-transparent">
                    <button class="btn btn-primary w-100 book-service-btn" 
                            data-service-id="${service.id}"
                            data-provider-id="${service.provider_id}">
                        <i class="bi bi-calendar-plus"></i> Book Service
                    </button>
                </div>
            </div>
        </div>
    `;
}

function generateStars(rating) {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);
    
    let stars = '';
    for (let i = 0; i < fullStars; i++) {
        stars += '<i class="bi bi-star-fill"></i>';
    }
    if (hasHalfStar) {
        stars += '<i class="bi bi-star-half"></i>';
    }
    for (let i = 0; i < emptyStars; i++) {
        stars += '<i class="bi bi-star"></i>';
    }
    
    return stars;
}

// Rating functionality
function initializeRatings() {
    const ratingInputs = document.querySelectorAll('.rating-input');
    ratingInputs.forEach(ratingInput => {
        const stars = ratingInput.querySelectorAll('label');
        stars.forEach(star => {
            star.addEventListener('click', function() {
                const rating = this.getAttribute('for').split('-').pop();
                updateRatingDisplay(ratingInput, rating);
            });
        });
    });
}

function updateRatingDisplay(ratingInput, rating) {
    const stars = ratingInput.querySelectorAll('label');
    stars.forEach((star, index) => {
        if (index < rating) {
            star.style.color = '#ffc107';
        } else {
            star.style.color = '#ddd';
        }
    });
}

// Booking functionality
function initializeBookings() {
    initializeBookingButtons();
}

function initializeBookingButtons() {
    const bookingBtns = document.querySelectorAll('.book-service-btn');
    bookingBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const serviceId = this.dataset.serviceId;
            const providerId = this.dataset.providerId;
            showBookingModal(serviceId, providerId);
        });
    });
}

function showBookingModal(serviceId, providerId) {
    // Create booking modal dynamically
    const modalHtml = `
        <div class="modal fade" id="bookingModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Book Service</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form id="booking-form" class="ajax-form" action="/api/bookings/create/">
                            <input type="hidden" name="service_id" value="${serviceId}">
                            <input type="hidden" name="provider_id" value="${providerId}">
                            
                            <div class="mb-3">
                                <label for="booking-date" class="form-label">Preferred Date</label>
                                <input type="date" class="form-control" id="booking-date" name="preferred_date" required>
                            </div>
                            
                            <div class="mb-3">
                                <label for="booking-time" class="form-label">Preferred Time</label>
                                <input type="time" class="form-control" id="booking-time" name="preferred_time" required>
                            </div>
                            
                            <div class="mb-3">
                                <label for="booking-description" class="form-label">Service Description</label>
                                <textarea class="form-control" id="booking-description" name="description" rows="3" 
                                         placeholder="Describe what you need help with..." required></textarea>
                            </div>
                            
                            <div class="mb-3">
                                <label for="payment-method" class="form-label">Payment Method</label>
                                <select class="form-select" id="payment-method" name="payment_method" required>
                                    <option value="">Select payment method</option>
                                    <option value="cash">Cash</option>
                                    <option value="online">Online Payment</option>
                                </select>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="submit" form="booking-form" class="btn btn-primary">Book Service</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal
    const existingModal = document.getElementById('bookingModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to DOM
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Initialize form handling
    const form = document.getElementById('booking-form');
    form.addEventListener('submit', handleAjaxForm);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('bookingModal'));
    modal.show();
    
    // Set minimum date to today
    const dateInput = document.getElementById('booking-date');
    const today = new Date().toISOString().split('T')[0];
    dateInput.min = today;
}

// Notification functionality
function initializeNotifications() {
    // Check for new notifications periodically
    if (document.querySelector('[data-user-authenticated="true"]')) {
        setInterval(checkNotifications, 30000); // Check every 30 seconds
    }
}

function checkNotifications() {
    fetch('/api/notifications/unread/')
    .then(response => response.json())
    .then(data => {
        if (data.count > 0) {
            updateNotificationBadge(data.count);
        }
    })
    .catch(error => {
        console.error('Notification check error:', error);
    });
}

function updateNotificationBadge(count) {
    let badge = document.getElementById('notification-badge');
    if (!badge) {
        // Create badge if it doesn't exist
        const navLink = document.querySelector('a[href*="notifications"]');
        if (navLink) {
            badge = document.createElement('span');
            badge.id = 'notification-badge';
            badge.className = 'badge bg-danger rounded-pill ms-1';
            navLink.appendChild(badge);
        }
    }
    
    if (badge) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = count > 0 ? 'inline' : 'none';
    }
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertTypes = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    };
    
    const alertClass = alertTypes[type] || 'alert-info';
    const alertHtml = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    // Find or create alert container
    let alertContainer = document.getElementById('alert-container');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'alert-container';
        alertContainer.className = 'container mt-3';
        document.querySelector('main').insertBefore(alertContainer, document.querySelector('main').firstChild);
    }
    
    alertContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alert = alertContainer.querySelector('.alert:last-child');
        if (alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }
    }, 5000);
}

function getCsrfToken() {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfToken ? csrfToken.value : '';
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Export functions for global access
window.ServiceFinder = {
    getCurrentLocation,
    searchServices,
    showBookingModal,
    showAlert,
    generateStars
};
