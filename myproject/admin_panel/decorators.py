from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


ALLOWED_ROLES = {"admin", "moderator"}


def user_is_admin_or_moderator(user):
    return bool(user.is_authenticated and user.role in ALLOWED_ROLES and not user.is_banned)


def user_is_admin(user):
    return bool(user.is_authenticated and user.role == "admin" and not user.is_banned)


def admin_panel_required(view_func):
    @login_required(login_url="admin_panel:login")
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not user_is_admin_or_moderator(request.user):
            raise PermissionDenied("Недостатньо прав доступу.")
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_only_required(view_func):
    @login_required(login_url="admin_panel:login")
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not user_is_admin(request.user):
            raise PermissionDenied("Лише адміністратор має доступ до цієї дії.")
        return view_func(request, *args, **kwargs)

    return _wrapped


class AdminPanelAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    login_url = "admin_panel:login"
    raise_exception = False
    allowed_roles = ALLOWED_ROLES

    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and user.role in self.allowed_roles and not user.is_banned)

    def handle_no_permission(self):
        user = self.request.user

        if not user.is_authenticated:
            return redirect("admin_panel:login")

        if getattr(user, "is_banned", False):
            messages.error(self.request, "Ваш акаунт заблоковано. Доступ до адмін-панелі заборонено.")
            return redirect("admin_panel:login")

        if getattr(user, "role", None) in ALLOWED_ROLES:
            raise PermissionDenied("Недостатньо прав доступу.")

        messages.error(self.request, "Доступ до адмін-панелі дозволений лише модераторам та адміністраторам.")
        return redirect("admin_panel:login")

        raise PermissionDenied("Недостатньо прав доступу.")


class AdminOnlyMixin(AdminPanelAccessMixin):
    allowed_roles = {"admin"}
