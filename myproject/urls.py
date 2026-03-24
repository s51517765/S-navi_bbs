# myproject/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    # アプリ(board)のURL設定を読み込む
    path("", include("board.urls")),
]
