import json
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.views.generic import TemplateView

from admin_panel.decorators import AdminPanelAccessMixin
from myproject.models import Genre, Media, MediaView, User


class AnalyticsView(AdminPanelAccessMixin, TemplateView):
    template_name = "admin_panel/analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()

        media_type_map = dict(Media.MEDIA_TYPE_CHOICES)
        media_by_type_raw = Media.objects.values("media_type").annotate(total=Count("id"))
        media_count_map = {item["media_type"]: item["total"] for item in media_by_type_raw}

        media_type_labels = [media_type_map["anime"], media_type_map["serial"], media_type_map["movie"]]
        media_type_data = [
            media_count_map.get("anime", 0),
            media_count_map.get("serial", 0),
            media_count_map.get("movie", 0),
        ]

        views_start = today - timedelta(days=29)
        views_raw = (
            MediaView.objects.filter(viewed_at__date__gte=views_start)
            .annotate(day=TruncDate("viewed_at"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )
        views_map = {item["day"]: item["total"] for item in views_raw}

        view_labels = []
        view_data = []
        for i in range(30):
            day = views_start + timedelta(days=i)
            view_labels.append(day.strftime("%d.%m"))
            view_data.append(views_map.get(day, 0))

        top_genres = Genre.objects.annotate(total=Count("media", distinct=True)).order_by("-total", "name")[:10]

        reg_start = today - timedelta(days=89)
        registrations_raw = (
            User.objects.filter(date_joined__date__gte=reg_start)
            .annotate(day=TruncDate("date_joined"))
            .values("day")
            .annotate(total=Count("id"))
            .order_by("day")
        )
        registrations_map = {item["day"]: item["total"] for item in registrations_raw}

        registration_labels = []
        registration_data = []
        for i in range(90):
            day = reg_start + timedelta(days=i)
            registration_labels.append(day.strftime("%d.%m"))
            registration_data.append(registrations_map.get(day, 0))

        seven_days_ago = timezone.now() - timedelta(days=7)
        trending_media = (
            Media.objects.annotate(recent_views=Count("views", filter=Q(views__viewed_at__gte=seven_days_ago)))
            .filter(recent_views__gt=0)
            .order_by("-recent_views", "title")[:10]
        )

        context["media_type_labels_json"] = json.dumps(media_type_labels, ensure_ascii=False)
        context["media_type_data_json"] = json.dumps(media_type_data)
        context["view_labels_json"] = json.dumps(view_labels, ensure_ascii=False)
        context["view_data_json"] = json.dumps(view_data)
        context["genre_labels_json"] = json.dumps([genre.name for genre in top_genres], ensure_ascii=False)
        context["genre_data_json"] = json.dumps([genre.total for genre in top_genres])
        context["registration_labels_json"] = json.dumps(registration_labels, ensure_ascii=False)
        context["registration_data_json"] = json.dumps(registration_data)
        context["trending_media"] = trending_media

        return context
