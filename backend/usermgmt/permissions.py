from rest_framework import permissions


class IsCustomer(permissions.BasePermission):
    """
    Custom permission to only allow customers to access customer-specific views.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'customer'


class IsProvider(permissions.BasePermission):
    """
    Custom permission to only allow service providers to access provider-specific views.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'provider'


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object.
        return obj.provider == request.user


class IsCustomerOrProvider(permissions.BasePermission):
    """
    Custom permission to allow both customers and providers.
    """
    
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                request.user.role in ['customer', 'provider'])


class IsVerifiedProvider(permissions.BasePermission):
    """
    Custom permission to only allow verified service providers.
    """
    
    def has_permission(self, request, view):
        return (request.user and request.user.is_authenticated and 
                request.user.role == 'provider' and request.user.is_verified)
