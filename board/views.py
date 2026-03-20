# board/views.py
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CustomUserCreationForm  # 新しく作ったフォームを読み込む
from .models import Post, Profile, Evaluation
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.views.generic import UpdateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db import transaction
from django.views.decorators.http import require_POST


# 一覧表示（ログイン必須に変更）
class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "board/index.html"
    context_object_name = "posts"

    def get_queryset(self):
        # ポイントが0以下の場合は空のリストを返す（または特定のメッセージ用フラグを立てる）
        if self.request.user.profile.points <= 0:
            return Post.objects.none()
        return Post.objects.all().order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_points"] = self.request.user.profile.points
        return context

    def get_queryset(self):
        queryset = Post.objects.all().order_by("-created_at")
        for post in queryset:
            # ログインユーザーの評価を一時的な属性として持たせる
            user_eval = post.evaluations.filter(user=self.request.user).first()
            post.my_eval = user_eval.value if user_eval else None
        return queryset


# 新規投稿（こちらは既にログイン必須のはず）
class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    template_name = "board/post_form.html"
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
        # 1. 送られてきたデータをコピーする
        data = request.POST.copy()
        visit_date_raw = data.get("visit_date")

        # 2. "2026-03" を "2026-03-01" に書き換えてから Django に渡す
        # 日付は、月レベルにあいまいにする
        if visit_date_raw and len(visit_date_raw) == 7:
            data["visit_date"] = visit_date_raw + "-01"

        # 3. 書き換えたデータでフォームを処理する
        request.POST = data
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        # 1. フォームから送られてきた raw データを確認
        visit_date_raw = self.request.POST.get("visit_date")

        # 2. 日付が "YYYY-MM" 形式なら補完してセット
        if visit_date_raw and len(visit_date_raw) == 7:
            form.instance.visit_date = visit_date_raw + "-01"

        # 3. 投稿者をセット
        form.instance.author = self.request.user

        # ポイント加算
        profile = self.request.user.profile
        profile.points += 30
        profile.save()

        # 4. これで全てのフィールド（URL含む）が保存される
        return super().form_valid(form)


class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("login")
    # 表示したいメッセージを設定
    success_message = (
        "ユーザー登録が完了しました。メールを確認してアカウントを有効化してください。"
    )

    def form_valid(self, form):
        # 1. まずユーザーを保存（is_active=False）
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        # 2. 保存されたあとの user オブジェクトを使ってトークンを作る
        current_site = get_current_site(self.request)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)  # ここが重要

        subject = "【重要】会員登録を完了させてください"
        message = render_to_string(
            "registration/acc_active_email.html",
            {
                "user": user,
                "domain": current_site.domain,
                "uid": uid,
                "token": token,
            },
        )

        # 3. デバッグ用にターミナルに表示
        print(
            f"\n--- Activation URL ---\nhttp://{current_site.domain}/activate/{uid}/{token}/\n----------------------\n"
        )

        send_mail(subject, message, "admin@example.com", [user.email])

        # 4. super().form_valid を呼ばずに直接リダイレクトする（確実な方法）
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
        # ここで失敗している
        return render(request, "registration/activation_invalid.html")


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


def give_good(request, post_id):
    # 1. どの投稿に対する「Good」か特定する
    post = get_object_or_404(Post, id=post_id)

    # 2. 投稿した人のプロフィールを取得
    author_profile = post.author.profile

    # 3. ポイントを加算して保存
    author_profile.points += 3
    author_profile.save()

    # 4. メッセージを表示（任意）
    messages.success(request, f"{post.author.username}さんに3ポイント送りました！")

    # 5. もとの画面（一覧画面など）に戻る
    return redirect("index")


@require_POST  # POST以外のアクセス（直接URLを叩くなど）を禁止する
def evaluate_post(request, post_id, eval_type):
    post = get_object_or_404(Post, id=post_id)
    author_profile = post.author.profile
    user = request.user

    # 自分の投稿には評価できないようにする場合
    if post.author == user:
        messages.warning(request, "自分の投稿は評価できません。")
        return redirect("index")

    with transaction.atomic():
        # 既存の評価があるか確認
        existing_eval = Evaluation.objects.filter(user=user, post=post).first()
        if existing_eval:
            # --- 【追加】同じボタンをもう一度押した場合（キャンセル） ---
            if existing_eval.value == eval_type:
                if eval_type == "good":
                    author_profile.points -= 3
                else:
                    author_profile.points += 1

                existing_eval.delete()  # 評価レコードを削除
                author_profile.save()
                messages.info(request, "評価を取り消しました。")
                return redirect("index")

            # --- 評価の書き換え（Good ↔ Bad） ---
            if existing_eval.value == "good":
                author_profile.points -= 3  # 前のGood分を引く
            else:
                author_profile.points += 1  # 前のBad分を戻す

            existing_eval.value = eval_type
            existing_eval.save()
        else:
            # --- 新規評価 ---
            Evaluation.objects.create(user=user, post=post, value=eval_type)

        # 今回の評価分を反映
        if eval_type == "good":
            author_profile.points += 3
        else:
            author_profile.points -= 1

        author_profile.save()

    messages.success(request, f"評価を反映しました。")
    return redirect("index")
