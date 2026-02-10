import os

INSTALLED_APPS.append("oedxvmint.djangoapp")

HTBLAB = {
    "VCENTER_URL": os.getenv("VCENTER_URL", ""),
    "VCENTER_USERNAME": os.getenv("VCENTER_USERNAME", ""),
    "VCENTER_PASSWORD": os.getenv("VCENTER_PASSWORD", ""),
    "VCENTER_INSECURE": os.getenv("VCENTER_INSECURE", "true").lower() == "true",
    "VCENTER_STUB": os.getenv("VCENTER_STUB", "false").lower() == "true",
    "VCENTER_DATACENTER": os.getenv("VCENTER_DATACENTER", ""),
    "VCENTER_CLUSTER": os.getenv("VCENTER_CLUSTER", ""),
    "VCENTER_RESOURCE_POOL": os.getenv("VCENTER_RESOURCE_POOL", ""),
    "VCENTER_FOLDER": os.getenv("VCENTER_FOLDER", ""),
    "VCENTER_DATASTORE": os.getenv("VCENTER_DATASTORE", ""),
    "NETWORK_STRATEGIES_ALLOWED": os.getenv("NETWORK_STRATEGIES_ALLOWED", "pool,ephemeral,shared").split(","),
}

URLS = globals().setdefault("lms_url_overrides", {})
URLS["^api/htblab/"] = "oedxvmint.djangoapp.urls"

CELERY_BEAT_SCHEDULE = globals().get("CELERY_BEAT_SCHEDULE", {})
CELERY_BEAT_SCHEDULE.update(
    {
        "htblab-expiry-cleanup": {
            "task": "oedxvmint.djangoapp.tasks.cleanup_expired_labs",
            "schedule": 60.0,
        }
    }
)
