"""
Authentication Service Layer - Business logic lives here, not in views.
"""
import logging
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from rest_framework.exceptions import PermissionDenied, NotFound

from .models import UserRole

User = get_user_model()
logger = logging.getLogger(__name__)


class UserService:
    """All user-related business logic."""

    @staticmethod
    def get_all_users(requesting_user) -> QuerySet:
        """Admin sees all; Manager sees employees; Employee sees only self."""
        if requesting_user.role == UserRole.ADMIN:
            return User.objects.all()
        elif requesting_user.role == UserRole.MANAGER:
            return User.objects.filter(role=UserRole.EMPLOYEE)
        return User.objects.filter(id=requesting_user.id)

    @staticmethod
    def get_user_by_id(user_id: int, requesting_user) -> User:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFound(f"User with id={user_id} not found.")

        # Employees can only see themselves
        if requesting_user.role == UserRole.EMPLOYEE and user.id != requesting_user.id:
            raise PermissionDenied("You are not allowed to view this user.")

        return user

    @staticmethod
    def create_user(validated_data: dict, requesting_user) -> User:
        """Admins can create any role; Managers can only create Employees."""
        role = validated_data.get("role", UserRole.EMPLOYEE)

        if requesting_user.role == UserRole.MANAGER and role != UserRole.EMPLOYEE:
            raise PermissionDenied("Managers can only create Employee accounts.")

        if requesting_user.role == UserRole.EMPLOYEE:
            raise PermissionDenied("Employees cannot create users.")

        user = User.objects.create_user(**validated_data)
        logger.info(f"User {user.email} created by {requesting_user.email}")
        return user

    @staticmethod
    def update_user(user_id: int, validated_data: dict, requesting_user) -> User:
        user = UserService.get_user_by_id(user_id, requesting_user)

        # Employees can only update their own non-role fields
        if requesting_user.role == UserRole.EMPLOYEE:
            validated_data.pop("role", None)
            validated_data.pop("is_active", None)

        for attr, value in validated_data.items():
            setattr(user, attr, value)
        user.save()

        logger.info(f"User {user.email} updated by {requesting_user.email}")
        return user

    @staticmethod
    def change_password(user, old_password: str, new_password: str) -> None:
        if not user.check_password(old_password):
            raise PermissionDenied("Current password is incorrect.")
        user.set_password(new_password)
        user.save()
        logger.info(f"Password changed for {user.email}")

    @staticmethod
    def deactivate_user(user_id: int, requesting_user) -> User:
        if requesting_user.role != UserRole.ADMIN:
            raise PermissionDenied("Only admins can deactivate users.")
        user = UserService.get_user_by_id(user_id, requesting_user)
        user.is_active = False
        user.save()
        logger.info(f"User {user.email} deactivated by {requesting_user.email}")
        return user
