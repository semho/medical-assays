"""
middleware for automatic user language activation
"""

from django.utils import translation
LANGUAGE_SESSION_KEY = "_language"

class UserLanguageMiddleware:
    """
    activate user's preferred language from their profile

    priority:
    1. session language (set by set_language view)
    2. user profile language_preference
    3. default language from settings
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # check if user is authenticated and has profile
        if request.user.is_authenticated and hasattr(request.user, "userprofile"):
            profile = request.user.userprofile

            # if no language in session, use profile preference
            if not request.session.get(LANGUAGE_SESSION_KEY):
                language = profile.language_preference
                translation.activate(language)
                request.LANGUAGE_CODE = language

        response = self.get_response(request)
        return response