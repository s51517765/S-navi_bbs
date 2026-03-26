# view.py
"""
from django.views.generic import ListView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Post


# 掲示板一覧（誰でも見れる）
class PostListView(ListView):
    model = Post
    template_name = "board/index.html"
    context_object_name = "posts"


# 新規投稿（ログイン必須）
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ["title", "content"]
    template_name = "board/post_form.html"
    success_url = "/"

    def form_valid(self, form):
        form.instance.author = self.request.user  # ログイン中のユーザーを作者にする
        return super().form_valid(form)
"""
