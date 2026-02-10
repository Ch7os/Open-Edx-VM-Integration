from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LabDefinition(TimeStampedModel):
    MODE_CHOICES = (("unit", "Per Unit"), ("course", "Per Course"), ("team", "Team"))

    course_id = models.CharField(max_length=255, db_index=True)
    usage_key = models.CharField(max_length=255, unique=True)
    block_id = models.CharField(max_length=255, db_index=True)
    display_name = models.CharField(max_length=255)
    mode = models.CharField(max_length=16, choices=MODE_CHOICES, default="unit")
    ttl_minutes = models.PositiveIntegerField(default=120)
    max_instances_per_scope = models.PositiveIntegerField(default=1)
    cooldown_seconds = models.PositiveIntegerField(default=5)
    network_strategy = models.CharField(max_length=32, default="pool")
    network_config = models.JSONField(default=dict, blank=True)
    vm_specs = models.JSONField(default=list)
    author_hint_text = models.TextField(blank=True, default="")


class LabInstance(TimeStampedModel):
    STATE_CHOICES = (
        ("provisioning", "Provisioning"),
        ("running", "Running"),
        ("stopped", "Stopped"),
        ("error", "Error"),
        ("expired", "Expired"),
        ("deleting", "Deleting"),
    )

    definition = models.ForeignKey(LabDefinition, on_delete=models.CASCADE, related_name="instances")
    allocation_key = models.CharField(max_length=512, unique=True)
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    team_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    state = models.CharField(max_length=32, choices=STATE_CHOICES, default="provisioning")
    expires_at = models.DateTimeField(db_index=True)
    last_action_at = models.DateTimeField(default=timezone.now)
    locked_until = models.DateTimeField(null=True, blank=True)
    network_allocation = models.JSONField(default=dict, blank=True)


class VMInstance(TimeStampedModel):
    ROLE_CHOICES = (("workstation", "Workstation"), ("target", "Target"))

    lab_instance = models.ForeignKey(LabInstance, on_delete=models.CASCADE, related_name="vms")
    role = models.CharField(max_length=32, choices=ROLE_CHOICES)
    vm_moid = models.CharField(max_length=128, blank=True, default="")
    vm_name = models.CharField(max_length=255)
    state = models.CharField(max_length=64, default="provisioning")
    ip_addresses = models.JSONField(default=list, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    creds_visible = models.BooleanField(default=False)
    console_url = models.URLField(blank=True, default="")
    vcenter_task_ids = models.JSONField(default=list, blank=True)
    last_error = models.TextField(blank=True, default="")


class LabActionLog(models.Model):
    RESULT_CHOICES = (("success", "Success"), ("error", "Error"), ("accepted", "Accepted"))

    lab_instance = models.ForeignKey(LabInstance, on_delete=models.CASCADE, related_name="actions")
    user_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=64)
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.CharField(max_length=16, choices=RESULT_CHOICES, default="accepted")
    details = models.JSONField(default=dict, blank=True)
