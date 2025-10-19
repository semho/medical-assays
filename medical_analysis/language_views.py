"""views for language switching"""
from django.utils import translation
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods
LANGUAGE_SESSION_KEY = "_language"

@require_http_methods(["POST"])
def set_language(request):
    """
    change user's language preference and save to profile
    """
    language_code = request.POST.get("language", "ru")

    # validate language code
    if language_code not in ["ru", "en"]:
        language_code = "ru"

    # activate language for current request
    translation.activate(language_code)
    request.session[LANGUAGE_SESSION_KEY] = language_code

    # save to user profile
    if hasattr(request.user, "userprofile"):
        profile = request.user.userprofile
        profile.language_preference = language_code
        profile.save(update_fields=["language_preference"])

    # redirect to previous page or dashboard
    next_url = request.POST.get("next", request.META.get("HTTP_REFERER", "/"))
    response = redirect(next_url)
    response.set_cookie(
        "django_language",
        language_code,
        max_age=365 * 24 * 60 * 60,  # 1 year
        path="/",
        samesite="Lax",
    )

    return response