"""
Authentication Views - Thin layer, delegates to service.
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
)
from .services import UserService
from .permissions import IsAdmin, IsAdminOrManager
from apps.authentication.utils import api_response


@extend_schema(tags=["Authentication"])
class LoginView(TokenObtainPairView):
    """
    POST /api/v1/login
    Returns JWT access + refresh tokens with user info.
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return api_response(
            data=response.data,
            message="Login successful.",
            status_code=status.HTTP_200_OK,
        )


@extend_schema(tags=["Authentication"])
class LogoutView(APIView):
    """
    POST /api/v1/logout
    Blacklists the refresh token.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return api_response(
                errors={"refresh": "Refresh token is required."},
                message="Logout failed.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return api_response(message="Logout successful.", status_code=status.HTTP_200_OK)
        except Exception:
            return api_response(
                errors={"refresh": "Invalid or expired token."},
                message="Logout failed.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(tags=["Users"])
class UserViewSet(ViewSet):
    """
    /api/v1/users
    Full CRUD on users with role-based access.
    """

    def get_permissions(self):
        if self.action == "create":
            return [IsAdminOrManager()]
        if self.action == "destroy":
            return [IsAdmin()]
        return [IsAuthenticated()]

    def list(self, request):
        """GET /api/v1/users — list users based on role."""
        users = UserService.get_all_users(request.user)
        serializer = UserSerializer(users, many=True)
        return api_response(data=serializer.data, status_code=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        """GET /api/v1/users/{id}"""
        user = UserService.get_user_by_id(pk, request.user)
        serializer = UserSerializer(user)
        return api_response(data=serializer.data, status_code=status.HTTP_200_OK)

    def create(self, request):
        """POST /api/v1/users — Admin/Manager only."""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = UserService.create_user(serializer.validated_data, request.user)
        return api_response(
            data=UserSerializer(user).data,
            message="User created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, pk=None):
        """PUT /api/v1/users/{id}"""
        serializer = UserUpdateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = UserService.update_user(pk, serializer.validated_data, request.user)
        return api_response(
            data=UserSerializer(user).data,
            message="User updated successfully.",
            status_code=status.HTTP_200_OK,
        )

    def partial_update(self, request, pk=None):
        """PATCH /api/v1/users/{id}"""
        serializer = UserUpdateSerializer(
            data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = UserService.update_user(pk, serializer.validated_data, request.user)
        return api_response(
            data=UserSerializer(user).data,
            message="User updated successfully.",
            status_code=status.HTTP_200_OK,
        )

    def destroy(self, request, pk=None):
        """DELETE /api/v1/users/{id} — Admin only (deactivates)."""
        UserService.deactivate_user(pk, request.user)
        return api_response(
            message="User deactivated successfully.",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """GET /api/v1/users/me"""
        serializer = UserSerializer(request.user)
        return api_response(data=serializer.data, status_code=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="change-password")
    def change_password(self, request):
        """POST /api/v1/users/change-password"""
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        UserService.change_password(
            request.user,
            serializer.validated_data["old_password"],
            serializer.validated_data["new_password"],
        )
        return api_response(
            message="Password changed successfully.",
            status_code=status.HTTP_200_OK,
        )
