"""
Task Views - Thin layer that delegates to TaskService.
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ViewSet
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .serializers import (
    TaskSerializer,
    TaskListSerializer,
    TaskCreateSerializer,
    TaskUpdateSerializer,
    TaskStatusUpdateSerializer,
    TaskCommentSerializer,
    TaskCommentCreateSerializer,
    TaskStatusHistorySerializer,
)
from .services import TaskService, CommentService
from apps.authentication.utils import api_response
from apps.authentication.permissions import IsAdminOrManager


@extend_schema(tags=["Tasks"])
class TaskViewSet(ViewSet):
    """
    /api/v1/tasks — Full CRUD + status change + summary report.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, description="Filter by status"),
            OpenApiParameter("priority", str, description="Filter by priority"),
            OpenApiParameter("assigned_to", int, description="Filter by user ID"),
            OpenApiParameter("search", str, description="Search title/description"),
            OpenApiParameter("due_date_from", str, description="YYYY-MM-DD"),
            OpenApiParameter("due_date_to", str, description="YYYY-MM-DD"),
        ]
    )
    def list(self, request):
        """GET /api/v1/tasks — returns role-filtered task list."""
        queryset = TaskService.get_task_queryset(request.user)
        queryset = TaskService.apply_filters(queryset, request.query_params)
        serializer = TaskListSerializer(queryset, many=True)
        return api_response(data=serializer.data, status_code=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        """GET /api/v1/tasks/{id} — full task detail with comments & history."""
        task = TaskService.get_task_by_id(pk, request.user)
        serializer = TaskSerializer(task)
        return api_response(data=serializer.data, status_code=status.HTTP_200_OK)

    def create(self, request):
        """POST /api/v1/tasks — Admin/Manager only."""
        self.check_permissions_for_write(request)
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TaskService.create_task(serializer.validated_data, request.user)
        return api_response(
            data=TaskSerializer(task).data,
            message="Task created successfully.",
            status_code=status.HTTP_201_CREATED,
        )

    def update(self, request, pk=None):
        """PUT /api/v1/tasks/{id} — Admin/Manager only."""
        self.check_permissions_for_write(request)
        serializer = TaskUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TaskService.update_task(pk, serializer.validated_data, request.user)
        return api_response(
            data=TaskSerializer(task).data,
            message="Task updated successfully.",
            status_code=status.HTTP_200_OK,
        )

    def partial_update(self, request, pk=None):
        """PATCH /api/v1/tasks/{id} — Admin/Manager only."""
        self.check_permissions_for_write(request)
        serializer = TaskUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = TaskService.update_task(pk, serializer.validated_data, request.user)
        return api_response(
            data=TaskSerializer(task).data,
            message="Task updated successfully.",
            status_code=status.HTTP_200_OK,
        )

    def destroy(self, request, pk=None):
        """DELETE /api/v1/tasks/{id} — Admin only."""
        TaskService.delete_task(pk, request.user)
        return api_response(
            message="Task deleted successfully.",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["patch"], url_path="status")
    def change_status(self, request, pk=None):
        """
        PATCH /api/v1/tasks/{id}/status
        Employees can move status forward; Admin/Manager can set any.
        """
        serializer = TaskStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = TaskService.change_task_status(
            pk,
            serializer.validated_data["status"],
            serializer.validated_data.get("notes", ""),
            request.user,
        )
        return api_response(
            data=TaskSerializer(task).data,
            message="Task status updated.",
            status_code=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        """GET /api/v1/tasks/{id}/history — full status change audit."""
        task = TaskService.get_task_by_id(pk, request.user)
        serializer = TaskStatusHistorySerializer(
            task.status_history.all(), many=True
        )
        return api_response(data=serializer.data, status_code=status.HTTP_200_OK)

    @action(detail=True, methods=["post", "get"], url_path="comments")
    def comments(self, request, pk=None):
        """
        GET  /api/v1/tasks/{id}/comments — list comments
        POST /api/v1/tasks/{id}/comments — add comment (any role)
        """
        if request.method == "GET":
            task = TaskService.get_task_by_id(pk, request.user)
            serializer = TaskCommentSerializer(task.comments.all(), many=True)
            return api_response(data=serializer.data, status_code=status.HTTP_200_OK)

        serializer = TaskCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = CommentService.add_comment(
            pk, serializer.validated_data["content"], request.user
        )
        return api_response(
            data=TaskCommentSerializer(comment).data,
            message="Comment added.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["delete"], url_path=r"comments/(?P<comment_id>[^/.]+)")
    def delete_comment(self, request, pk=None, comment_id=None):
        """DELETE /api/v1/tasks/{id}/comments/{comment_id}"""
        CommentService.delete_comment(comment_id, request.user)
        return api_response(
            message="Comment deleted.", status_code=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """
        GET /api/v1/tasks/summary
        Report: task counts by status and priority.
        """
        data = TaskService.get_task_summary(request.user)
        return api_response(data=data, status_code=status.HTTP_200_OK)

    def check_permissions_for_write(self, request):
        """Helper: raise if caller is not Admin/Manager."""
        from apps.authentication.permissions import IsAdminOrManager
        perm = IsAdminOrManager()
        if not perm.has_permission(request, self):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(perm.message)
