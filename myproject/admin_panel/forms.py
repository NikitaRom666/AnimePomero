from django import forms
from django.utils import timezone

from myproject.models import DubbingLanguage, Episode, Genre, Media, Report, Season, User


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                css_class = "form-select"
            else:
                css_class = "form-control"

            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {css_class}".strip()


class MediaForm(BootstrapFormMixin, forms.ModelForm):
    genres = forms.ModelMultipleChoiceField(
        queryset=Genre.objects.order_by("name"),
        required=False,
        label="Жанри",
    )
    dubbing_languages = forms.ModelMultipleChoiceField(
        queryset=DubbingLanguage.objects.order_by("language"),
        required=False,
        label="Мови озвучення",
    )

    class Meta:
        model = Media
        fields = [
            "title",
            "original_title",
            "description",
            "media_type",
            "release_year",
            "country",
            "episode_count",
            "season_count",
            "episode_duration",
            "poster_url",
            "studio",
            "genres",
            "dubbing_languages",
            "is_published",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "is_published": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["genres"].initial = self.instance.genres.all()
            self.fields["dubbing_languages"].initial = self.instance.dubbing_languages.all()

    def clean_release_year(self):
        release_year = self.cleaned_data.get("release_year")
        if release_year is None:
            return release_year

        current_year = timezone.localdate().year
        if release_year < 1900 or release_year > current_year + 1:
            raise forms.ValidationError("Некоректний рік релізу.")
        return release_year

    def clean(self):
        cleaned_data = super().clean()
        media_type = cleaned_data.get("media_type")
        season_count = cleaned_data.get("season_count") or 0

        if media_type == "movie" and season_count > 0:
            self.add_error("season_count", "Для фільмів кількість сезонів має бути 0.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            instance.genres.set(self.cleaned_data.get("genres", []))
            instance.dubbing_languages.set(self.cleaned_data.get("dubbing_languages", []))
        return instance


class SeasonForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Season
        fields = ["season_number", "year", "title"]

    def clean_season_number(self):
        season_number = self.cleaned_data["season_number"]
        if season_number < 1:
            raise forms.ValidationError("Номер сезону має бути більшим за 0.")
        return season_number


class EpisodeForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Episode
        fields = ["episode_number", "title", "duration_sec", "air_date", "description"]
        widgets = {
            "air_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_episode_number(self):
        episode_number = self.cleaned_data["episode_number"]
        if episode_number < 1:
            raise forms.ValidationError("Номер епізоду має бути більшим за 0.")
        return episode_number


class UserRoleForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["role"]


class UserBanForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["banned_until", "ban_reason"]
        widgets = {
            "banned_until": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "ban_reason": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["banned_until"].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean_banned_until(self):
        banned_until = self.cleaned_data.get("banned_until")
        if banned_until and banned_until <= timezone.now():
            raise forms.ValidationError("Дата блокування має бути в майбутньому.")
        return banned_until


class ReportModerationForm(BootstrapFormMixin, forms.ModelForm):
    ban_target_user = forms.BooleanField(required=False, label="Заблокувати цільового користувача")
    delete_target_comment = forms.BooleanField(required=False, label="Позначити коментар як видалений")
    ban_reason = forms.CharField(required=False, label="Причина блокування", widget=forms.Textarea(attrs={"rows": 2}))
    banned_until = forms.DateTimeField(
        required=False,
        label="Заблоковано до",
        input_formats=["%Y-%m-%dT%H:%M"],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
    )

    class Meta:
        model = Report
        fields = ["status"]
        widgets = {
            "status": forms.HiddenInput(),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("ban_target_user") and not cleaned_data.get("ban_reason"):
            self.add_error("ban_reason", "Вкажіть причину блокування.")

        banned_until = cleaned_data.get("banned_until")
        if banned_until and banned_until <= timezone.now():
            self.add_error("banned_until", "Дата блокування має бути в майбутньому.")

        return cleaned_data
