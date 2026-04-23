# board/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from board.views import CustomPasswordResetView
from board import views
from .views import (
    PostListView,
    PostCreateView,
    SignUpView,
    Guide,
    # PostUpdateView,
    # PostDeleteView,
)
from .views import CustomLoginView

urlpatterns = [
    path("", PostListView.as_view(), name="index"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("post/new/", PostCreateView.as_view(), name="post_create"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("guide", Guide.as_view(), name="guide"),
    path("activate/<uidb64>/<token>/", views.activate, name="activate"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    # path("post/<int:pk>/edit/", PostUpdateView.as_view(), name="post_edit"),
    # path("post/<int:pk>/delete/", PostDeleteView.as_view(), name="post_delete"),
    path(
        "post/<int:post_id>/eval/<str:eval_type>/",
        views.evaluate_post,
        name="evaluate_post",
    ),
    # 投稿の詳細画面を表示する
    path("post/<int:pk>/", views.post_detail, name="post_detail"),
    # コメントを追加する（投稿のIDを post_id として渡す）
    path("post/<int:post_id>/comment/", views.add_comment, name="add_comment"),
    # リアクション（Good/Bad）を送る
    path(
        "comment/<int:comment_id>/reaction/<str:reaction_type>/",
        views.comment_reaction,
        name="comment_reaction",
    ),
    # パスワードリセット用のURL
    path("password_reset/", CustomPasswordResetView.as_view(), name="password_reset"),
    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
