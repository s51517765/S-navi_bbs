# board/urls.py
from django.urls import path
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
    path("post/new/", PostCreateView.as_view(), name="post_create"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("activate/<uidb64>/<token>/", views.activate, name="activate"),
    path("post/<int:pk>/edit/", PostUpdateView.as_view(), name="post_edit"),
    path("post/<int:pk>/delete/", PostDeleteView.as_view(), name="post_delete"),
    path(
        "post/<int:post_id>/eval/<str:eval_type>/",
        views.evaluate_post,
        name="evaluate_post",
    ),
]
