# board/admin.py
from django.contrib import admin
from .models import Post, Profile
from .models import SiteConfig
from django.contrib import admin
from .models import Information


# admin管理画面
@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    # 'title' を 'shop_name' に変更し、他の項目も追加すると便利です
    list_display = ("id", "shop_name", "cast_name", "stars", "author", "created_at")

    # 検索窓で検索できる項目も更新
    search_fields = ("shop_name", "cast_name", "content")

    # 右側のフィルター機能
    list_filter = ("stars", "want_repeat", "created_at")


admin.site.register(Profile)


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    # 新しくレコードを追加できないようにする（1つあれば十分なので）
    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()

    # 削除もできないようにする
    def has_delete_permission(self, request, obj=None):
        return False


# ログイン前ページ　インフォメーション掲示
@admin.register(Information)
class InformationAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "is_active")
    list_filter = ("is_active",)
    search_fields = ("title", "content")
