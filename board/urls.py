# board/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import (
    PostListView,
    PostCreateView,
    SignUpView,
    PostUpdateView,
    PostDeleteView,
)


urlpatterns = [
    path("", PostListView.as_view(), name="index"),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("post/new/", PostCreateView.as_view(), name="post_create"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("activate/<uidb64>/<token>/", views.activate, name="activate"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("post/<int:pk>/edit/", PostUpdateView.as_view(), name="post_edit"),
    path("post/<int:pk>/delete/", PostDeleteView.as_view(), name="post_delete"),
    path(
        "post/<int:post_id>/eval/<str:eval_type>/",
        views.evaluate_post,
        name="evaluate_post",
    ),
    # パスワードリセット用のURL
    path(
        "password_reset/", auth_views.PasswordResetView.as_view(), name="password_reset"
    ),
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
