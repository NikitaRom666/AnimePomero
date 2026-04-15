from .analytics import AnalyticsView
from .comments import CommentCensorView, CommentDetailView, CommentListView, CommentSoftDeleteView
from .dashboard import AdminPanelLoginView, DashboardView
from .logs import AdminLogListView
from .media import (
    EpisodeCreateView,
    EpisodeDeleteView,
    EpisodeUpdateView,
    MediaCreateView,
    MediaDeleteView,
    MediaListView,
    MediaSeasonsView,
    MediaUpdateView,
    SeasonCreateView,
    SeasonDeleteView,
    SeasonUpdateView,
)
from .reports import ReportActionView, ReportDetailView, ReportListView
from .users import UserBanView, UserDeleteView, UserListView, UserRoleUpdateView, UserUnbanView

__all__ = [
    "DashboardView",
    "AdminPanelLoginView",
    "MediaListView",
    "MediaCreateView",
    "MediaUpdateView",
    "MediaDeleteView",
    "MediaSeasonsView",
    "SeasonCreateView",
    "SeasonUpdateView",
    "SeasonDeleteView",
    "EpisodeCreateView",
    "EpisodeUpdateView",
    "EpisodeDeleteView",
    "UserListView",
    "UserRoleUpdateView",
    "UserBanView",
    "UserUnbanView",
    "UserDeleteView",
    "CommentListView",
    "CommentDetailView",
    "CommentSoftDeleteView",
    "CommentCensorView",
    "ReportListView",
    "ReportDetailView",
    "ReportActionView",
    "AnalyticsView",
    "AdminLogListView",
]
