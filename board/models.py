# board/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=10)  # 初期ポイント
    last_point_update = models.DateField(default=timezone.now)  # 最後に減点した日
    nickname = models.CharField(max_length=20, blank=True, verbose_name="ニックネーム")

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
    # blank=Falseで必須
    # 訪問日を追加
    visit_date = models.DateField("訪問日", null=True, blank=False)
    shop_name = models.CharField("店名", max_length=100, default="")
    shop_url = models.URLField("URL", blank=True, null=True, default="")

    cast_name = models.CharField(
        "キャスト名", max_length=100, blank=True, null=True, default=""
    )
    cast_url = models.URLField("キャストURL", blank=True, null=True, default="")

    content = models.TextField("感想", blank=False, default="")

    # 数値や真偽値もデフォルトを設定
    stars = models.IntegerField(
        "評価",
        default="",
        null=False,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
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

    def get_good_count(self):
        return self.reactions.filter(reaction_type="good").count()

    def get_bad_count(self):
        return self.reactions.filter(reaction_type="bad").count()

    def get_score(self):  # @property が付いていないことを確認
        # Goodは3pt、Badは-1ptで計算
        return (self.get_good_count() * 3) - self.get_bad_count()


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


class Comment(models.Model):
    post = models.ForeignKey("Post", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField(max_length=500, verbose_name="コメント内容")
    created_at = models.DateTimeField(auto_now_add=True)

    # リアクション用
    good_count = models.IntegerField(default=0)
    bad_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.author.username}のコメント - {self.content[:10]}"

    def get_good_count(self):
        return self.reactions.filter(reaction_type="good").count()

    def get_bad_count(self):
        return self.reactions.filter(reaction_type="bad").count()


class CommentReaction(models.Model):
    REACTION_CHOICES = [("good", "Good"), ("bad", "Bad")]

    comment = models.ForeignKey(
        Comment, on_delete=models.CASCADE, related_name="reactions"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)

    class Meta:
        # 同じユーザーが同じコメントに2回以上反応できないようにする制約
        unique_together = ("comment", "user")


# すでにあるクラスの下に追加
class PostReaction(models.Model):
    REACTION_CHOICES = [("good", "Good"), ("bad", "Bad")]

    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reactions")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)

    class Meta:
        unique_together = ("post", "user")  # 1人1投稿につき1反応まで
