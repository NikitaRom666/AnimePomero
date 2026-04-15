from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView

from admin_panel.decorators import AdminPanelAccessMixin
from admin_panel.helpers import querystring_without_page, serialize_instance, write_admin_log
from myproject.models import Comment, Media


class CommentListView(AdminPanelAccessMixin, ListView):
    template_name = "admin_panel/comments_list.html"
    model = Comment
    context_object_name = "comments"
    paginate_by = 25

    def get_queryset(self):
        queryset = Comment.objects.select_related("user", "media", "parent").order_by("-created_at")

        media_id = self.request.GET.get("media", "")
        is_deleted = self.request.GET.get("is_deleted", "")
        is_censored = self.request.GET.get("is_censored", "")

        if media_id:
            queryset = queryset.filter(media_id=media_id)
        if is_deleted in {"true", "false"}:
            queryset = queryset.filter(is_deleted=(is_deleted == "true"))
        if is_censored in {"true", "false"}:
            queryset = queryset.filter(is_censored=(is_censored == "true"))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["media_list"] = Media.objects.order_by("title")
        context["selected_media"] = self.request.GET.get("media", "")
        context["selected_is_deleted"] = self.request.GET.get("is_deleted", "")
        context["selected_is_censored"] = self.request.GET.get("is_censored", "")
        context["querystring"] = querystring_without_page(self.request)
        return context


class CommentDetailView(AdminPanelAccessMixin, DetailView):
    template_name = "admin_panel/comment_detail.html"
    model = Comment
    context_object_name = "comment"

    def get_queryset(self):
        return Comment.objects.select_related("user", "media", "parent").prefetch_related("replies__user")


def _redirect_comments_list(request):
    next_url = request.POST.get("next")
    if next_url and next_url.startswith("/admin-panel/comments"):
        return redirect(next_url)
    return redirect("admin_panel:comments_list")


class CommentSoftDeleteView(AdminPanelAccessMixin, View):
    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        old_data = serialize_instance(comment)

        if not comment.is_deleted:
            comment.is_deleted = True
            comment.save(update_fields=["is_deleted"])

            write_admin_log(
                admin=request.user,
                action="soft_delete",
                entity_type="comment",
                entity_id=comment.id,
                old_data=old_data,
                new_data=serialize_instance(comment),
                request=request,
            )
            messages.success(request, "Коментар позначено як видалений.")
        else:
            messages.info(request, "Коментар уже позначено як видалений.")

        return _redirect_comments_list(request)


class CommentCensorView(AdminPanelAccessMixin, View):
    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        old_data = serialize_instance(comment)

        if not comment.is_censored:
            comment.is_censored = True
            comment.save(update_fields=["is_censored"])

            write_admin_log(
                admin=request.user,
                action="censor",
                entity_type="comment",
                entity_id=comment.id,
                old_data=old_data,
                new_data=serialize_instance(comment),
                request=request,
            )
            messages.success(request, "Коментар успішно зацензуровано.")
        else:
            messages.info(request, "Коментар уже зацензуровано.")

        return _redirect_comments_list(request)
