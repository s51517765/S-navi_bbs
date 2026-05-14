# board/models.py #root直下にもmodels.pyはあるが使っていない
from django import forms
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
import os


class SiteConfig(models.Model):
    signup_locked = models.BooleanField(
        default=False, verbose_name="新規登録をロックする"
    )
    login_locked = models.BooleanField(
        # パスワードリセット含む
        default=False,
        verbose_name="ログインをロックする（管理者以外）",
    )

    class Meta:
        verbose_name = "システム設定"
        verbose_name_plural = "システム設定"

    def __str__(self):
        return "システム設定"

    signup_locked = models.BooleanField(
        default=False, verbose_name="新規登録をロックする"
    )
    maintenance_message = models.TextField(
        blank=True, verbose_name="メンテナンス中メッセージ"
    )

    class Meta:
        verbose_name = "システム設定"
        verbose_name_plural = "システム設定"

    def __str__(self):
        return "システム設定"

    def save(self, *args, **kwargs):
        # 常にID=1のレコードを更新するようにし、データが1つしか存在しないようにする
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        # 設定を取得する便利メソッド
        config, created = cls.objects.get_or_create(pk=1)
        return config


class Profile(models.Model):
    INITIAL_POINT = int(os.getenv("INITIAL_POINT", 1))
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    points = models.IntegerField(default=INITIAL_POINT)  # 初期ポイント
    last_point_update = models.DateTimeField(default=timezone.now)  # 最後に減点した日時

    def __str__(self):
        return f"{self.user.username} - {self.points}pt"


# ユーザー作成時に自動でプロフィールも作る設定
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
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
    point = models.IntegerField(default=0)

    cast_name = models.CharField(
        "キャスト名", max_length=100, blank=True, null=True, default=""
    )
    cast_url = models.URLField("キャストURL", blank=True, null=True, default="")
    content = models.TextField("感想", blank=False, default="")
    category = models.CharField("カテゴリ", blank=False, max_length=50, default="")
    region = models.CharField("都道府県", blank=False, max_length=50, default="")
    sub_region = models.CharField("地域", max_length=50, blank=True, null=True)
    is_draft = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    # 数値や真偽値もデフォルトを設定
    stars = models.IntegerField(
        "評価",
        default="",
        null=False,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    want_repeat = models.BooleanField("リピートしたいか", default=False)

    # ユーザーとの紐付け
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.shop_name} - {self.cast_name}"

    def get_good_count(self):
        return self.reactions.filter(reaction_type="good").count()

    def get_bad_count(self):
        return self.reactions.filter(reaction_type="bad").count()


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


# 投稿に対するリアクション
@receiver(post_save, sender=PostReaction)
def update_user_points_from_reaction(sender, instance, created, **kwargs):
    # 環境変数を数値として取得（デフォルト値を設定）
    GOOD_REWARD = int(os.getenv("GOOD_REWARD", 1))
    BAD_REWARD = int(os.getenv("BAD_REWARD", 1))

    # プロフィールを取得（なければ作成）
    author = instance.post.author
    profile, _ = Profile.objects.get_or_create(user=author)

    if created:
        # 新しくリアクションが追加された場合
        if instance.reaction_type == "good":
            profile.points += GOOD_REWARD
        elif instance.reaction_type == "bad":
            profile.points -= BAD_REWARD
    else:
        # GoodからBad（または逆）へ変更された場合（created=False）
        if instance.reaction_type == "good":
            profile.points += GOOD_REWARD + BAD_REWARD
        elif instance.reaction_type == "bad":
            profile.points -= GOOD_REWARD + BAD_REWARD

    profile.save()


# 取り消し（削除）された時もポイントを差し戻す必要がある場合
@receiver(post_delete, sender=PostReaction)
def refund_user_points(sender, instance, **kwargs):
    # 環境変数を数値として取得（デフォルト値を設定）
    GOOD_REWARD = int(os.getenv("GOOD_REWARD", 1))
    BAD_REWARD = int(os.getenv("BAD_REWARD", 1))

    profile, _ = Profile.objects.get_or_create(user=instance.post.author)
    if instance.reaction_type == "good":
        profile.points -= GOOD_REWARD
    elif instance.reaction_type == "bad":
        profile.points += BAD_REWARD

    profile.save()


# コメントに対するリアクション
@receiver(post_save, sender=CommentReaction)
def update_user_points_from_comment_reaction(sender, instance, created, **kwargs):
    # 環境変数を数値として取得（デフォルト値を設定）
    GOOD_REWARD = int(os.getenv("GOOD_REWARD", 1))
    BAD_REWARD = int(os.getenv("BAD_REWARD", 1))

    # コメントの投稿者のプロフィールを取得
    author = instance.comment.author
    profile, _ = Profile.objects.get_or_create(user=author)

    if created:
        # 新規リアクション
        if instance.reaction_type == "good":
            profile.points += GOOD_REWARD
        elif instance.reaction_type == "bad":
            profile.points -= BAD_REWARD
    else:
        # Good <-> Bad の切り替え
        # (GOOD + BAD) 分を動かすことで、逆の評価を相殺して新評価を適用する
        if instance.reaction_type == "good":
            profile.points += GOOD_REWARD + BAD_REWARD
        elif instance.reaction_type == "bad":
            profile.points -= GOOD_REWARD + BAD_REWARD

    profile.save()


# 取り消し（削除）された時もポイントを差し戻す必要がある場合
@receiver(post_delete, sender=CommentReaction)
def refund_user_points(sender, instance, **kwargs):

    GOOD_REWARD = int(os.getenv("GOOD_REWARD", 1))
    BAD_REWARD = int(os.getenv("BAD_REWARD", 1))
    author = instance.comment.author
    profile, _ = Profile.objects.get_or_create(user=author)
    if instance.reaction_type == "good":
        profile.points -= GOOD_REWARD
    elif instance.reaction_type == "bad":
        profile.points += BAD_REWARD

    profile.save()


# ログイン前ページ　インフォメーション掲示
class Information(models.Model):
    title = models.CharField("タイトル", max_length=200)
    content = models.TextField("内容")
    created_at = models.DateTimeField("公開日", default=timezone.now)
    is_active = models.BooleanField("表示フラグ", default=True)

    class Meta:
        verbose_name = "お知らせ"
        verbose_name_plural = "お知らせ"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
