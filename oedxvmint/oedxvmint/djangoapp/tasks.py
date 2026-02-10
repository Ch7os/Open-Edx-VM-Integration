"""Celery tasks for vCenter operations."""

from celery import shared_task
from django.utils import timezone

from .models import LabInstance
from .services.lab_service import LabService


@shared_task(bind=True)
def provision_lab(self, instance_id, user_id=None):
    service = LabService()
    instance = LabInstance.objects.select_related("definition").get(id=instance_id)
    try:
        if instance.vms.exists():
            service.start_existing(instance)
        else:
            service.provision_topology(instance)
        service.log_action(instance, user_id, "start", result="success", details={"task_id": self.request.id})
    except Exception as exc:  # noqa: BLE001
        service.log_action(instance, user_id, "start", result="error", details={"task_id": self.request.id, "error": str(exc)})
        raise
    finally:
        service.unlock_instance(instance)


@shared_task(bind=True)
def stop_lab(self, instance_id, user_id=None):
    service = LabService()
    instance = LabInstance.objects.get(id=instance_id)
    try:
        service.stop_instance(instance)
        service.log_action(instance, user_id, "stop", result="success", details={"task_id": self.request.id})
    except Exception as exc:  # noqa: BLE001
        service.log_action(instance, user_id, "stop", result="error", details={"task_id": self.request.id, "error": str(exc)})
        raise
    finally:
        service.unlock_instance(instance)


@shared_task(bind=True)
def reset_lab(self, instance_id, user_id=None):
    service = LabService()
    instance = LabInstance.objects.select_related("definition").get(id=instance_id)
    try:
        service.reset_instance(instance)
        service.log_action(instance, user_id, "reset", result="success", details={"task_id": self.request.id})
    except Exception as exc:  # noqa: BLE001
        service.log_action(instance, user_id, "reset", result="error", details={"task_id": self.request.id, "error": str(exc)})
        raise
    finally:
        service.unlock_instance(instance)


@shared_task(bind=True)
def delete_lab(self, instance_id, user_id=None):
    service = LabService()
    instance = LabInstance.objects.select_related("definition").get(id=instance_id)
    try:
        # Log before deletion since instance will be removed
        service.log_action(instance, user_id, "delete", result="accepted", details={"task_id": self.request.id})
        service.delete_instance(instance)
        # Instance is now deleted, can't log success to it
    except Exception as exc:  # noqa: BLE001
        # On error, instance might still exist - try to log and unlock
        try:
            service.log_action(instance, user_id, "delete", result="error", details={"task_id": self.request.id, "error": str(exc)})
            service.unlock_instance(instance)
        except Exception:  # noqa: BLE001
            pass  # Instance might have been partially deleted
        raise


@shared_task
def cleanup_expired_labs():
    """Clean up expired labs in batches, respecting locks."""
    from django.db.models import Q
    
    service = LabService()
    now = timezone.now()
    batch_size = 50
    
    # Query expired labs that aren't locked, using iterator for efficiency
    queryset = (
        LabInstance.objects.filter(expires_at__lte=now)
        .filter(Q(locked_until__isnull=True) | Q(locked_until__lte=now))
        .select_related("definition")
        .iterator(chunk_size=batch_size)
    )
    
    count = 0
    for instance in queryset:
        # Check lock again in case another task grabbed it
        instance.refresh_from_db()
        if instance.locked_until and instance.locked_until > now:
            continue
        
        try:
            service.log_action(instance, None, "expire", result="accepted")
            service.delete_instance(instance)
            count += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to cleanup instance %s: %s", instance.id, exc)
            continue
    
    if count > 0:
        logger.info("Cleaned up %d expired lab instances", count)
