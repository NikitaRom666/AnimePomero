from django.contrib import messages
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from admin_panel.decorators import AdminPanelAccessMixin
from admin_panel.forms import EpisodeForm, MediaForm, SeasonForm
from admin_panel.helpers import querystring_without_page, serialize_instance, write_admin_log
from myproject.models import Episode, Genre, Media, Season


class MediaListView(AdminPanelAccessMixin, ListView):
    template_name = "admin_panel/media_list.html"
    model = Media
    context_object_name = "media_list"
    paginate_by = 25

    def get_queryset(self):
        queryset = Media.objects.select_related("studio").prefetch_related("genres").order_by("-created_at")

        media_type = self.request.GET.get("media_type")
        genre_id = self.request.GET.get("genre")
        is_published = self.request.GET.get("is_published")
        search_query = self.request.GET.get("q", "").strip()

        if media_type:
            queryset = queryset.filter(media_type=media_type)
        if genre_id:
            queryset = queryset.filter(genres__id=genre_id)
        if is_published in {"true", "false"}:
            queryset = queryset.filter(is_published=(is_published == "true"))
        if search_query:
            queryset = queryset.filter(title__icontains=search_query)

        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["media_type_choices"] = Media.MEDIA_TYPE_CHOICES
        context["genres"] = Genre.objects.order_by("name")
        context["selected_media_type"] = self.request.GET.get("media_type", "")
        context["selected_genre"] = self.request.GET.get("genre", "")
        context["selected_is_published"] = self.request.GET.get("is_published", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["querystring"] = querystring_without_page(self.request)
        return context


class MediaCreateView(AdminPanelAccessMixin, CreateView):
    model = Media
    form_class = MediaForm
    template_name = "admin_panel/media_form.html"
    success_url = reverse_lazy("admin_panel:media_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        write_admin_log(
            admin=self.request.user,
            action="create",
            entity_type="media",
            entity_id=self.object.id,
            new_data=serialize_instance(self.object, m2m_fields=["genres", "dubbing_languages"]),
            request=self.request,
        )
        messages.success(self.request, "Медіа успішно створено.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Не вдалося створити медіа. Перевірте дані форми.")
        return super().form_invalid(form)


class MediaUpdateView(AdminPanelAccessMixin, UpdateView):
    model = Media
    form_class = MediaForm
    template_name = "admin_panel/media_form.html"
    success_url = reverse_lazy("admin_panel:media_list")

    def form_valid(self, form):
        old_data = serialize_instance(self.get_object(), m2m_fields=["genres", "dubbing_languages"])
        response = super().form_valid(form)
        write_admin_log(
            admin=self.request.user,
            action="update",
            entity_type="media",
            entity_id=self.object.id,
            old_data=old_data,
            new_data=serialize_instance(self.object, m2m_fields=["genres", "dubbing_languages"]),
            request=self.request,
        )
        messages.success(self.request, "Медіа успішно оновлено.")
        return response

    def form_invalid(self, form):
        messages.error(self.request, "Не вдалося оновити медіа. Перевірте дані форми.")
        return super().form_invalid(form)


class MediaDeleteView(AdminPanelAccessMixin, View):
    def post(self, request, pk):
        media = get_object_or_404(Media, pk=pk)
        media_title = media.title
        old_data = serialize_instance(media, m2m_fields=["genres", "dubbing_languages"])

        media.delete()
        write_admin_log(
            admin=request.user,
            action="delete",
            entity_type="media",
            entity_id=pk,
            old_data=old_data,
            request=request,
        )
        messages.success(request, f"Медіа '{media_title}' видалено.")
        return redirect("admin_panel:media_list")


def sync_media_counts(media):
    season_total = media.seasons.count()
    episode_total = Episode.objects.filter(season__media=media).count()
    Media.objects.filter(pk=media.pk).update(season_count=season_total, episode_count=episode_total)


class MediaSeasonsView(AdminPanelAccessMixin, TemplateView):
    template_name = "admin_panel/media_seasons.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        media = get_object_or_404(
            Media.objects.prefetch_related(
                Prefetch(
                    "seasons",
                    queryset=Season.objects.prefetch_related("episodes").order_by("season_number"),
                )
            ),
            pk=self.kwargs["media_id"],
        )

        season_blocks = []
        for season in media.seasons.all():
            episodes = []
            for episode in season.episodes.all():
                episodes.append(
                    {
                        "episode": episode,
                        "edit_form": EpisodeForm(instance=episode, prefix=f"ep_{episode.id}"),
                    }
                )

            season_blocks.append(
                {
                    "season": season,
                    "edit_form": SeasonForm(instance=season, prefix=f"season_{season.id}"),
                    "episode_create_form": EpisodeForm(prefix=f"new_ep_{season.id}"),
                    "episodes": episodes,
                }
            )

        context["media"] = media
        context["season_create_form"] = SeasonForm(prefix="season_new")
        context["season_blocks"] = season_blocks
        return context


class SeasonCreateView(AdminPanelAccessMixin, View):
    def post(self, request, media_id):
        media = get_object_or_404(Media, pk=media_id)
        form = SeasonForm(request.POST, prefix="season_new")

        if form.is_valid():
            season = form.save(commit=False)
            season.media = media
            season.save()

            sync_media_counts(media)
            write_admin_log(
                admin=request.user,
                action="create",
                entity_type="season",
                entity_id=season.id,
                new_data=serialize_instance(season),
                request=request,
            )
            messages.success(request, "Сезон успішно додано.")
        else:
            messages.error(request, "Не вдалося додати сезон. Перевірте введені дані.")

        return redirect(reverse("admin_panel:media_seasons", kwargs={"media_id": media_id}))


class SeasonUpdateView(AdminPanelAccessMixin, View):
    def post(self, request, media_id, season_id):
        media = get_object_or_404(Media, pk=media_id)
        season = get_object_or_404(Season, pk=season_id, media=media)
        old_data = serialize_instance(season)

        form = SeasonForm(request.POST, instance=season, prefix=f"season_{season.id}")
        if form.is_valid():
            updated = form.save()
            sync_media_counts(media)
            write_admin_log(
                admin=request.user,
                action="update",
                entity_type="season",
                entity_id=updated.id,
                old_data=old_data,
                new_data=serialize_instance(updated),
                request=request,
            )
            messages.success(request, "Сезон успішно оновлено.")
        else:
            messages.error(request, "Не вдалося оновити сезон. Перевірте введені дані.")

        return redirect(reverse("admin_panel:media_seasons", kwargs={"media_id": media_id}))


class SeasonDeleteView(AdminPanelAccessMixin, View):
    def post(self, request, media_id, season_id):
        media = get_object_or_404(Media, pk=media_id)
        season = get_object_or_404(Season, pk=season_id, media=media)
        old_data = serialize_instance(season)

        season.delete()
        sync_media_counts(media)
        write_admin_log(
            admin=request.user,
            action="delete",
            entity_type="season",
            entity_id=season_id,
            old_data=old_data,
            request=request,
        )
        messages.success(request, "Сезон видалено.")
        return redirect(reverse("admin_panel:media_seasons", kwargs={"media_id": media_id}))


class EpisodeCreateView(AdminPanelAccessMixin, View):
    def post(self, request, media_id, season_id):
        media = get_object_or_404(Media, pk=media_id)
        season = get_object_or_404(Season, pk=season_id, media=media)
        form = EpisodeForm(request.POST, prefix=f"new_ep_{season.id}")

        if form.is_valid():
            episode = form.save(commit=False)
            episode.season = season
            episode.save()

            sync_media_counts(media)
            write_admin_log(
                admin=request.user,
                action="create",
                entity_type="episode",
                entity_id=episode.id,
                new_data=serialize_instance(episode),
                request=request,
            )
            messages.success(request, "Епізод успішно додано.")
        else:
            messages.error(request, "Не вдалося додати епізод. Перевірте введені дані.")

        return redirect(reverse("admin_panel:media_seasons", kwargs={"media_id": media_id}))


class EpisodeUpdateView(AdminPanelAccessMixin, View):
    def post(self, request, media_id, season_id, episode_id):
        media = get_object_or_404(Media, pk=media_id)
        season = get_object_or_404(Season, pk=season_id, media=media)
        episode = get_object_or_404(Episode, pk=episode_id, season=season)
        old_data = serialize_instance(episode)

        form = EpisodeForm(request.POST, instance=episode, prefix=f"ep_{episode.id}")
        if form.is_valid():
            updated = form.save()
            sync_media_counts(media)
            write_admin_log(
                admin=request.user,
                action="update",
                entity_type="episode",
                entity_id=updated.id,
                old_data=old_data,
                new_data=serialize_instance(updated),
                request=request,
            )
            messages.success(request, "Епізод успішно оновлено.")
        else:
            messages.error(request, "Не вдалося оновити епізод. Перевірте введені дані.")

        return redirect(reverse("admin_panel:media_seasons", kwargs={"media_id": media_id}))


class EpisodeDeleteView(AdminPanelAccessMixin, View):
    def post(self, request, media_id, season_id, episode_id):
        media = get_object_or_404(Media, pk=media_id)
        season = get_object_or_404(Season, pk=season_id, media=media)
        episode = get_object_or_404(Episode, pk=episode_id, season=season)
        old_data = serialize_instance(episode)

        episode.delete()
        sync_media_counts(media)
        write_admin_log(
            admin=request.user,
            action="delete",
            entity_type="episode",
            entity_id=episode_id,
            old_data=old_data,
            request=request,
        )
        messages.success(request, "Епізод видалено.")
        return redirect(reverse("admin_panel:media_seasons", kwargs={"media_id": media_id}))
