# board/context_processors.py
from django.conf import settings
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
    }
