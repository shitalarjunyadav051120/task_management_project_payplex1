"""
Task Models - Core task management with full audit trail.
"""
from django.db import models
from django.conf import settings


class TaskPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class TaskStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"


class Task(models.Model):
    """
    Core task entity.
    Indexed on: assigned_to, status, priority, due_date for fast filtering.
    """
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    priority = models.CharField(
        max_length=10,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        db_index=True,
    )
    due_date = models.DateField(db_index=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tasks",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tasks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["due_date", "status"]),
        ]

    def __str__(self):
        return f"[{self.priority.upper()}] {self.title} — {self.status}"


class TaskComment(models.Model):
    """
    Comments on tasks. Employees can comment; all roles can read.
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments",
        db_index=True,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_comments",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "task_comments"
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.email} on Task #{self.task_id}"


class TaskStatusHistory(models.Model):
    """
    Immutable audit log: every status change on a task.
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="status_history",
        db_index=True,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="status_changes",
    )
    old_status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        null=True,
        blank=True,
    )
    new_status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
    )
    changed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "task_status_history"
        ordering = ["-changed_at"]

    def __str__(self):
        return (
            f"Task #{self.task_id}: {self.old_status} → {self.new_status} "
            f"by {getattr(self.changed_by, 'email', 'system')}"
        )
