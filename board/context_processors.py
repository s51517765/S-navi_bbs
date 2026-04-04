import os


def const_settings(request):
    return {
        "SITE_TITLE": os.environ.get("SITE_TITLE", "デフォルトのサイト名"),
        "POST_REWARD": os.environ.get("POST_REWARD", 30),
        "GOOD_REWARD": os.environ.get("GOOD_REWARD", 1),
        "BAD_REWARD": os.environ.get("BAD_REWARD", 1),
    }
