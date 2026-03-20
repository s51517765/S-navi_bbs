# hash_filters.py
import hashlib
from django import template

register = template.Library()


@register.filter
def hash_id(value):
    # ユーザーIDをSHA256でハッシュ化し、最初の8文字だけを返す
    # (saltを足すとより安全ですが、表示用なら簡易的なもので十分です)
    hash_object = hashlib.sha256(str(value).encode())
    return hash_object.hexdigest()[:8]
