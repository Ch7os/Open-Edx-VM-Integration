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


class ActionConflictError(Exception):
    """Raised when action cannot be enqueued due to rate/lock rules."""


def _request_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def _xblock_config_from_request(request):
    body = _request_body(request)
    return body.get("xblock_config", {})


def _team_id_from_request(request, fallback=None):
    body = _request_body(request)
    return request.GET.get("team_id") or body.get("team_id") or fallback


@method_decorator([login_required, csrf_exempt], name="dispatch")
class LearnerLabView(View):
    service = LabService()

    def _resolve(self, request, course_id, block_id):
        definition = LabDefinition.objects.filter(course_id=course_id, block_id=block_id).first()
        if not definition:
            # Only allow staff to create/update LabDefinition from request-supplied config
            if request.method == "POST" and is_staff(request.user):
                cfg = _xblock_config_from_request(request)
                if not cfg:
                    return None, None, HttpResponseBadRequest("Missing lab definition")
                definition = self.service.ensure_definition(course_id=course_id, block_id=block_id, xblock_config=cfg)
            if not definition:
                return None, None, JsonResponse({"state": "missing", "message": "Lab not configured", "vms": []})

        team_id = _team_id_from_request(request)
        try:
            alloc = self.service.allocation_for(definition, request.user.id, team_id)
        except ValueError as exc:
            logger.warning("Failed to build allocation key: %s", exc)
            message = str(exc) or "Invalid or missing team_id for team-based lab"
            return definition, None, HttpResponseBadRequest(message)
        instance = LabInstance.objects.filter(allocation_key=alloc).first()
        if instance and instance.user_id and instance.user_id != request.user.id and not is_staff(request.user):
            return definition, None, JsonResponse({"message": "Forbidden"}, status=403)
        return definition, instance, None

    def _enqueue(self, *, instance, definition, user_id, action, task_func):
        try:
            self.service.check_rate_limit(instance, definition.cooldown_seconds)
            self.service.lock_instance(instance)
        except RuntimeError as exc:
            raise ActionConflictError(str(exc)) from exc

        op = task_func.delay(instance.id, user_id)
        self.service.log_action(instance, user_id, action, result="accepted", details={"task_id": op.id})
        payload = self.service.serialize_instance(instance)
        payload["operation_id"] = op.id
        payload["message"] = f"{action} accepted"
        return payload

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

        team_id = _team_id_from_request(request)
        try:
            if action == "start":
                if not instance:
                    instance, _ = self.service.create_instance(definition, request.user.id, team_id)
                if instance.vms.exists():
                    payload = self._enqueue(instance=instance, definition=definition, user_id=request.user.id, action="restart", task_func=provision_lab)
                else:
                    payload = self._enqueue(instance=instance, definition=definition, user_id=request.user.id, action="start", task_func=provision_lab)
                return JsonResponse(payload)

            if not instance:
                return JsonResponse({"message": "No instance"}, status=404)

            if action == "stop":
                payload = self._enqueue(instance=instance, definition=definition, user_id=request.user.id, action="stop", task_func=stop_lab)
            elif action == "restart":
                payload = self._enqueue(instance=instance, definition=definition, user_id=request.user.id, action="restart", task_func=provision_lab)
            elif action == "reset":
                payload = self._enqueue(instance=instance, definition=definition, user_id=request.user.id, action="reset", task_func=reset_lab)
            elif action == "extend":
                self.service.check_rate_limit(instance, definition.cooldown_seconds)
                self.service.extend_instance(instance)
                self.service.log_action(instance, request.user.id, "extend", result="success")
                payload = self.service.serialize_instance(instance)
                payload["message"] = "extended"
            else:
                return JsonResponse({"message": "Unsupported action"}, status=400)
            return JsonResponse(payload)
        except ActionConflictError as exc:
            return JsonResponse({"message": str(exc)}, status=429)
        except RuntimeError as exc:
            self.service.log_action(instance, request.user.id, action, result="error", details={"error": str(exc)})
            return JsonResponse({"message": str(exc)}, status=400)


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
        action = _request_body(request).get("action")
        if action == "stop":
            op = stop_lab.delay(instance.id, request.user.id)
        elif action == "reset":
            op = reset_lab.delay(instance.id, request.user.id)
        elif action == "delete":
            op = delete_lab.delay(instance.id, request.user.id)
        else:
            return JsonResponse({"message": "Unsupported action"}, status=400)
        return JsonResponse({"operation_id": op.id, "state": instance.state})
