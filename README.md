# Open edX HTB Lab VM Integration (Tutor Plugin)

Production-ready Open edX plugin for Tutor deployments that adds **HTB-like lab VM controls** to course units. It combines an XBlock UI, a Django plugin API, and Celery workers for long-running VMware vCenter operations.

## Features

- `HTBLabXBlock` with learner Lab Panel (Start/Stop/Restart/Reset/Extend/Refresh).
- Django API under `/api/htblab/` with strict learner/staff authorization.
- Celery tasks for clone/power/reset/delete and periodic TTL cleanup.
- VMware **vCenter REST-first** provisioning (`VCENTER_STUB=true` for dev simulation).
- Multi-VM lab topology per unit with role-aware credential visibility:
  - `workstation`: credentials optionally shown.
  - `target`: credentials never shown.
- Lab modes: `unit`, `course`, `team`.
- Network isolation strategies:
  - Pool of isolated port groups.
  - Ephemeral distributed port group allocation metadata.
  - Shared network (non-default).
- Audit logging for every control action.

## Repository layout

```text
pyproject.toml
README.md
oedxvmint/
  oedxvmint/
    xblock.py
    djangoapp/
      models.py
      tasks.py
      urls.py
      api/views.py
      services/
      migrations/0001_initial.py
      settings/common.py
```

## Tutor installation

### 1) Install package in openedx image

Option A (recommended): add to Tutor `OPENEDX_EXTRA_PIP_REQUIREMENTS`:

```yaml
OPENEDX_EXTRA_PIP_REQUIREMENTS:
  - /openedx/requirements/oedxvmint-htblab
```

Option B: bake into a custom openedx image and run `pip install oedxvmint-htblab`.

### 2) Enable plugin and redeploy

```bash
tutor config save
tutor images build openedx
tutor local launch
```

### 3) Ensure Celery worker + beat are running

Tutor standard deployment already runs both; this plugin registers periodic cleanup in `CELERY_BEAT_SCHEDULE`.

## Configuration

Set environment variables in Tutor (`tutor config save --set ...`):

- `VCENTER_URL`
- `VCENTER_USERNAME`
- `VCENTER_PASSWORD`
- `VCENTER_INSECURE=true|false`
- `VCENTER_DATACENTER`
- `VCENTER_CLUSTER`
- `VCENTER_RESOURCE_POOL`
- `VCENTER_FOLDER`
- `VCENTER_DATASTORE`
- `NETWORK_STRATEGIES_ALLOWED=pool,ephemeral,shared`
- `VCENTER_STUB=true|false` (local testing)

### Security notes

- vCenter secrets are read from env vars only (never exposed to browser).
- Learner controls are allocation-key scoped.
- Staff can manage all instances.
- Target VM credentials are always hidden in learner responses.
- Action logs are persisted in `LabActionLog`.

## Author usage

In Studio, add `oedxvmint` XBlock to a unit and configure:

- Mode: `unit`, `course`, `team`
- TTL, cooldown, max instances
- Network strategy
- `vm_specs_json` (list of VMs with `role`, `template_ref`, optional creds and reset policy)
- Author hint text

Example `vm_specs_json`:

```json
[
  {
    "name": "ws-learner",
    "role": "workstation",
    "template_ref": "vm-template-workstation",
    "show_credentials": true,
    "username": "student",
    "password": "ChangeMe!",
    "snapshot_ref": "clean"
  },
  {
    "name": "target-web",
    "role": "target",
    "template_ref": "vm-template-target-web",
    "show_credentials": false
  }
]
```

## API

Learner endpoints:

- `GET  /api/htblab/{course_id}/{block_id}/status`
- `POST /api/htblab/{course_id}/{block_id}/start`
- `POST /api/htblab/{course_id}/{block_id}/stop`
- `POST /api/htblab/{course_id}/{block_id}/restart`
- `POST /api/htblab/{course_id}/{block_id}/reset`
- `POST /api/htblab/{course_id}/{block_id}/extend`

Staff endpoints:

- `GET  /api/htblab/admin/instances?course_id=...&block_id=...&user=...`
- `POST /api/htblab/admin/{instance_id}/action` body `{"action":"stop|reset|delete"}`

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
pytest oedxvmint/tests
```

Use `VCENTER_STUB=true` for local simulation without vCenter.
