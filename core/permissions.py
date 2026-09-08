from rest_framework import permissions

class IsUserOwner(permissions.BasePermission):
    """
    Custom permission to only allow users to edit/delete their own account or admins.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            return True
        return obj == request.user

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit/delete it, or admins.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            return True
        return hasattr(obj, 'user') and obj.user == request.user
