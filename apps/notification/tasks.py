"""
Notification Tasks - Celery background tasks for email notifications.
"""
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_task(task_id: int):
    """Lazy import to avoid circular imports."""
    from apps.tasks.models import Task
    try:
        return Task.objects.select_related("assigned_to", "created_by").get(id=task_id)
    except Task.DoesNotExist:
        logger.warning(f"Notification skipped — Task #{task_id} not found.")
        return None


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.send_task_assigned_email",
)
def send_task_assigned_email(self, task_id: int):
    """
    Send email to the user when a task is assigned to them.
    Retries up to 3 times on failure (network issues, etc.).
    """
    task = _get_task(task_id)
    if not task or not task.assigned_to:
        return

    user = task.assigned_to
    subject = f"[Task Management] New Task Assigned: {task.title}"
    message = (
        f"Hi {user.get_full_name()},\n\n"
        f"You have been assigned a new task:\n\n"
        f"  Title    : {task.title}\n"
        f"  Priority : {task.get_priority_display()}\n"
        f"  Status   : {task.get_status_display()}\n"
        f"  Due Date : {task.due_date}\n\n"
        f"Description:\n{task.description or 'N/A'}\n\n"
        f"Please log in to the Task Management System to view details.\n\n"
        f"Regards,\nTask Management System"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f"Assignment email sent to {user.email} for Task #{task_id}")
    except Exception as exc:
        logger.error(f"Failed to send assignment email for Task #{task_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.send_task_status_updated_email",
)
def send_task_status_updated_email(self, task_id: int, old_status: str, new_status: str):
    """
    Send email when task status changes.
    Notifies the assigned user and the task creator.
    """
    task = _get_task(task_id)
    if not task:
        return

    recipients = []
    if task.assigned_to:
        recipients.append(task.assigned_to.email)
    if task.created_by and task.created_by != task.assigned_to:
        recipients.append(task.created_by.email)

    if not recipients:
        return

    subject = f"[Task Management] Task Status Updated: {task.title}"
    message = (
        f"Hi,\n\n"
        f"The status of a task has been updated:\n\n"
        f"  Task     : {task.title}\n"
        f"  Priority : {task.get_priority_display()}\n"
        f"  Old Status: {old_status.replace('_', ' ').title()}\n"
        f"  New Status: {new_status.replace('_', ' ').title()}\n"
        f"  Due Date : {task.due_date}\n\n"
        f"Please log in to the Task Management System for more details.\n\n"
        f"Regards,\nTask Management System"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=list(set(recipients)),
            fail_silently=False,
        )
        logger.info(
            f"Status update email sent to {recipients} for Task #{task_id}: "
            f"{old_status} → {new_status}"
        )
    except Exception as exc:
        logger.error(f"Failed to send status update email for Task #{task_id}: {exc}")
        raise self.retry(exc=exc)
