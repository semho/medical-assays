"""URL configuration for medical_mvp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))

"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.conf.urls.static import static
from medical_mvp import settings


def health_check(request):
    """Endpoint для проверки здоровья приложения"""
    return JsonResponse(
        {
            "status": "healthy",
            "version": "1.0.0",
            "services": {"database": "ok", "redis": "ok", "file_processing": "ok"},
        }
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    # Проверка здоровья
    path("health/", health_check, name="health_check"),
    # API endpoints
    path("api/", include("medical_analysis.api_urls")),
    # Веб-интерфейс
    path("", include("medical_analysis.urls")),
]

# Обслуживание медиа файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Django Debug Toolbar
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
        ] + urlpatterns

# Кастомные страницы ошибок
handler404 = "medical_analysis.views.custom_404"
handler500 = "medical_analysis.views.custom_500"
