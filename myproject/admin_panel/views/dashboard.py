import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

from admin_panel.decorators import AdminPanelAccessMixin
from myproject.models import Comment, Media, Report, User


class AdminPanelLoginView(LoginView):
    template_name = "admin_panel/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("admin_panel:dashboard")

    def form_valid(self, form):
        user = form.get_user()
        if user.role not in {"admin", "moderator"}:
            messages.error(self.request, "Доступ до адмін-панелі дозволений лише модераторам та адміністраторам.")
            return redirect("admin_panel:login")
        if user.is_banned:
            messages.error(self.request, "Ваш акаунт заблоковано.")
            return redirect("admin_panel:login")
        return super().form_valid(form)


class DashboardView(AdminPanelAccessMixin, TemplateView):
    template_name = "admin_panel/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["total_users"] = User.objects.count()
        context["total_media"] = Media.objects.count()
        context["total_comments"] = Comment.objects.count()
        context["pending_reports"] = Report.objects.filter(status="pending").count()

        today = timezone.localdate()
        start_date = today - timedelta(days=29)

        registrations = (
            User.objects.filter(date_joined__date__gte=start_date)
            .annotate(day=TruncDate("date_joined"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )
        registrations_map = {item["day"]: item["total"] for item in registrations}

        labels = []
        data = []
        for i in range(30):
            day = start_date + timedelta(days=i)
            labels.append(day.strftime("%d.%m"))
            data.append(registrations_map.get(day, 0))

        context["registration_labels_json"] = json.dumps(labels, ensure_ascii=False)
        context["registration_data_json"] = json.dumps(data)
        context["top_media"] = Media.objects.order_by("-views_count", "title")[:5]

        return context
