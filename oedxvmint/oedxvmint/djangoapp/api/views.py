"""REST API for HTB lab controls."""

from __future__ import annotations

import json
import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from ..models import LabDefinition, LabInstance
from ..services.auth import is_staff
from ..services.lab_service import LabService
from ..tasks import delete_lab, provision_lab, reset_lab, stop_lab

logger = logging.getLogger(__name__)


def _xblock_config_from_request(request):
    body = {}
    if request.body:
        try:
            body = json.loads(request.body.decode("utf-8"))
        except Exception:  # pylint: disable=broad-except
            body = {}
    return body.get("xblock_config", {})


@method_decorator([login_required, csrf_exempt], name="dispatch")
class LearnerLabView(View):
    service = LabService()

    def _resolve(self, request, course_id, block_id):
        definition = LabDefinition.objects.filter(course_id=course_id, block_id=block_id).first()
        if not definition and request.method == "POST":
            cfg = _xblock_config_from_request(request)
            if not cfg:
                return None, None, HttpResponseBadRequest("Missing lab definition")
            definition = self.service.ensure_definition(course_id=course_id, block_id=block_id, xblock_config=cfg)
        if not definition:
            return None, None, JsonResponse({"state": "missing", "message": "Lab not configured", "vms": []})

        team_id = request.GET.get("team_id")
        alloc = self.service.allocation_for(definition, request.user.id, team_id)
        instance = LabInstance.objects.filter(allocation_key=alloc).first()
        if instance and instance.user_id and instance.user_id != request.user.id and not is_staff(request.user):
            return definition, None, JsonResponse({"message": "Forbidden"}, status=403)
        return definition, instance, None

    def get(self, request, course_id, block_id, action):
        if action != "status":
            return JsonResponse({"message": "Method not allowed"}, status=405)
        _, instance, err = self._resolve(request, course_id, block_id)
        if err:
            return err
        if not instance:
            return JsonResponse({"state": "not_started", "message": "No lab instance", "vms": []})
        return JsonResponse(self.service.serialize_instance(instance))

    def post(self, request, course_id, block_id, action):
        definition, instance, err = self._resolve(request, course_id, block_id)
        if err:
            return err

        team_id = request.GET.get("team_id")
        if action == "start":
            if not instance:
                instance, created = self.service.create_instance(definition, request.user.id, team_id)
                if created:
                    op = provision_lab.delay(instance.id, request.user.id)
                    self.service.log_action(instance, request.user.id, "start", result="accepted", details={"task_id": op.id})
                    payload = self.service.serialize_instance(instance)
                    payload["operation_id"] = op.id
                    payload["message"] = "Provisioning started"
                    return JsonResponse(payload)
            self.service.check_rate_limit(instance, definition.cooldown_seconds)
            op = provision_lab.delay(instance.id, request.user.id)
            payload = self.service.serialize_instance(instance)
            payload["operation_id"] = op.id
            return JsonResponse(payload)

        if not instance:
            return JsonResponse({"message": "No instance"}, status=404)

        self.service.check_rate_limit(instance, definition.cooldown_seconds)

        if action == "stop":
            op = stop_lab.delay(instance.id, request.user.id)
        elif action == "restart":
            op = provision_lab.delay(instance.id, request.user.id)
        elif action == "reset":
            op = reset_lab.delay(instance.id, request.user.id)
        elif action == "extend":
            instance.expires_at = instance.expires_at + (instance.expires_at - instance.created_at) / 4
            instance.save(update_fields=["expires_at", "updated_at"])
            op = None
        else:
            return JsonResponse({"message": "Unsupported action"}, status=400)

        payload = self.service.serialize_instance(instance)
        payload["operation_id"] = op.id if op else None
        return JsonResponse(payload)


@method_decorator([login_required, csrf_exempt], name="dispatch")
class AdminInstanceView(View):
    service = LabService()

    def dispatch(self, request, *args, **kwargs):
        if not is_staff(request.user):
            return JsonResponse({"message": "Forbidden"}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        queryset = LabInstance.objects.select_related("definition").all()
        course_id = request.GET.get("course_id")
        block_id = request.GET.get("block_id")
        user_id = request.GET.get("user")
        if course_id:
            queryset = queryset.filter(definition__course_id=course_id)
        if block_id:
            queryset = queryset.filter(definition__block_id=block_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        data = [
            {
                "id": i.id,
                "allocation_key": i.allocation_key,
                "state": i.state,
                "user_id": i.user_id,
                "team_id": i.team_id,
            }
            for i in queryset[:200]
        ]
        return JsonResponse({"instances": data})

    def post(self, request, instance_id):
        instance = LabInstance.objects.get(id=instance_id)
        action = json.loads(request.body.decode("utf-8")).get("action")
        if action == "stop":
            op = stop_lab.delay(instance.id, request.user.id)
        elif action == "reset":
            op = reset_lab.delay(instance.id, request.user.id)
        elif action == "delete":
            op = delete_lab.delay(instance.id, request.user.id)
        else:
            return JsonResponse({"message": "Unsupported action"}, status=400)
        return JsonResponse({"operation_id": op.id, "state": instance.state})
