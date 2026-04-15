import json

from django.views.generic import ListView

from admin_panel.decorators import AdminOnlyMixin
from admin_panel.helpers import querystring_without_page
from myproject.models import AdminLog


class AdminLogListView(AdminOnlyMixin, ListView):
    template_name = "admin_panel/logs_list.html"
    model = AdminLog
    context_object_name = "logs"
    paginate_by = 25

    def get_queryset(self):
        queryset = AdminLog.objects.select_related("admin").order_by("-created_at")

        action = self.request.GET.get("action", "")
        entity_type = self.request.GET.get("entity_type", "")

        if action:
            queryset = queryset.filter(action=action)
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_action"] = self.request.GET.get("action", "")
        context["selected_entity_type"] = self.request.GET.get("entity_type", "")
        context["available_actions"] = (
            AdminLog.objects.values_list("action", flat=True).distinct().order_by("action")
        )
        context["available_entity_types"] = (
            AdminLog.objects.values_list("entity_type", flat=True).distinct().order_by("entity_type")
        )
        context["querystring"] = querystring_without_page(self.request)

        for log in context["logs"]:
            log.old_data_pretty = (
                json.dumps(log.old_data, ensure_ascii=False, indent=2) if log.old_data is not None else "null"
            )
            log.new_data_pretty = (
                json.dumps(log.new_data, ensure_ascii=False, indent=2) if log.new_data is not None else "null"
            )

        return context
