from django.shortcuts import redirect


def custom_404_view(request, exception):
    # トップページにリダイレクト。メッセージを添えることも可能。
    return redirect("index")
