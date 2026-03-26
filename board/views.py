# board/views.py
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CustomUserCreationForm, ProfileForm, CommentForm
from .models import Post, Profile, Evaluation, Comment, CommentReaction, PostReaction
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
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse


# 一覧表示（ログイン必須に変更）
class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "board/index.html"
    context_object_name = "posts"


class PostListView(LoginRequiredMixin, ListView):
    model = Post
    template_name = "board/index.html"
    context_object_name = "posts"

    def get_queryset(self):
        # 1. ユーザーのプロフィールを取得
        profile, _ = Profile.objects.get_or_create(user=self.request.user)

        # 2. ポイント不足で空になっていないかDBを確認（管理画面で増やしておくと確実）
        if profile.points <= 0:
            return Post.objects.none()

        # 3. データをリストとして確定させる（属性が消えるのを防ぐ）
        queryset = list(
            Post.objects.all().prefetch_related("comments").order_by("-created_at")
        )

        for post in queryset:
            # 評価情報を直接付与
            post.good_count = post.evaluations.filter(value="good").count()
            post.bad_count = post.evaluations.filter(value="bad").count()
            # スコア計算
            post.get_score = (post.good_count * 3) - (post.bad_count * 1)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # テンプレートに渡す変数を確実にセット
        context["posts"] = self.get_queryset()
        context["user_points"] = self.request.user.profile.points
        context["comment_form"] = CommentForm()
        return context


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

        # ここから追加：first_name のバリデーション


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
    post = get_object_or_404(Post, id=post_id)
    reaction = PostReaction.objects.filter(post=post, user=request.user).first()

    if reaction:
        if reaction.reaction_type == eval_type:
            reaction.delete()
            status = "removed"
        else:
            reaction.reaction_type = eval_type
            reaction.save()
            status = "switched"
    else:
        PostReaction.objects.create(
            post=post, user=request.user, reaction_type=eval_type
        )
        status = "added"

    # ★ ここで「モデルのメソッド」を呼び出して最新の数を取得する
    # もしメソッド名が good_count なら () をつけて呼び出す
    good_count = post.reactions.filter(reaction_type="good").count()
    bad_count = post.reactions.filter(reaction_type="bad").count()

    return JsonResponse(
        {
            "good_count": good_count,
            "bad_count": bad_count,
            "status": status,
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
    # プロフィールモデルではなく、ログインユーザー自身を編集対象にする
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
        # 1. まず、対象となる Post をデータベースから取得する（これが抜けていたはずです）
        post = get_object_or_404(Post, id=post_id)

        content = request.POST.get("content")
        if content:
            # 2. 取得した post 変数を使ってコメントを作成
            comment = Comment.objects.create(
                post=post, author=request.user, content=content
            )

            # JavaScriptに返すデータ
            return JsonResponse(
                {
                    "status": "ok",
                    "comment_id": comment.id,
                    "author_display_name": request.user.first_name,  # プロフィール名なら request.user.profile.nickname など
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
        return redirect("post_detail", pk=comment.post.id)

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
