# board/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=10)  # 初期ポイント

    def __str__(self):
        return f"{self.user.username} - {self.points}pt"


# ユーザー作成時に自動でプロフィールも作る設定
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


# 投稿フォーム
# 入力項目を増やした時は、defaultを指定する
class Post(models.Model):
    # default="" を追加することで、既存データがあっても空文字で埋めてくれます
    # 訪問日を追加
    visit_date = models.DateField("訪問日", null=True, blank=True)
    shop_name = models.CharField("店名", max_length=100, default="")
    shop_url = models.URLField("URL", blank=True, null=True, default="")

    cast_name = models.CharField(
        "キャスト名", max_length=100, blank=True, null=True, default=""
    )
    cast_url = models.URLField("キャストURL", blank=True, null=True, default="")

    content = models.TextField("感想", blank=True, default="")

    # 数値や真偽値もデフォルトを設定
    stars = models.IntegerField(
        "評価", default=3, validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    want_repeat = models.BooleanField("リピートしたいか", default=False)

    # ユーザーとの紐付け（ここが一番重要です）
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.shop_name} - {self.cast_name}"

    def get_score(self):
        # この投稿に紐付く評価をすべて取得
        evals = self.evaluations.all()
        # Goodの数 × 3  +  Badの数 × (-1) を計算
        goods = evals.filter(value="good").count()
        bads = evals.filter(value="bad").count()
        return (goods * 3) - bads

    def good_count(self):
        return self.evaluations.filter(value="good").count()

    def bad_count(self):
        return self.evaluations.filter(value="bad").count()

    def get_score(self):
        return (self.good_count() * 3) - self.bad_count()


# 同じユーザーが同じ投稿に1回しか評価できない設定
class Evaluation(models.Model):
    CHOICES = (("good", "Good"), ("bad", "Bad"))
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 評価した人
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name="evaluations"
    )  # 評価された投稿
    value = models.CharField(max_length=10, choices=CHOICES)

    class Meta:
        unique_together = (
            "user",
            "post",
        )
