"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

# myproject/urls.py
from django.contrib import admin
from django.urls import path, include  # include を忘れずに追加！

urlpatterns = [
    path("admin/", admin.site.urls),
    # 1. 掲示板アプリのURLをルート（/）に紐付ける
    path("", include("board.urls")),
    # 2. Django標準のログイン・ログアウト機能を有効にする
    path("accounts/", include("django.contrib.auth.urls")),
]
