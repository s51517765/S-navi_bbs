# board/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile
from django.core.exceptions import ValidationError
from .models import Comment, Post
import os


def validate_nickname(value, is_staff):
    if not is_staff:
        tmp = value.lower()
        if "管理" in value or "admin" in tmp:
            raise ValidationError("「管理」や「admin」などは管理者専用です")
        if "@" in value:
            raise ValidationError("禁止されている文字が含まれています")


class CustomUserCreationForm(UserCreationForm):
    # 表示名用の入力欄を追加（Django標準のfirst_nameを利用）
    nickname = forms.CharField(
        label="表示名（ニックネーム）",
        max_length=30,
        help_text="サイト内で表示される名前です。",
        required=True,
    )
    # メールアドレスを明示的に定義し、required=True にする
    email = forms.EmailField(
        required=True, help_text="有効なメールアドレスを入力してください。"
    )

    class Meta(UserCreationForm.Meta):
        model = User
        # 入力項目に email を追加
        fields = ("username", "email", "nickname")

        labels = {
            "username": "ユーザーID",  # ここで表記を変更
            "email": "メールアドレス",
        }

        help_texts = {
            "username": "ユーザIDは半角英数字と記号（@/./+/-/_）が使用可能です。",
        }

    # メールアドレスの重複チェック
    def clean_email(self):
        email = self.cleaned_data.get("email")

        # データベース内に同じメールアドレスを持つユーザーがいるか確認
        if User.objects.filter(email=email).exists():
            raise ValidationError("このメールアドレスは既に登録されています。")

        return email

    def clean_nickname(self):
        # self.cleaned_data["nickname"] をチェックする
        nickname = self.cleaned_data.get("nickname")

        # 共通バリデーション関数を呼び出す
        # 新規登録時は self.instance.is_staff は常に False なのでそのまま渡してOK
        validate_nickname(nickname, self.instance.is_staff)

        return nickname

    def save(self, commit=True):
        user = super().save(commit=False)
        # 入力された nickname を first_name フィールドに保存
        user.first_name = self.cleaned_data["nickname"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name"]  # ニックネームとして使っている項目
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "ニックネームを入力"}
            ),
        }
        labels = {
            "first_name": "ニックネーム",
        }

    # ここから追加：first_name のバリデーション
    def clean_first_name(self):
        first_name = self.cleaned_data.get("first_name")
        # 共通関数を呼び出す（修正漏れを防げる！）
        validate_nickname(first_name, self.instance.is_staff)
        return first_name


class PostForm(forms.ModelForm):
    # プルダウンとして定義
    category = forms.ChoiceField(
        choices=[],
        label="カテゴリ",
        required=True,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    class Meta:
        model = Post
        fields = [
            "visit_date",
            "category",
            "shop_name",
            "shop_url",
            "cast_name",
            "cast_url",
            "content",
            "stars",
            "want_repeat",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 環境変数から取得
        env_categories = os.getenv("POST_CATEGORIES", ",牛丼,カレー,カフェ,雑貨,その他")
        category_list = [
            (cat.strip(), cat.strip()) for cat in env_categories.split(",")
        ]
        self.fields["category"].choices = category_list


# コメント
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["content"]  # 投稿する内容はコメント本文だけ
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "コメントを入力してください...",
                }
            ),
        }
        labels = {
            "content": "コメント",
        }
