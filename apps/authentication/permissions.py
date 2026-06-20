"""
Role-Based Access Control Permissions
"""
from rest_framework.permissions import BasePermission
from .models import UserRole


class IsAdmin(BasePermission):
    """Only Admin users can access."""
    message = "Access restricted to Admin users only."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.ADMIN
        )


class IsManager(BasePermission):
    """Only Manager users can access."""
    message = "Access restricted to Manager users only."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == UserRole.MANAGER
        )


class IsAdminOrManager(BasePermission):
    """Admin or Manager users can access."""
    message = "Access restricted to Admin or Manager users."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in [UserRole.ADMIN, UserRole.MANAGER]
        )


class IsAdminOrManagerOrReadOnly(BasePermission):
    """
    Admin/Manager can write; Employees get read-only on their assigned tasks.
    """
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.role in [UserRole.ADMIN, UserRole.MANAGER]


class IsOwnerOrAdminOrManager(BasePermission):
    """Object-level: owner, admin, or manager can access."""

    def has_object_permission(self, request, view, obj):
        if request.user.role in [UserRole.ADMIN, UserRole.MANAGER]:
            return True
        # Employee can only access tasks assigned to them
        assigned_to = getattr(obj, "assigned_to", None)
        return assigned_to == request.user
