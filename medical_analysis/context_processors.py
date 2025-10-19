"""
context processors for adding data to all templates
"""

from django.conf import settings
from django.utils import translation


def language_context(request):
    """
    add current language code to template context

    this allows templates to access LANGUAGE_CODE directly
    """
    return {
        "LANGUAGE_CODE": translation.get_language(),
        "AVAILABLE_LANGUAGES": settings.LANGUAGES,
    }