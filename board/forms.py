# board/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class CustomUserCreationForm(UserCreationForm):
    # 表示名用の入力欄を追加（Django標準のfirst_nameを利用）
    nickname = forms.CharField(
        label="表示名（ニックネーム）",
        max_length=30,
        help_text="サイト内で表示される名前です。後から変更可能です。",
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

    def save(self, commit=True):
        user = super().save(commit=False)
        # 入力された nickname を first_name フィールドに保存
        user.first_name = self.cleaned_data["nickname"]
        if commit:
            user.save()
        return user
