from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="LabDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("course_id", models.CharField(db_index=True, max_length=255)),
                ("usage_key", models.CharField(max_length=255, unique=True)),
                ("block_id", models.CharField(db_index=True, max_length=255)),
                ("display_name", models.CharField(max_length=255)),
                ("mode", models.CharField(choices=[("unit", "Per Unit"), ("course", "Per Course"), ("team", "Team")], default="unit", max_length=16)),
                ("ttl_minutes", models.PositiveIntegerField(default=120)),
                ("max_instances_per_scope", models.PositiveIntegerField(default=1)),
                ("cooldown_seconds", models.PositiveIntegerField(default=5)),
                ("network_strategy", models.CharField(default="pool", max_length=32)),
                ("network_config", models.JSONField(blank=True, default=dict)),
                ("vm_specs", models.JSONField(default=list)),
                ("author_hint_text", models.TextField(blank=True, default="")),
            ],
        ),
        migrations.CreateModel(
            name="LabInstance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("allocation_key", models.CharField(max_length=512, unique=True)),
                ("user_id", models.IntegerField(blank=True, db_index=True, null=True)),
                ("team_id", models.CharField(blank=True, db_index=True, max_length=255, null=True)),
                ("state", models.CharField(choices=[("provisioning", "Provisioning"), ("running", "Running"), ("stopped", "Stopped"), ("error", "Error"), ("expired", "Expired"), ("deleting", "Deleting")], default="provisioning", max_length=32)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("last_action_at", models.DateTimeField()),
                ("locked_until", models.DateTimeField(blank=True, null=True)),
                ("network_allocation", models.JSONField(blank=True, default=dict)),
                ("definition", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="instances", to="djangoapp.labdefinition")),
            ],
        ),
        migrations.CreateModel(
            name="LabActionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_id", models.IntegerField(blank=True, null=True)),
                ("action", models.CharField(max_length=64)),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("result", models.CharField(choices=[("success", "Success"), ("error", "Error"), ("accepted", "Accepted")], default="accepted", max_length=16)),
                ("details", models.JSONField(blank=True, default=dict)),
                ("lab_instance", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="actions", to="djangoapp.labinstance")),
            ],
        ),
        migrations.CreateModel(
            name="VMInstance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("role", models.CharField(choices=[("workstation", "Workstation"), ("target", "Target")], max_length=32)),
                ("vm_moid", models.CharField(blank=True, default="", max_length=128)),
                ("vm_name", models.CharField(max_length=255)),
                ("state", models.CharField(default="provisioning", max_length=64)),
                ("ip_addresses", models.JSONField(blank=True, default=list)),
                ("username", models.CharField(blank=True, max_length=255, null=True)),
                ("password", models.CharField(blank=True, max_length=255, null=True)),
                ("creds_visible", models.BooleanField(default=False)),
                ("console_url", models.URLField(blank=True, default="")),
                ("vcenter_task_ids", models.JSONField(blank=True, default=list)),
                ("last_error", models.TextField(blank=True, default="")),
                ("lab_instance", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="vms", to="djangoapp.labinstance")),
            ],
        ),
    ]
