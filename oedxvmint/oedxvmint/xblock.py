"""XBlock implementation for HTB-like lab controls."""

from __future__ import annotations

import json
import pkg_resources

from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Boolean, Integer, Scope, String
from xblockutils.studio_editable import StudioEditableXBlockMixin


class HTBLabXBlock(StudioEditableXBlockMixin, XBlock):
    """Displays learner VM lab controls and stores lab configuration."""

    display_name = String(default="HTB Lab", scope=Scope.settings)
    mode = String(default="unit", scope=Scope.settings)
    ttl_minutes = Integer(default=120, scope=Scope.settings)
    max_instances = Integer(default=1, scope=Scope.settings)
    cooldown_seconds = Integer(default=5, scope=Scope.settings)
    network_strategy = String(default="pool", scope=Scope.settings)
    vm_specs_json = String(
        default='[{"name":"target-1","role":"target","template_ref":"template-target","show_credentials":false}]',
        scope=Scope.settings,
    )
    author_hint_text = String(default="Attack target from your workstation VM.", scope=Scope.settings)
    allow_extend = Boolean(default=True, scope=Scope.settings)
    extend_minutes = Integer(default=30, scope=Scope.settings)
    team_group_id = String(default="", scope=Scope.settings)

    editable_fields = (
        "display_name",
        "mode",
        "ttl_minutes",
        "max_instances",
        "cooldown_seconds",
        "network_strategy",
        "vm_specs_json",
        "author_hint_text",
        "allow_extend",
        "extend_minutes",
        "team_group_id",
    )

    def resource_string(self, path: str) -> str:
        return pkg_resources.resource_string(__name__, path).decode("utf8")

    def _vm_specs(self):
        try:
            payload = json.loads(self.vm_specs_json)
        except json.JSONDecodeError:
            return []
        return payload if isinstance(payload, list) else []

    def _context(self) -> dict:
        usage_key = str(self.scope_ids.usage_id)
        course_key = str(self.runtime.course_id) if hasattr(self.runtime, "course_id") else usage_key.split("+")[0]
        xblock_config = {
            "display_name": self.display_name,
            "mode": self.mode,
            "ttl_minutes": self.ttl_minutes,
            "max_instances": self.max_instances,
            "cooldown_seconds": self.cooldown_seconds,
            "allow_extend": self.allow_extend,
            "extend_minutes": self.extend_minutes,
            "network_strategy": self.network_strategy,
            "network_config": {},
            "vm_specs": self._vm_specs(),
            "author_hint_text": self.author_hint_text,
        }
        return {
            "display_name": self.display_name,
            "course_id": course_key,
            "block_id": usage_key,
            "hint": self.author_hint_text,
            "allow_extend": self.allow_extend,
            "team_group_id": self.team_group_id,
            "xblock_config": xblock_config,
        }

    def student_view(self, context=None):
        html = self.resource_string("static/html/student_view.html")
        frag = Fragment(html)
        frag.add_css(self.resource_string("static/css/student_view.css"))
        frag.add_javascript(self.resource_string("static/js/src/student_view.js"))
        frag.initialize_js("HTBLabXBlock", self._context())
        return frag

    def studio_view(self, context=None):
        html = self.resource_string("static/html/studio_view.html")
        frag = Fragment(html)
        frag.add_css(self.resource_string("static/css/studio_view.css"))
        frag.add_javascript(self.resource_string("static/js/src/studio_view.js"))
        frag.initialize_js("HTBLabStudio", self._context())
        return frag

    @XBlock.json_handler
    def validate_vm_specs(self, data, suffix=""):
        """Best effort JSON validation for studio authors."""
        payload = data.get("vm_specs_json", self.vm_specs_json)
        try:
            parsed = json.loads(payload)
        except json.JSONDecodeError as exc:
            return {"ok": False, "message": f"Invalid JSON: {exc!s}"}
        if not isinstance(parsed, list) or not parsed:
            return {"ok": False, "message": "vm_specs_json must be a non-empty list"}
        for vm in parsed:
            if vm.get("role") not in {"workstation", "target"}:
                return {"ok": False, "message": "Each VM role must be workstation or target"}
            if not vm.get("template_ref"):
                return {"ok": False, "message": "Each VM must set template_ref"}
        return {"ok": True, "message": "Configuration is valid"}

    @staticmethod
    def workbench_scenarios():
        return [("HTBLabXBlock", """<vertical_demo><oedxvmint/></vertical_demo>""")]
