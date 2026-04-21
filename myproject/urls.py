# myproject/urls.py
from django.contrib import admin
from django.urls import path, include
from board import views
from django.conf.urls import handler404
from .views import custom_404_view

urlpatterns = [
    # アプリ(board)のURL設定を読み込む
    path("", include("board.urls")),
    path("admin/", admin.site.urls),
]

# 404エラー時に呼び出すビューを指定
handler404 = "myproject.views.custom_404_view"
