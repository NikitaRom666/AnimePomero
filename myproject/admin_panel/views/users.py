from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from admin_panel.decorators import AdminOnlyMixin, AdminPanelAccessMixin
from admin_panel.forms import UserBanForm, UserRoleForm
from admin_panel.helpers import querystring_without_page, serialize_instance, write_admin_log
from myproject.models import User


class UserListView(AdminPanelAccessMixin, ListView):
    template_name = "admin_panel/users_list.html"
    model = User
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self):
        queryset = User.objects.order_by("-date_joined")

        search_query = self.request.GET.get("q", "").strip()
        role = self.request.GET.get("role", "")
        is_banned = self.request.GET.get("is_banned", "")

        if search_query:
            queryset = queryset.filter(Q(username__icontains=search_query) | Q(email__icontains=search_query))
        if role:
            queryset = queryset.filter(role=role)
        if is_banned in {"true", "false"}:
            queryset = queryset.filter(is_banned=(is_banned == "true"))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_role"] = self.request.GET.get("role", "")
        context["selected_is_banned"] = self.request.GET.get("is_banned", "")
        context["role_choices"] = User.ROLE_CHOICES
        context["querystring"] = querystring_without_page(self.request)
        return context


def _redirect_users_list(request):
    next_url = request.POST.get("next")
    if next_url and next_url.startswith("/admin-panel/users"):
        return redirect(next_url)
    return redirect("admin_panel:users_list")


class UserRoleUpdateView(AdminOnlyMixin, View):
    def post(self, request, user_id):
        user_obj = get_object_or_404(User, pk=user_id)
        old_data = serialize_instance(user_obj)

        form = UserRoleForm(request.POST, instance=user_obj, prefix=f"role_{user_obj.id}")
        if form.is_valid():
            updated_user = form.save(commit=False)
            if updated_user == request.user and updated_user.role != "admin":
                messages.error(request, "Ви не можете зняти права адміністратора із власного акаунту.")
                return _redirect_users_list(request)

            updated_user.save(update_fields=["role"])
            write_admin_log(
                admin=request.user,
                action="change_role",
                entity_type="user",
                entity_id=updated_user.id,
                old_data=old_data,
                new_data=serialize_instance(updated_user),
                request=request,
            )
            messages.success(request, f"Роль користувача '{updated_user.username}' оновлено.")
        else:
            messages.error(request, "Не вдалося змінити роль. Перевірте введені дані.")

        return _redirect_users_list(request)


class UserBanView(AdminPanelAccessMixin, View):
    def post(self, request, user_id):
        user_obj = get_object_or_404(User, pk=user_id)

        if user_obj == request.user:
            messages.error(request, "Ви не можете заблокувати власний акаунт.")
            return _redirect_users_list(request)
        if request.user.role == "moderator" and user_obj.role == "admin":
            messages.error(request, "Модератор не може блокувати адміністратора.")
            return _redirect_users_list(request)

        old_data = serialize_instance(user_obj)
        form = UserBanForm(request.POST, instance=user_obj, prefix=f"ban_{user_obj.id}")

        if form.is_valid():
            banned_user = form.save(commit=False)
            banned_user.is_banned = True
            banned_user.save(update_fields=["is_banned", "banned_until", "ban_reason"])
            write_admin_log(
                admin=request.user,
                action="ban",
                entity_type="user",
                entity_id=banned_user.id,
                old_data=old_data,
                new_data=serialize_instance(banned_user),
                request=request,
            )
            messages.success(request, f"Користувача '{banned_user.username}' заблоковано.")
        else:
            messages.error(request, "Не вдалося заблокувати користувача. Перевірте форму.")

        return _redirect_users_list(request)


class UserUnbanView(AdminPanelAccessMixin, View):
    def post(self, request, user_id):
        user_obj = get_object_or_404(User, pk=user_id)
        old_data = serialize_instance(user_obj)

        user_obj.is_banned = False
        user_obj.banned_until = None
        user_obj.ban_reason = ""
        user_obj.save(update_fields=["is_banned", "banned_until", "ban_reason"])

        write_admin_log(
            admin=request.user,
            action="unban",
            entity_type="user",
            entity_id=user_obj.id,
            old_data=old_data,
            new_data=serialize_instance(user_obj),
            request=request,
        )
        messages.success(request, f"Користувача '{user_obj.username}' розблоковано.")
        return _redirect_users_list(request)


class UserDeleteView(AdminOnlyMixin, View):
    def post(self, request, user_id):
        user_obj = get_object_or_404(User, pk=user_id)

        if user_obj == request.user:
            messages.error(request, "Ви не можете видалити власний акаунт.")
            return _redirect_users_list(request)

        username = user_obj.username
        old_data = serialize_instance(user_obj)
        user_obj.delete()

        write_admin_log(
            admin=request.user,
            action="delete",
            entity_type="user",
            entity_id=user_id,
            old_data=old_data,
            request=request,
        )
        messages.success(request, f"Користувача '{username}' видалено.")
        return _redirect_users_list(request)
