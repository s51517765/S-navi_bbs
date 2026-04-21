# board/views.py

from .forms import CustomUserCreationForm, ProfileForm, CommentForm, PostForm
from .models import (
    Post,
    Profile,
    Evaluation,
    Comment,
    CommentReaction,
    PostReaction,
    SiteConfig,
)
from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import send_mail as django_send_mail
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth import login, logout
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
)
from django.db import transaction
from django.db.models import Prefetch
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
import os


# 一覧表示（ログイン必須）
class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "board/index.html"
    context_object_name = "posts"

    def get_queryset(self):
        user = self.request.user
        profile, _ = Profile.objects.get_or_create(user=self.request.user)

        if profile.points <= 0:
            return Post.objects.none()

        # DBからスコア順や新着順で取得する
        comments_prefetch = Prefetch(
            "comments",
            queryset=Comment.objects.all().order_by(
                "created_at"
            ),  # "created_at" で固定
        )
        queryset = list(
            Post.objects.all()
            .prefetch_related(
                comments_prefetch, "comments", "reactions", "comments__reactions"
            )
            .order_by("-created_at")
        )
        # 自分が「投稿」にしたリアクションを辞書化 {post_id: type}
        user_post_reactions = {
            r.post_id: r.reaction_type for r in PostReaction.objects.filter(user=user)
        }

        # 自分が「コメント」にしたリアクションを辞書化 {comment_id: type}
        user_comment_reactions = {
            r.comment_id: r.reaction_type
            for r in CommentReaction.objects.filter(user=user)
        }

        # 各投稿とコメントに判定用データをセット
        for post in queryset:
            post.good_count_val = post.get_good_count()
            post.bad_count_val = post.get_bad_count()
            post.my_eval = user_post_reactions.get(post.id)

            # コメントに自分の評価をセット
            for comment in post.comments.all():
                comment.my_eval = user_comment_reactions.get(comment.id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # テンプレートに渡す変数を確実にセット
        context["posts"] = self.get_queryset()
        context["user_points"] = self.request.user.profile.points
        context["post_reward"] = int(os.getenv("POST_REWARD", 10))
        context["comment_form"] = CommentForm()
        return context


# 新規投稿（こちらは既にログイン済みのはず）
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = "board/post_form.html"
    success_url = reverse_lazy("index")
    form_class = PostForm

    def post(self, request, *args, **kwargs):
        # 送られてきたデータをコピーする
        data = request.POST.copy()
        visit_date_raw = data.get("visit_date")

        # "2026-03" を "2026-03-01" に書き換えてから Django に渡す
        # 日付は、月レベルにあいまいにする
        if visit_date_raw and len(visit_date_raw) == 7:
            data["visit_date"] = visit_date_raw + "-01"

        # 書き換えたデータでフォームを処理する
        request.POST = data
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        # フォームから送られてきた raw データを確認
        visit_date_raw = self.request.POST.get("visit_date")

        # 日付が "YYYY-MM" 形式なら補完してセット
        if visit_date_raw and len(visit_date_raw) == 7:
            form.instance.visit_date = visit_date_raw + "-01"

        # 投稿者をセット
        form.instance.author = self.request.user

        # ポイント加算
        POST_REWARD = os.getenv("POST_REWARD")
        profile = self.request.user.profile
        profile.points += int(POST_REWARD)
        profile.save()

        # これで全てのフィールド（URL含む）が保存される
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        context["user_points"] = profile.points
        # .env からメッセージを取得。設定がない場合のデフォルトも指定できます。
        context["post_note"] = os.getenv(
            "POST_NOTE_MESSAGE", "感想は具体的に記入してください。"
        )
        return context


@receiver(user_logged_in)
def check_login_lock(sender, request, user, **kwargs):
    config = SiteConfig.get_config()

    # ロック中 かつ ユーザーが管理者(is_staff)でない場合
    if config.login_locked and not user.is_staff:
        logout(request)


class SignUpView(CreateView):
    def dispatch(self, request, *args, **kwargs):
        config = SiteConfig.get_config()
        # ログインロック（メンテナンス）時はサインアップも停止
        if config.signup_locked or config.login_locked:
            return redirect("index")
        return super().dispatch(request, *args, **kwargs)

    form_class = CustomUserCreationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")
    # 表示したいメッセージを設定
    success_message = (
        "ユーザー登録が完了しました。メールを確認してアカウントを有効化してください。"
    )

    def form_valid(self, form):
        # まずユーザーを保存（is_active=False）
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        # 保存されたあとの user オブジェクトを使ってトークンを作る
        current_site = get_current_site(self.request)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        SITE_TITLE = os.getenv("SITE_TITLE", "掲示板")
        EMAIL_REGISTER_MESSAGE = os.getenv("EMAIL_REGISTER_MESSAGE", "掲示板")
        subject = f"【{SITE_TITLE}】会員登録を完了させてください"

        context = {
            "user": user,
            "domain": current_site.domain,
            "uid": uid,
            "token": token,
            "site_name": SITE_TITLE,
            "email_register_message": EMAIL_REGISTER_MESSAGE,
        }

        message = render_to_string("registration/acc_active_email.html", context)
        user.email_user(subject, message)
        # デバッグ用にターミナルに表示
        print(
            f"\n--- Activation URL ---\nhttp://{current_site.domain}/activate/{uid}/{token}/\n----------------------\n"
        )

        messages.success(
            self.request, "ユーザー登録が完了しました。メールを確認してください。"
        )
        return redirect(self.success_url)


def activate(request, uidb64, token):
    try:
        # uidb64 を復号してユーザーIDを取得
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # ユーザーが存在し、かつトークンが正しいかチェック
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(
            request, "アカウントが有効化されました！ログインしてください。"
        )
        return redirect("login")
    else:
        return render(request, "registration/activation_invalid.html")


# パスワードリセットのカスタム
class CustomPasswordResetForm(PasswordResetForm):
    def send_mail(
        self,
        subject_template_name,
        email_template_name,
        context,
        from_email,
        to_email,
        html_email_template_name=None,
    ):
        site_title = os.getenv("SITE_TITLE", "掲示板")

        # 本文用変数
        context["site_name"] = site_title

        # 標準の送信処理に、作成した subject を渡して実行
        super().send_mail(
            subject_template_name,
            email_template_name,
            context,
            from_email,
            to_email,
            html_email_template_name=html_email_template_name,
        )


# 2. ビューでこのカスタムフォームを使うように指定する
class CustomPasswordResetView(PasswordResetView):
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    success_url = reverse_lazy("password_reset_done")
    # 自作フォームを指定
    form_class = CustomPasswordResetForm

    def dispatch(self, *args, **kwargs):
        print("\n!!! DEBUG: CustomPasswordResetView CALLED !!!\n")
        config = SiteConfig.get_config()
        if config.login_locked:
            return redirect("index")
        return super().dispatch(*args, **kwargs)


"""
# 編集機能は入れない
class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    template_name = "board/post_form.html"
    # fields を最新に合わせる
    fields = [
        "visit_date",
        "shop_name",
        "shop_url",
        "cast_name",
        "cast_url",
        "content",
        "stars",
        "want_repeat",
    ]
    success_url = reverse_lazy("index")

    def post(self, request, *args, **kwargs):
        data = request.POST.copy()
        visit_date_raw = data.get("visit_date")
        if visit_date_raw and len(visit_date_raw) == 7:
            data["visit_date"] = visit_date_raw + "-01"
        request.POST = data
        return super().post(request, *args, **kwargs)

    def test_func(self):
        return self.get_object().author == self.request.user


# 削除機能は入れない
class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    template_name = "board/post_confirm_delete.html"
    success_url = reverse_lazy("index")

    def test_func(self):
        return self.get_object().author == self.request.user
"""


class Guide(TemplateView):
    # 表示するHTMLファイルを指定
    template_name = "board/guide.html"

    def get_context_data(self, **kwargs):
        # テンプレートに渡す追加データがあればここに記述
        context = super().get_context_data(**kwargs)
        # 例: ページタイトルなどを動的に渡す場合
        context["page_title"] = "ご利用ガイド"
        return context


# （投稿）POST以外のアクセス（直接URLを叩くなど）を禁止する
def evaluate_post(request, post_id, eval_type):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "ログインが必要です"}, status=403)

    post = get_object_or_404(Post, id=post_id)
    if post.author == request.user:
        return JsonResponse(
            {
                "error": "自分の投稿にはリアクションできません",
                "status": "mine",  # JavaScript側で判定するためにステータスを送る
            },
            status=403,
        )

    reaction = PostReaction.objects.filter(post=post, user=request.user).first()

    GOOD_REWARD = int(os.getenv("GOOD_REWARD", 10))
    BAD_REWARD = int(os.getenv("BAD_REWARD", 5))

    if reaction:
        if reaction.reaction_type == eval_type:
            # 【解除】
            if eval_type == "good":
                post.point -= GOOD_REWARD
            else:
                post.point += BAD_REWARD
            reaction.delete()
            status = "removed"
        else:
            old_type = reaction.reaction_type

            if old_type == "good":
                post.point -= GOOD_REWARD + BAD_REWARD
            else:
                post.point += GOOD_REWARD + BAD_REWARD

            reaction.reaction_type = eval_type
            reaction.save()
            status = "switched"
    else:
        # 【新規】
        PostReaction.objects.create(
            post=post, user=request.user, reaction_type=eval_type
        )
        if eval_type == "good":
            post.point += GOOD_REWARD
        else:
            post.point -= BAD_REWARD
        status = "added"

    # DBに保存
    post.save()

    # ここで「モデルのメソッド」を呼び出して最新の数を取得する
    good_count = post.reactions.filter(reaction_type="good").count()
    bad_count = post.reactions.filter(reaction_type="bad").count()

    return JsonResponse(
        {
            "good_count": good_count,
            "bad_count": bad_count,
            "status": status,
            "point": post.point,
        }
    )


@receiver(user_logged_in)
def reduce_points_on_login(sender, request, user, **kwargs):
    print(f"\n=== DEBUG START for {user.username} ===")
    profile, created = Profile.objects.get_or_create(user=user)

    # DBから取り出した直後の値を確認
    raw_last_update = profile.last_point_update
    print(f"1. DB内の最終更新日: {raw_last_update} (型: {type(raw_last_update)})")

    today = timezone.now().date()
    print(f"2. 計算に使用する今日の日付: {today}")

    # 計算式の内訳を確認
    diff = today - raw_last_update
    days_passed = diff.days
    print(f"3. 差分計算結果: {diff} -> days属性: {days_passed}")

    if days_passed >= 1:
        reduction = days_passed
        old_points = profile.points
        profile.points = max(0, profile.points - reduction)
        profile.last_point_update = today
        profile.save()
        print(f"4. 【更新実行】 {old_points} -> {profile.points} (減少量: {reduction})")
    else:
        print("4. 【更新スキップ】 1日以上経過していません")

    print("=== DEBUG END ===\n")


@login_required
def profile_edit(request):
    # ユーザーモデル
    user = request.user

    if request.method == "POST":
        # instance=user とすることで、今のユーザー情報を上書き保存します
        form = ProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect("index")
    else:
        form = ProfileForm(instance=user)

    return render(request, "board/profile_edit.html", {"form": form})


# コメントをする
@login_required
def add_comment(request, post_id):
    if request.method == "POST" and request.user.is_authenticated:
        # まず、対象となる Post をデータベースから取得する
        post = get_object_or_404(Post, id=post_id)

        content = request.POST.get("content")
        if content:
            # 取得した post 変数を使ってコメントを作成
            comment = Comment.objects.create(
                post=post, author=request.user, content=content
            )

            # JavaScriptに返すデータ
            return JsonResponse(
                {
                    "status": "ok",
                    "comment_id": comment.id,
                    "author_display_name": request.user.first_name,  # ニックネーム
                    "content": comment.content,
                    "created_at": "たった今",
                }
            )

    return JsonResponse({"status": "error"}, status=400)


# コメントに対するリアクション処理（元の投稿とコメントは区別）
@login_required
def comment_reaction(request, comment_id, reaction_type):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "ログインが必要です"}, status=403)

    comment = get_object_or_404(Comment, id=comment_id)

    # 自分のコメントにはリアクションできないようにする
    if comment.author == request.user:
        return JsonResponse(
            {"error": "自分のコメントにはリアクションできません"}, status=403
        )

    # ユーザーがこのコメントに対して持っている既存のリアクションを探す
    reaction = CommentReaction.objects.filter(
        comment=comment, user=request.user
    ).first()

    if reaction:
        if reaction.reaction_type == reaction_type:
            # 【解除】同じボタンをもう一度押した場合：削除してカウントを減らす
            reaction.delete()
            if reaction_type == "good":
                comment.good_count = max(0, comment.good_count - 1)
            else:
                comment.bad_count = max(0, comment.bad_count - 1)
            status = "removed"
        else:
            # 【切り替え】Good<-->Badへ変更する場合
            # 古い方のカウントを減らす
            if reaction.reaction_type == "good":
                comment.good_count = max(0, comment.good_count - 1)
                comment.bad_count += 1
            else:
                comment.bad_count = max(0, comment.bad_count - 1)
                comment.good_count += 1

            # 種類を書き換えて保存
            reaction.reaction_type = reaction_type
            reaction.save()
            status = "switched"
    else:
        # 【新規】まだリアクションがない場合
        CommentReaction.objects.create(
            comment=comment, user=request.user, reaction_type=reaction_type
        )
        if reaction_type == "good":
            comment.good_count += 1
        else:
            comment.bad_count += 1
        status = "added"

    # DB更新
    comment.save()
    # リダイレクトではなくJSONデータを返す
    return JsonResponse(
        {
            "good_count": comment.good_count,
            "bad_count": comment.bad_count,
            "status": status,
            "current_type": reaction_type if status != "removed" else None,
        }
    )


def post_detail(request, pk):
    post = get_object_or_404(Post, pk=pk)
    # 詳細画面でもコメント入力用のフォームを表示するために渡す
    comment_form = CommentForm()
    return render(
        request,
        "board/post_detail.html",
        {
            "post": post,
            "comment_form": comment_form,
        },
    )
