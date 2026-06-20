"""
Task Signals - Additional hooks beyond the service layer.
"""
import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Task

logger = logging.getLogger(__name__)

# Store pre-save state for comparison
_task_pre_save_status = {}


@receiver(pre_save, sender=Task)
def capture_pre_save_status(sender, instance, **kwargs):
    """Capture the old status before save for logging."""
    if instance.pk:
        try:
            old = Task.objects.get(pk=instance.pk)
            _task_pre_save_status[instance.pk] = old.status
        except Task.DoesNotExist:
            pass


@receiver(post_save, sender=Task)
def log_task_change(sender, instance, created, **kwargs):
    """Log all task saves for observability."""
    if created:
        logger.info(
            f"TASK_CREATED | id={instance.id} title='{instance.title}' "
            f"status={instance.status} priority={instance.priority}"
        )
    else:
        old_status = _task_pre_save_status.pop(instance.pk, None)
        if old_status and old_status != instance.status:
            logger.info(
                f"TASK_STATUS_CHANGED | id={instance.id} "
                f"'{old_status}' → '{instance.status}'"
            )
        else:
            logger.debug(f"TASK_UPDATED | id={instance.id}")
