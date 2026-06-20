"""
Task Service Layer - All business logic for tasks, comments, and history.
"""
import logging
from django.db import transaction
from django.db.models import QuerySet, Q
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError

from .models import Task, TaskComment, TaskStatusHistory, TaskStatus
from apps.authentication.models import UserRole
from apps.notification.tasks import send_task_assigned_email, send_task_status_updated_email

logger = logging.getLogger(__name__)


class TaskService:
    """All task business logic — no HTTP concerns."""

    @staticmethod
    def get_task_queryset(requesting_user) -> QuerySet:
        """
        Role-based task filtering:
        - Admin: all tasks
        - Manager: all tasks (they oversee)
        - Employee: only their assigned tasks
        """
        qs = Task.objects.select_related(
            "assigned_to", "created_by"
        ).prefetch_related("comments__author", "status_history__changed_by")

        if requesting_user.role == UserRole.EMPLOYEE:
            qs = qs.filter(assigned_to=requesting_user)

        return qs

    @staticmethod
    def apply_filters(queryset: QuerySet, filters: dict) -> QuerySet:
        """Apply query filters from request params."""
        status = filters.get("status")
        priority = filters.get("priority")
        assigned_to = filters.get("assigned_to")
        search = filters.get("search")
        due_date_from = filters.get("due_date_from")
        due_date_to = filters.get("due_date_to")

        if status:
            queryset = queryset.filter(status=status)
        if priority:
            queryset = queryset.filter(priority=priority)
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        if due_date_from:
            queryset = queryset.filter(due_date__gte=due_date_from)
        if due_date_to:
            queryset = queryset.filter(due_date__lte=due_date_to)

        return queryset

    @staticmethod
    def get_task_by_id(task_id: int, requesting_user) -> Task:
        try:
            task = Task.objects.select_related(
                "assigned_to", "created_by"
            ).prefetch_related(
                "comments__author", "status_history__changed_by"
            ).get(id=task_id)
        except Task.DoesNotExist:
            raise NotFound(f"Task with id={task_id} not found.")

        # Employees can only see their own tasks
        if (
            requesting_user.role == UserRole.EMPLOYEE
            and task.assigned_to != requesting_user
        ):
            raise PermissionDenied("You do not have access to this task.")

        return task

    @staticmethod
    @transaction.atomic
    def create_task(validated_data: dict, requesting_user) -> Task:
        """Admin/Manager only. Records status history on creation."""
        if requesting_user.role == UserRole.EMPLOYEE:
            raise PermissionDenied("Employees cannot create tasks.")

        task = Task.objects.create(created_by=requesting_user, **validated_data)

        # Record initial status in history
        TaskStatusHistory.objects.create(
            task=task,
            changed_by=requesting_user,
            old_status=None,
            new_status=task.status,
            notes="Task created.",
        )

        logger.info(f"Task #{task.id} '{task.title}' created by {requesting_user.email}")

        # Fire notification if someone is assigned
        if task.assigned_to:
            send_task_assigned_email.delay(task.id)

        return task

    @staticmethod
    @transaction.atomic
    def update_task(task_id: int, validated_data: dict, requesting_user) -> Task:
        """Admin/Manager can update any field. Tracks status changes."""
        if requesting_user.role == UserRole.EMPLOYEE:
            raise PermissionDenied("Employees cannot update tasks.")

        task = TaskService.get_task_by_id(task_id, requesting_user)
        old_status = task.status
        old_assigned_to = task.assigned_to

        for attr, value in validated_data.items():
            setattr(task, attr, value)
        task.save()

        # Track status change
        new_status = task.status
        if old_status != new_status:
            TaskStatusHistory.objects.create(
                task=task,
                changed_by=requesting_user,
                old_status=old_status,
                new_status=new_status,
                notes=f"Status changed via task update.",
            )
            send_task_status_updated_email.delay(task.id, old_status, new_status)
            logger.info(
                f"Task #{task.id} status: {old_status} → {new_status} "
                f"by {requesting_user.email}"
            )

        # Notify new assignee
        if task.assigned_to and task.assigned_to != old_assigned_to:
            send_task_assigned_email.delay(task.id)

        return task

    @staticmethod
    @transaction.atomic
    def change_task_status(
        task_id: int, new_status: str, notes: str, requesting_user
    ) -> Task:
        """Dedicated status change — all roles allowed on their tasks."""
        task = TaskService.get_task_by_id(task_id, requesting_user)

        # Employee: only on their assigned task, only forward transitions
        if requesting_user.role == UserRole.EMPLOYEE:
            allowed = {
                TaskStatus.PENDING: [TaskStatus.IN_PROGRESS],
                TaskStatus.IN_PROGRESS: [TaskStatus.COMPLETED],
            }
            if new_status not in allowed.get(task.status, []):
                raise ValidationError(
                    f"Employees can only move tasks forward. "
                    f"Current: '{task.status}', tried: '{new_status}'."
                )

        old_status = task.status
        if old_status == new_status:
            raise ValidationError("Task is already in this status.")

        task.status = new_status
        task.save(update_fields=["status", "updated_at"])

        TaskStatusHistory.objects.create(
            task=task,
            changed_by=requesting_user,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
        )

        send_task_status_updated_email.delay(task.id, old_status, new_status)
        logger.info(
            f"Task #{task.id} status: {old_status} → {new_status} "
            f"by {requesting_user.email}"
        )

        return task

    @staticmethod
    def delete_task(task_id: int, requesting_user) -> None:
        """Admin only can delete tasks."""
        if requesting_user.role != UserRole.ADMIN:
            raise PermissionDenied("Only admins can delete tasks.")

        task = TaskService.get_task_by_id(task_id, requesting_user)
        task.delete()
        logger.info(f"Task #{task_id} deleted by {requesting_user.email}")

    @staticmethod
    def get_task_summary(requesting_user) -> dict:
        """Summary/reporting: count by status and priority."""
        qs = TaskService.get_task_queryset(requesting_user)
        summary = {
            "total": qs.count(),
            "by_status": {
                status: qs.filter(status=status).count()
                for status, _ in Task._meta.get_field("status").choices
            },
            "by_priority": {
                priority: qs.filter(priority=priority).count()
                for priority, _ in Task._meta.get_field("priority").choices
            },
        }
        return summary


class CommentService:
    """Business logic for task comments."""

    @staticmethod
    def add_comment(task_id: int, content: str, requesting_user) -> TaskComment:
        """Any authenticated user can comment on tasks they can see."""
        # Fetch via TaskService to enforce visibility
        task = TaskService.get_task_by_id(task_id, requesting_user)

        comment = TaskComment.objects.create(
            task=task,
            author=requesting_user,
            content=content,
        )
        logger.info(f"Comment added to Task #{task_id} by {requesting_user.email}")
        return comment

    @staticmethod
    def delete_comment(comment_id: int, requesting_user) -> None:
        try:
            comment = TaskComment.objects.get(id=comment_id)
        except TaskComment.DoesNotExist:
            raise NotFound(f"Comment #{comment_id} not found.")

        if comment.author != requesting_user and requesting_user.role not in [
            UserRole.ADMIN, UserRole.MANAGER
        ]:
            raise PermissionDenied("You can only delete your own comments.")

        comment.delete()
