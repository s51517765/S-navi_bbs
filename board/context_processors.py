# board/context_processors.py
from django.conf import settings
from .models import SiteConfig
import os


def const_settings(request):
    return {
        "SITE_TITLE": os.environ.get("SITE_TITLE", "デフォルトのサイト名"),
        "POST_REWARD": os.environ.get("POST_REWARD", 30),
        "GOOD_REWARD": os.environ.get("GOOD_REWARD", 1),
        "BAD_REWARD": os.environ.get("BAD_REWARD", 1),
    }


def environment_info(request):
    return {
        "ENV_COLOR": os.environ.get("ENVIRONMENT_COLOR", "Black"),
        "INQUIRY_LINK_SCRIPT": os.environ.get(
            "INQUIRY_LINK", "<問い合わせフォームスクリプト>"
        ),
    }


def support_widget(request):
    return {
        "SUPPORT_MY_SITE_SCRIPT": os.getenv("SUPPORT_MY_SITE", "<寄付の方法スクリプト>")
    }


def site_config(request):
    return {"site_config": SiteConfig.get_config()}
