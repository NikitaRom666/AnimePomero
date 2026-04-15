from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from admin_panel.decorators import AdminPanelAccessMixin
from admin_panel.forms import ReportModerationForm
from admin_panel.helpers import querystring_without_page, serialize_instance, write_admin_log
from myproject.models import Report


class ReportListView(AdminPanelAccessMixin, ListView):
    template_name = "admin_panel/reports_list.html"
    model = Report
    context_object_name = "reports"
    paginate_by = 25

    def get_queryset(self):
        queryset = Report.objects.select_related(
            "reporter", "media", "comment", "comment__user", "target_user", "resolved_by"
        ).order_by("-created_at")

        status = self.request.GET.get("status", "")
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["selected_status"] = self.request.GET.get("status", "")
        context["status_choices"] = Report.STATUS_CHOICES
        context["querystring"] = querystring_without_page(self.request)
        return context


class ReportDetailView(AdminPanelAccessMixin, DetailView):
    template_name = "admin_panel/report_detail.html"
    model = Report
    context_object_name = "report"

    def get_queryset(self):
        return Report.objects.select_related(
            "reporter", "media", "comment", "comment__user", "target_user", "resolved_by"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["resolve_form"] = ReportModerationForm(
            instance=self.object,
            prefix="report",
            initial={"status": "resolved"},
        )
        return context


class ReportActionView(AdminPanelAccessMixin, View):
    valid_actions = {"reviewed", "resolved", "dismissed"}

    def post(self, request, pk, action):
        report = get_object_or_404(
            Report.objects.select_related("comment", "comment__user", "target_user"),
            pk=pk,
        )

        if action not in self.valid_actions:
            messages.error(request, "Непідтримувана дія для скарги.")
            return redirect("admin_panel:report_detail", pk=report.pk)

        old_data = serialize_instance(report)

        if action == "reviewed":
            report.status = "reviewed"
            report.save(update_fields=["status"])
            messages.success(request, "Скаргу позначено як переглянуту.")

        elif action == "dismissed":
            report.status = "dismissed"
            report.resolved_by = request.user
            report.resolved_at = timezone.now()
            report.save(update_fields=["status", "resolved_by", "resolved_at"])
            messages.success(request, "Скаргу відхилено.")

        else:
            form = ReportModerationForm(request.POST, instance=report, prefix="report")
            if not form.is_valid():
                messages.error(request, "Не вдалося вирішити скаргу. Перевірте форму.")
                return redirect("admin_panel:report_detail", pk=report.pk)

            report = form.save(commit=False)
            report.status = "resolved"
            report.resolved_by = request.user
            report.resolved_at = timezone.now()
            report.save(update_fields=["status", "resolved_by", "resolved_at"])

            self._handle_resolution_effects(request, report, form.cleaned_data)
            messages.success(request, "Скаргу вирішено.")

        write_admin_log(
            admin=request.user,
            action=f"report_{action}",
            entity_type="report",
            entity_id=report.id,
            old_data=old_data,
            new_data=serialize_instance(report),
            request=request,
        )
        next_url = request.POST.get("next")
        if next_url and next_url.startswith("/admin-panel/reports"):
            return redirect(next_url)
        return redirect("admin_panel:report_detail", pk=report.pk)

    def _handle_resolution_effects(self, request, report, cleaned_data):
        if cleaned_data.get("ban_target_user"):
            target_user = report.target_user
            if not target_user and report.comment:
                target_user = report.comment.user

            if target_user:
                old_user_data = serialize_instance(target_user)
                target_user.is_banned = True
                target_user.banned_until = cleaned_data.get("banned_until")
                target_user.ban_reason = cleaned_data.get("ban_reason") or (
                    f"Автоблокування за скаргою #{report.id}: {report.get_reason_display()}"
                )
                target_user.save(update_fields=["is_banned", "banned_until", "ban_reason"])

                write_admin_log(
                    admin=request.user,
                    action="ban",
                    entity_type="user",
                    entity_id=target_user.id,
                    old_data=old_user_data,
                    new_data=serialize_instance(target_user),
                    request=request,
                )

        if cleaned_data.get("delete_target_comment") and report.comment:
            comment = report.comment
            if not comment.is_deleted:
                old_comment_data = serialize_instance(comment)
                comment.is_deleted = True
                comment.save(update_fields=["is_deleted"])

                write_admin_log(
                    admin=request.user,
                    action="soft_delete",
                    entity_type="comment",
                    entity_id=comment.id,
                    old_data=old_comment_data,
                    new_data=serialize_instance(comment),
                    request=request,
                )
