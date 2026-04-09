from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


# ============================================================
# USERS
# ============================================================

class User(AbstractUser):
    groups = models.ManyToManyField('auth.Group', related_name='custom_user_set', blank=True)
    user_permissions = models.ManyToManyField('auth.Permission', related_name='custom_user_permissions_set', blank=True)
    ROLE_CHOICES = [
        ('user',      'Користувач'),
        ('moderator', 'Модератор'),
        ('admin',     'Адміністратор'),
    ]
    role       = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    avatar_url = models.URLField(blank=True, null=True)
    is_banned  = models.BooleanField(default=False)
    banned_until = models.DateTimeField(blank=True, null=True)
    ban_reason = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'Користувач'
        verbose_name_plural = 'Користувачі'

    def __str__(self):
        return self.username


# ============================================================
# STUDIOS
# ============================================================

class Studio(models.Model):
    name    = models.CharField(max_length=200)
    country = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'studios'
        verbose_name = 'Студія'
        verbose_name_plural = 'Студії'

    def __str__(self):
        return self.name


# ============================================================
# GENRES
# ============================================================

class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'genres'
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанри'

    def __str__(self):
        return self.name


# ============================================================
# DUBBING LANGUAGES
# ============================================================

class DubbingLanguage(models.Model):
    language = models.CharField(max_length=100)
    country  = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = 'dubbing_languages'
        verbose_name = 'Мова озвучення'
        verbose_name_plural = 'Мови озвучення'

    def __str__(self):
        return self.language


# ============================================================
# MEDIA
# ============================================================

class Media(models.Model):
    MEDIA_TYPE_CHOICES = [
        ('anime',  'Аніме'),
        ('serial', 'Серіал'),
        ('movie',  'Фільм'),
    ]

    title            = models.CharField(max_length=500)
    original_title   = models.CharField(max_length=500, blank=True, null=True)
    description      = models.TextField(blank=True, null=True)
    media_type       = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES)
    release_year     = models.SmallIntegerField(blank=True, null=True)
    country          = models.CharField(max_length=100, blank=True, null=True)
    episode_count    = models.SmallIntegerField(default=0)
    season_count     = models.SmallIntegerField(default=0)
    episode_duration = models.SmallIntegerField(blank=True, null=True, help_text='хвилини')
    rating           = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    views_count      = models.IntegerField(default=0)
    reactions_count  = models.IntegerField(default=0)
    poster_url       = models.URLField(blank=True, null=True)
    is_published     = models.BooleanField(default=True)
    studio           = models.ForeignKey(
        Studio, on_delete=models.SET_NULL, null=True, blank=True, related_name='media'
    )
    genres           = models.ManyToManyField(Genre, through='MediaGenre', blank=True)
    dubbing_languages = models.ManyToManyField(
        DubbingLanguage, through='MediaDubbing', blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'media'
        verbose_name = 'Медіа'
        verbose_name_plural = 'Медіа'
        ordering = ['-views_count']

    def __str__(self):
        return f'{self.title} ({self.get_media_type_display()})'


# ============================================================
# MEDIA_GENRES (M2M через проміжну таблицю)
# ============================================================

class MediaGenre(models.Model):
    media = models.ForeignKey(Media, on_delete=models.CASCADE)
    genre = models.ForeignKey(Genre, on_delete=models.CASCADE)

    class Meta:
        db_table = 'media_genres'
        unique_together = ('media', 'genre')


# ============================================================
# MEDIA_DUBBING (M2M через проміжну таблицю)
# ============================================================

class MediaDubbing(models.Model):
    media   = models.ForeignKey(Media, on_delete=models.CASCADE)
    dubbing = models.ForeignKey(DubbingLanguage, on_delete=models.CASCADE)

    class Meta:
        db_table = 'media_dubbing'
        unique_together = ('media', 'dubbing')


# ============================================================
# SEASONS
# ============================================================

class Season(models.Model):
    media         = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='seasons')
    season_number = models.SmallIntegerField()
    year          = models.SmallIntegerField(blank=True, null=True)
    title         = models.CharField(max_length=300, blank=True, null=True)

    class Meta:
        db_table = 'seasons'
        unique_together = ('media', 'season_number')
        ordering = ['season_number']
        verbose_name = 'Сезон'
        verbose_name_plural = 'Сезони'

    def __str__(self):
        return f'{self.media.title} — Сезон {self.season_number}'


# ============================================================
# EPISODES
# ============================================================

class Episode(models.Model):
    season         = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='episodes')
    episode_number = models.SmallIntegerField()
    title          = models.CharField(max_length=500, blank=True, null=True)
    duration_sec   = models.IntegerField(blank=True, null=True)
    air_date       = models.DateField(blank=True, null=True)
    description    = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'episodes'
        unique_together = ('season', 'episode_number')
        ordering = ['episode_number']
        verbose_name = 'Епізод'
        verbose_name_plural = 'Епізоди'

    def __str__(self):
        return f'{self.season} — Епізод {self.episode_number}'


# ============================================================
# COMMENTS
# ============================================================

class Comment(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    media       = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='comments')
    parent      = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies'
    )
    content     = models.TextField()
    is_deleted  = models.BooleanField(default=False)
    is_censored = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'comments'
        ordering = ['-created_at']
        verbose_name = 'Коментар'
        verbose_name_plural = 'Коментарі'

    def __str__(self):
        return f'Коментар від {self.user.username} до {self.media.title}'


# ============================================================
# COMMENT_REACTIONS
# ============================================================

class CommentReaction(models.Model):
    REACTION_CHOICES = [
        ('positive', 'Позитивна'),
        ('negative', 'Негативна'),
    ]
    comment       = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='reactions')
    user          = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'comment_reactions'
        unique_together = ('comment', 'user')
        verbose_name = 'Реакція на коментар'
        verbose_name_plural = 'Реакції на коментарі'


# ============================================================
# USER_MEDIA_STATUS (трекінг)
# ============================================================

class UserMediaStatus(models.Model):
    STATUS_CHOICES = [
        ('watching',       'Дивлюсь'),
        ('completed',      'Переглянуто'),
        ('on_hold',        'Призупинено'),
        ('dropped',        'Покинуто'),
        ('plan_to_watch',  'Планую'),
    ]
    user             = models.ForeignKey(User, on_delete=models.CASCADE, related_name='media_statuses')
    media            = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='user_statuses')
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default='plan_to_watch')
    episodes_watched = models.SmallIntegerField(default=0)
    user_rating      = models.SmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_media_status'
        unique_together = ('user', 'media')
        verbose_name = 'Статус перегляду'
        verbose_name_plural = 'Статуси перегляду'


# ============================================================
# COLLECTIONS
# ============================================================

class Collection(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')
    title       = models.CharField(max_length=300)
    description = models.TextField(blank=True, null=True)
    is_public   = models.BooleanField(default=True)
    media       = models.ManyToManyField(Media, through='CollectionMedia', blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'collections'
        verbose_name = 'Колекція'
        verbose_name_plural = 'Колекції'

    def __str__(self):
        return f'{self.user.username} — {self.title}'


# ============================================================
# COLLECTION_MEDIA (M2M)
# ============================================================

class CollectionMedia(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    media      = models.ForeignKey(Media, on_delete=models.CASCADE)
    added_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'collection_media'
        unique_together = ('collection', 'media')


# ============================================================
# MEDIA_VIEWS (для тренд-системи)
# ============================================================

class MediaView(models.Model):
    media     = models.ForeignKey(Media, on_delete=models.CASCADE, related_name='views')
    user      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'media_views'
        verbose_name = 'Перегляд'
        verbose_name_plural = 'Перегляди'
        indexes = [
            models.Index(fields=['media', 'viewed_at']),
        ]


# ============================================================
# REPORTS (скарги)
# ============================================================

class Report(models.Model):
    REASON_CHOICES = [
        ('spam',           'Спам'),
        ('offensive',      'Образливий контент'),
        ('spoiler',        'Спойлер'),
        ('misinformation', 'Дезінформація'),
        ('other',          'Інше'),
    ]
    STATUS_CHOICES = [
        ('pending',   'На розгляді'),
        ('reviewed',  'Переглянуто'),
        ('resolved',  'Вирішено'),
        ('dismissed', 'Відхилено'),
    ]
    reporter       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_sent')
    media          = models.ForeignKey(Media, on_delete=models.CASCADE, null=True, blank=True)
    comment        = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    target_user    = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name='reports_received'
    )
    reason      = models.CharField(max_length=30, choices=REASON_CHOICES)
    description = models.TextField(blank=True, null=True)
    status      = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    resolved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports_resolved'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        verbose_name = 'Скарга'
        verbose_name_plural = 'Скарги'


# ============================================================
# ADMIN_LOGS (журнал дій)
# ============================================================

class AdminLog(models.Model):
    admin       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_logs')
    action      = models.CharField(max_length=100)   # create, update, delete, ban ...
    entity_type = models.CharField(max_length=100)   # media, user, comment ...
    entity_id   = models.IntegerField(null=True, blank=True)
    old_data    = models.JSONField(null=True, blank=True)
    new_data    = models.JSONField(null=True, blank=True)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin_logs'
        ordering = ['-created_at']
        verbose_name = 'Лог адміна'
        verbose_name_plural = 'Логи адміна'

    def __str__(self):
        return f'{self.admin.username} — {self.action} {self.entity_type}'
