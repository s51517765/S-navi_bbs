# myproject/urls.py
from django.contrib import admin
from django.urls import path, include
from board import views

urlpatterns = [
    # アプリ(board)のURL設定を読み込む
    path("", include("board.urls")),
    path("admin/", admin.site.urls),
]
