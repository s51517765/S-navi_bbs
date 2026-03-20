# ログインしていない時に飛ばされる先
LOGIN_URL = "login"

# ログイン・ログアウト後の移動先
LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "login"  # ログアウトしたらログイン画面に戻るのが一般的です

# Mailアドレスでログイン
AUTHENTICATION_BACKENDS = [
    "board.auth_backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",  # 標準のユーザー名ログインも残す場合
]
